param(
    [Parameter(Mandatory=$false)][string]$Python = "python",
    [Parameter(Mandatory=$false)][string]$OutputDir = ".\resolve-spike-evidence"
)
$ErrorActionPreference = "Stop"
$repoRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$srcRoot=Join-Path $repoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $env:PYTHONPATH=$srcRoot } else { $env:PYTHONPATH="$srcRoot;$($env:PYTHONPATH)" }
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$serverScript=Join-Path $PSScriptRoot "wsl-http-probe-server.py"
$clientWin=Join-Path $repoRoot "tools\wsl\http-ipc-client.py"
$phase1Win=Join-Path $OutputDir "wsl-ipc-phase1.json"; $phase2Win=Join-Path $OutputDir "wsl-ipc-phase2.json"; $final=Join-Path $OutputDir "resolve-wsl-ipc-probe-report.json"
$listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0); $listener.Start(); $port=([System.Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
$token=[Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")
$oldToken=$env:BAI_IPC_PROBE_TOKEN; $oldWSLENV=$env:WSLENV; $env:BAI_IPC_PROBE_TOKEN=$token
$s1=$null; $s2=$null
if ([string]::IsNullOrWhiteSpace($env:WSLENV)) { $env:WSLENV="BAI_IPC_PROBE_TOKEN" } elseif ($env:WSLENV -notmatch 'BAI_IPC_PROBE_TOKEN') { $env:WSLENV="$($env:WSLENV):BAI_IPC_PROBE_TOKEN" }
function WslPath([string]$p) { return (& wsl.exe wslpath -a $p).Trim() }
$client=WslPath $clientWin; $p1=WslPath $phase1Win; $p2=WslPath $phase2Win
function StartServer([string]$ready) {
    if (Test-Path $ready) { Remove-Item $ready -Force }
    $proc=Start-Process -FilePath $Python -ArgumentList @("`"$serverScript`"",'--port',"$port",'--ready-file',"`"$ready`"") -PassThru -WindowStyle Hidden
    for($i=0;$i -lt 50;$i++){ if(Test-Path $ready){return $proc}; Start-Sleep -Milliseconds 100 }
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; throw "Probe server did not become ready"
}
try {
    $ready1=Join-Path $env:TEMP "bai-wsl-ipc-ready1-$PID.json"; $s1=StartServer $ready1
    & wsl.exe python3 $client --port $port --phase 1 --output $p1
    if($LASTEXITCODE -ne 0){ throw "WSL2 phase 1 could not reach the Windows probe endpoint" }
    $phase1=Get-Content -Raw $phase1Win | ConvertFrom-Json
    Stop-Process -Id $s1.Id -Force; $s1=$null; Start-Sleep -Milliseconds 500
    $ready2=Join-Path $env:TEMP "bai-wsl-ipc-ready2-$PID.json"; $s2=StartServer $ready2
    & wsl.exe python3 $client --port $port --phase 2 --output $p2 --expect-host-kind $phase1.host_kind
    if($LASTEXITCODE -ne 0){ throw "WSL2 phase 2 failed after same-port Windows server restart" }
    Stop-Process -Id $s2.Id -Force; $s2=$null
    & $Python -m ai_video_production.wsl_ipc_report --phase1 $phase1Win --phase2 $phase2Win --output $final
    if($LASTEXITCODE -ne 0){ throw "WSL2 IPC final report validation failed" }
    Write-Host "WSL2-to-Windows IPC Evidence: $final"
} finally {
    if($null -ne $s1){Stop-Process -Id $s1.Id -Force -ErrorAction SilentlyContinue}
    if($null -ne $s2){Stop-Process -Id $s2.Id -Force -ErrorAction SilentlyContinue}
    if($null -eq $oldToken){Remove-Item Env:BAI_IPC_PROBE_TOKEN -ErrorAction SilentlyContinue}else{$env:BAI_IPC_PROBE_TOKEN=$oldToken}
    if($null -eq $oldWSLENV){Remove-Item Env:WSLENV -ErrorAction SilentlyContinue}else{$env:WSLENV=$oldWSLENV}
}
