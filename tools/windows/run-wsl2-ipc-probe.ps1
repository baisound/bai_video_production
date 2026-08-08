param(
    [Parameter(Mandatory=$false)][string]$Python = "python",
    [Parameter(Mandatory=$false)][string]$OutputDir = ".\resolve-spike-evidence"
)
$ErrorActionPreference = "Stop"
$repoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$srcRoot=Join-Path $repoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $env:PYTHONPATH=$srcRoot } else { $env:PYTHONPATH="$srcRoot;$($env:PYTHONPATH)" }
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputRoot=(Resolve-Path $OutputDir).Path
$serverScript=Join-Path $PSScriptRoot "wsl-http-probe-server.py"
$clientWin=Join-Path $repoRoot "tools\wsl\http-ipc-client.py"
$phase1Win=Join-Path $outputRoot "wsl-ipc-phase1.json"
$phase2Win=Join-Path $outputRoot "wsl-ipc-phase2.json"
$final=Join-Path $outputRoot "resolve-wsl-ipc-probe-report.json"
$listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
$listener.Start(); $port=([System.Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
$token=[Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")

$oldEnv=@{
    BAI_IPC_PROBE_TOKEN=$env:BAI_IPC_PROBE_TOKEN
    BAI_WSL_CLIENT_PATH=$env:BAI_WSL_CLIENT_PATH
    BAI_WSL_PHASE1_PATH=$env:BAI_WSL_PHASE1_PATH
    BAI_WSL_PHASE2_PATH=$env:BAI_WSL_PHASE2_PATH
    BAI_WSL_IPC_PORT=$env:BAI_WSL_IPC_PORT
    BAI_WSL_EXPECT_HOST_KIND=$env:BAI_WSL_EXPECT_HOST_KIND
    WSLENV=$env:WSLENV
}

function Add-WslEnvEntry([string]$Name, [bool]$TranslatePath) {
    $items=@()
    if (-not [string]::IsNullOrWhiteSpace($env:WSLENV)) { $items=@($env:WSLENV -split ':') }
    $escaped=[regex]::Escape($Name)
    $items=@($items | Where-Object { $_ -notmatch "^$escaped(?:/.*)?$" })
    if ($TranslatePath) { $items += "$Name/p" } else { $items += $Name }
    $env:WSLENV=($items -join ':')
}

$env:BAI_IPC_PROBE_TOKEN=$token
$env:BAI_WSL_CLIENT_PATH=$clientWin
$env:BAI_WSL_PHASE1_PATH=$phase1Win
$env:BAI_WSL_PHASE2_PATH=$phase2Win
$env:BAI_WSL_IPC_PORT="$port"
$env:BAI_WSL_EXPECT_HOST_KIND=""
Add-WslEnvEntry "BAI_IPC_PROBE_TOKEN" $false
Add-WslEnvEntry "BAI_WSL_CLIENT_PATH" $true
Add-WslEnvEntry "BAI_WSL_PHASE1_PATH" $true
Add-WslEnvEntry "BAI_WSL_PHASE2_PATH" $true
Add-WslEnvEntry "BAI_WSL_IPC_PORT" $false
Add-WslEnvEntry "BAI_WSL_EXPECT_HOST_KIND" $false

$s1=$null; $s2=$null
function StartServer([string]$ready) {
    if (Test-Path $ready) { Remove-Item $ready -Force }
    $proc=Start-Process -FilePath $Python -ArgumentList @("`"$serverScript`"",'--port',"$port",'--ready-file',"`"$ready`"") -PassThru -WindowStyle Hidden
    for($i=0;$i -lt 50;$i++){ if(Test-Path $ready){return $proc}; Start-Sleep -Milliseconds 100 }
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw "Probe server did not become ready"
}

function Invoke-WslPhase([int]$Phase) {
    if ($Phase -eq 1) {
        $command='python3 "$BAI_WSL_CLIENT_PATH" --port "$BAI_WSL_IPC_PORT" --phase 1 --output "$BAI_WSL_PHASE1_PATH"'
    } else {
        $command='python3 "$BAI_WSL_CLIENT_PATH" --port "$BAI_WSL_IPC_PORT" --phase 2 --output "$BAI_WSL_PHASE2_PATH" --expect-host-kind "$BAI_WSL_EXPECT_HOST_KIND"'
    }
    & wsl.exe sh -lc $command | Out-Host
    $exitCode=$LASTEXITCODE
    return $exitCode
}

try {
    & wsl.exe sh -lc 'command -v python3 >/dev/null 2>&1'
    if ($LASTEXITCODE -ne 0) { throw "WSL2 is available but python3 was not found in the selected distribution." }

    Write-Host "WSL path bridge: WSLENV /p translation"
    Write-Host "Windows client: $clientWin"

    $ready1=Join-Path $env:TEMP "bai-wsl-ipc-ready1-$PID.json"; $s1=StartServer $ready1
    $phase1Exit=Invoke-WslPhase 1
    if($phase1Exit -ne 0){ throw "WSL2 phase 1 could not reach the Windows probe endpoint (exit $phase1Exit). Diagnostic: $phase1Win" }
    if(-not (Test-Path $phase1Win)){ throw "WSL2 phase 1 exited successfully but did not create $phase1Win" }
    $phase1=Get-Content -Raw $phase1Win | ConvertFrom-Json
    if($null -eq $phase1 -or [string]::IsNullOrWhiteSpace([string]$phase1.host_kind)){
        throw "WSL2 phase 1 report did not contain host_kind. Diagnostic: $phase1Win"
    }
    $env:BAI_WSL_EXPECT_HOST_KIND=[string]$phase1.host_kind

    Stop-Process -Id $s1.Id -Force; $s1=$null; Start-Sleep -Milliseconds 500
    $ready2=Join-Path $env:TEMP "bai-wsl-ipc-ready2-$PID.json"; $s2=StartServer $ready2
    $phase2Exit=Invoke-WslPhase 2
    if($phase2Exit -ne 0){ throw "WSL2 phase 2 failed after same-port Windows server restart (exit $phase2Exit). Diagnostic: $phase2Win" }
    if(-not (Test-Path $phase2Win)){ throw "WSL2 phase 2 exited successfully but did not create $phase2Win" }
    Stop-Process -Id $s2.Id -Force; $s2=$null

    & $Python -m ai_video_production.wsl_ipc_report --phase1 $phase1Win --phase2 $phase2Win --output $final
    if($LASTEXITCODE -ne 0){ throw "WSL2 IPC final report validation failed" }
    Write-Host "WSL2-to-Windows IPC Evidence: $final"
} finally {
    if($null -ne $s1){Stop-Process -Id $s1.Id -Force -ErrorAction SilentlyContinue}
    if($null -ne $s2){Stop-Process -Id $s2.Id -Force -ErrorAction SilentlyContinue}
    foreach($name in @('BAI_IPC_PROBE_TOKEN','BAI_WSL_CLIENT_PATH','BAI_WSL_PHASE1_PATH','BAI_WSL_PHASE2_PATH','BAI_WSL_IPC_PORT','BAI_WSL_EXPECT_HOST_KIND','WSLENV')){
        $old=$oldEnv[$name]
        if($null -eq $old){ Remove-Item "Env:$name" -ErrorAction SilentlyContinue } else { Set-Item "Env:$name" $old }
    }
}
