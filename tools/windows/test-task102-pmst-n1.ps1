param(
    [ValidateSet('N1A', 'N1B')]
    [string]$Phase = 'N1A',
    [string]$RunId = ([Guid]::NewGuid().ToString('N')),
    [string]$ExternalEvidenceRoot = 'C:\home\baisound\evidence\bai-video-production\TASK-102\pmst-n1',
    [switch]$ElevatedInternal
)

$ErrorActionPreference = 'Stop'
$tempCandidate = if ($Phase -eq 'N1B') {
    [Environment]::ExpandEnvironmentVariables([Environment]::GetEnvironmentVariable('TEMP', 'Machine'))
}
else {
    [IO.Path]::GetTempPath()
}
$tempRoot = [IO.Path]::GetFullPath($tempCandidate).TrimEnd('\')
$runRoot = Join-Path $tempRoot ("bvp-task102-pmst-n1-{0}" -f $RunId)
$evidenceRoot = Join-Path $ExternalEvidenceRoot $RunId
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$harnessPath = Join-Path $repositoryRoot 'src\ai_video_production\task102_windows_feasibility.py'

if ([IO.Path]::GetPathRoot($runRoot).TrimEnd('\') -eq $runRoot.TrimEnd('\')) { throw 'DRIVE_ROOT_PLACEMENT_REJECTED' }
if ((Split-Path -Parent $runRoot) -ne $tempRoot) { throw 'RUN_ROOT_NOT_DIRECT_TEMP_CHILD' }
if (Test-Path -LiteralPath $runRoot) { throw 'RUN_ROOT_ALREADY_EXISTS' }
if ($RunId -notmatch '^[A-Za-z0-9-]{16,64}$') { throw 'RUN_ID_REJECTED' }

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-CurrentSid { return [Security.Principal.WindowsIdentity]::GetCurrent().User.Value }

function Get-TextSha256([string]$Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    $digest = [Security.Cryptography.SHA256]::HashData($bytes)
    return 'sha256:' + [Convert]::ToHexString($digest).ToLowerInvariant()
}

function Invoke-Icacls([string[]]$Arguments) {
    & icacls.exe @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'ACL_APPLY_FAILED' }
}

function Test-Denied([scriptblock]$Operation) {
    try { & $Operation; return $false }
    catch [System.UnauthorizedAccessException] { return $true }
    catch [System.IO.IOException] { return $true }
}

function Test-ExactControlAcl(
    [System.Security.AccessControl.DirectorySecurity]$Acl,
    [string]$ServiceSid,
    [string]$ClientSid
) {
    if (-not $Acl.AreAccessRulesProtected) { return $false }
    $expected = @{
        $ServiceSid = [int][Security.AccessControl.FileSystemRights]::FullControl
        $ClientSid = [int]([Security.AccessControl.FileSystemRights]::ReadAndExecute -bor [Security.AccessControl.FileSystemRights]::Synchronize)
        'S-1-5-18' = [int]([Security.AccessControl.FileSystemRights]::ReadAndExecute -bor [Security.AccessControl.FileSystemRights]::Synchronize)
        'S-1-5-32-544' = [int]([Security.AccessControl.FileSystemRights]::ReadAndExecute -bor [Security.AccessControl.FileSystemRights]::Synchronize)
    }
    $observed = @{}
    foreach ($rule in @($Acl.Access)) {
        if ($rule.IsInherited -or $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow) { return $false }
        $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        if ($observed.ContainsKey($sid)) { return $false }
        $observed[$sid] = [int]$rule.FileSystemRights
    }
    if ($observed.Count -ne $expected.Count) { return $false }
    foreach ($sid in $expected.Keys) {
        if (-not $observed.ContainsKey($sid) -or $observed[$sid] -ne $expected[$sid]) { return $false }
    }
    return $true
}

function Invoke-N1A {
    $reportPath = Join-Path $runRoot 'pmst-n1a-report.json'
    python $harnessPath --run-root $runRoot --report $reportPath
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $reportPath) { Get-Content -Raw -LiteralPath $reportPath }
        throw 'PMST_N1A_FAILED'
    }
    New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
    $externalReport = Join-Path $evidenceRoot 'pmst-n1a-report.json'
    Copy-Item -LiteralPath $reportPath -Destination $externalReport
    $readback = Get-Content -Raw -LiteralPath $externalReport | ConvertFrom-Json
    if ($readback.result -ne 'PASS') { throw 'EVIDENCE_READBACK_FAILED' }
    $reportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $externalReport).Hash
    $checkpoint = [ordered]@{
        task = 'TASK-102'; atomic_unit = 'PMST-N1A'; run_id = $RunId; technical_result = 'PASS'
        resolved_temp_root = $runRoot; resolved_external_evidence_root = $evidenceRoot
        report_sha256 = "sha256:$($reportHash.ToLowerInvariant())"
        intentional_residuals = @($runRoot, $evidenceRoot)
        prohibited_effects = @('real Project mutation', 'service installation', 'Release', 'Deploy', 'Production')
    }
    $checkpointPath = Join-Path $evidenceRoot 'checkpoint.json'
    $checkpoint | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $checkpointPath -Encoding utf8
    $null = Get-Content -Raw -LiteralPath $checkpointPath | ConvertFrom-Json
    [ordered]@{ result = 'PASS'; run_id = $RunId; temp_root = $runRoot; evidence_root = $evidenceRoot; report_sha256 = "sha256:$($reportHash.ToLowerInvariant())" } | ConvertTo-Json -Compress
}

function Invoke-N1B {
    if (-not (Test-IsAdministrator)) { throw 'BLOCKED_PRIVILEGE' }
    if (-not $ElevatedInternal) { throw 'ELEVATED_INTERNAL_MARKER_REQUIRED' }

    $suffix = ([Guid]::NewGuid().ToString('N')).Substring(0, 16)
    $serviceName = "BvpTask102PmstN1-$suffix"
    $pipeName = "\\.\pipe\$serviceName"
    $controlRoot = Join-Path $runRoot 'control'
    $workerPath = Join-Path $runRoot 'task102-windows-feasibility-worker.py'
    $externalReport = Join-Path $evidenceRoot 'pmst-n1b-report.json'
    $checkpointPath = Join-Path $evidenceRoot 'checkpoint.json'
    $serviceCreated = $false; $serviceDeleted = $false
    $result = 'FAIL'; $reason = 'N1B_UNEXPECTED_FAILURE'
    $proof = $null; $client = $null
    $configurationReadback = $false
    $exactDaclReadback = $false
    $peerCreateDenied = $false; $peerOverwriteDenied = $false
    $peerDeleteDenied = $false; $peerRenameDenied = $false

    New-Item -ItemType Directory -Path $runRoot | Out-Null
    New-Item -ItemType Directory -Path $controlRoot | Out-Null
    New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
    Copy-Item -LiteralPath $harnessPath -Destination $workerPath

    try {
        & sc.exe query $serviceName *> $null
        if ($LASTEXITCODE -eq 0) { throw 'SERVICE_NAME_COLLISION' }
        & sc.exe create $serviceName type= own start= demand error= normal binPath= 'cmd.exe /c exit 91' DisplayName= $serviceName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'SERVICE_CREATE_FAILED' }
        $serviceCreated = $true
        & sc.exe sidtype $serviceName unrestricted | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'SERVICE_SIDTYPE_FAILED' }
        $serviceAccount = "NT SERVICE\$serviceName"
        $serviceSid = ([Security.Principal.NTAccount]::new($serviceAccount)).Translate([Security.Principal.SecurityIdentifier]).Value
        $clientSid = Get-CurrentSid
        $pythonPath = (Get-Command python).Source
        $binPath = "`"$pythonPath`" `"$workerPath`" --service-worker $serviceName `"$controlRoot`" `"$pipeName`" $serviceSid $clientSid"
        # Keep the SCM default LocalSystem identity. SYSTEM receives read/execute
        # only below; the service-specific SID is the sole Full-control ACE.
        & sc.exe config $serviceName binPath= $binPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'SERVICE_CONFIG_FAILED' }
        $serviceKey = Get-ItemProperty -LiteralPath "Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\$serviceName"
        if (
            $serviceKey.ImagePath -ne $binPath -or
            $serviceKey.ObjectName -ne 'LocalSystem' -or
            [int]$serviceKey.Start -ne 3 -or
            [int]$serviceKey.Type -ne 16 -or
            [int]$serviceKey.ServiceSidType -ne 1
        ) { throw 'SERVICE_CONFIG_READBACK_FAILED' }
        $configurationReadback = $true

        Invoke-Icacls @($controlRoot, '/inheritance:r', '/grant:r', "*$serviceSid`:(OI)(CI)F", "*$clientSid`:(OI)(CI)RX", '*S-1-5-18:(OI)(CI)RX', '*S-1-5-32-544:(OI)(CI)RX')
        Invoke-Icacls @($runRoot, '/inheritance:r', '/grant:r', "*$serviceSid`:(OI)(CI)RX", "*$clientSid`:(OI)(CI)RX", '*S-1-5-18:(OI)(CI)RX', '*S-1-5-32-544:(OI)(CI)RX')
        $controlAcl = Get-Acl -LiteralPath $controlRoot
        $exactDaclReadback = Test-ExactControlAcl $controlAcl $serviceSid $clientSid
        if (-not $exactDaclReadback) { throw 'ACL_TOPOLOGY_UNPROVEN' }
        $aclDigest = Get-TextSha256 $controlAcl.Sddl

        $peerCreateDenied = Test-Denied { [IO.File]::WriteAllText((Join-Path $controlRoot 'peer-create.txt'), 'peer') }
        if (-not $peerCreateDenied) { throw 'PEER_WRITE_NOT_DENIED' }
        & sc.exe start $serviceName | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'SERVICE_START_FAILED' }
        $servicePid = 0
        for ($attempt = 0; $attempt -lt 100; $attempt++) {
            $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'"
            if ($service.ProcessId -gt 0) { $servicePid = [int]$service.ProcessId; break }
            if (Test-Path -LiteralPath (Join-Path $controlRoot 'service-failure.json')) { break }
            Start-Sleep -Milliseconds 100
        }
        if ($servicePid -le 0) { throw 'SERVICE_PID_UNAVAILABLE' }
        $clientOutput = & python $workerPath --n1b-client $pipeName $servicePid
        if ($LASTEXITCODE -ne 0) { throw 'SERVICE_PIPE_CLIENT_FAILED' }
        $client = $clientOutput | ConvertFrom-Json
        $proofPath = Join-Path $controlRoot 'service-proof.json'
        for ($attempt = 0; $attempt -lt 100 -and -not (Test-Path -LiteralPath $proofPath); $attempt++) { Start-Sleep -Milliseconds 100 }
        if (-not (Test-Path -LiteralPath $proofPath)) { throw 'SERVICE_PROOF_MISSING' }
        $proof = Get-Content -Raw -LiteralPath $proofPath | ConvertFrom-Json
        if (-not $proof.service_sid_present -or $proof.server_pid -ne $servicePid) { throw 'SERVICE_SID_BINDING_UNPROVEN' }
        if ($client.server_pid -ne $servicePid -or $client.client_pid_observed -ne $proof.client_pid) { throw 'PIPE_IDENTITY_UNPROVEN' }

        $peerOverwriteDenied = Test-Denied { [IO.File]::WriteAllText($proofPath, 'peer-overwrite') }
        $peerDeleteDenied = Test-Denied { Remove-Item -LiteralPath $proofPath -Force }
        $peerRenameDenied = Test-Denied { Move-Item -LiteralPath $controlRoot -Destination ($controlRoot + '-moved') }
        if (-not ($peerOverwriteDenied -and $peerDeleteDenied -and $peerRenameDenied)) { throw 'PEER_MUTATION_NOT_DENIED' }
        $finalAcl = Get-Acl -LiteralPath $controlRoot
        if (-not $finalAcl.AreAccessRulesProtected -or (Get-TextSha256 $finalAcl.Sddl) -ne $aclDigest) { throw 'ACL_TOPOLOGY_UNPROVEN' }
        $result = 'PASS'; $reason = 'NONE'
    }
    catch {
        $reason = if ($_.Exception.Message -match '^[A-Z0-9_]+$') { $_.Exception.Message } else { 'N1B_UNEXPECTED_FAILURE' }
    }
    finally {
        if ($serviceCreated) {
            & sc.exe stop $serviceName *> $null
            for ($attempt = 0; $attempt -lt 50; $attempt++) {
                $state = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
                if ($null -eq $state -or $state.State -eq 'Stopped') { break }
                Start-Sleep -Milliseconds 100
            }
            & sc.exe delete $serviceName | Out-Null
            if ($LASTEXITCODE -eq 0) {
                for ($attempt = 0; $attempt -lt 50; $attempt++) {
                    if ($null -eq (Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue)) { $serviceDeleted = $true; break }
                    Start-Sleep -Milliseconds 100
                }
            }
        }
    }

    $report = [ordered]@{
        report_version = 'TASK102_PMST_N1B_REPORT_V1'; result = $result; reason_code = $reason
        service_name_sha256 = Get-TextSha256 $serviceName
        service_sid_sha256 = if ($null -ne $proof) { $proof.service_sid_sha256 } else { $null }
        service_created = $serviceCreated; service_deleted = $serviceDeleted
        configuration_readback = $configurationReadback
        exact_dacl_readback = $exactDaclReadback
        service_sid_present = if ($null -ne $proof) { [bool]$proof.service_sid_present } else { $false }
        protected_dacl = if (Test-Path -LiteralPath $controlRoot) { [bool](Get-Acl -LiteralPath $controlRoot).AreAccessRulesProtected } else { $false }
        peer_create_denied = [bool]$peerCreateDenied; peer_overwrite_denied = [bool]$peerOverwriteDenied
        peer_delete_denied = [bool]$peerDeleteDenied; peer_rename_denied = [bool]$peerRenameDenied
        pipe_server_client_pid_readback = ($null -ne $client -and $null -ne $proof)
        pipe_first_instance_and_remote_rejection_configured = ($null -ne $client)
        run_root_class = 'UNIQUE_SYSTEM_TEMP_CHILD'
        residuals = @('OWNED_RUN_ROOT_RETAINED_FOR_EVIDENCE', 'EXTERNAL_EVIDENCE_RETAINED')
    }
    $report | ConvertTo-Json -Depth 8 -Compress | Set-Content -LiteralPath $externalReport -Encoding utf8
    $readback = Get-Content -Raw -LiteralPath $externalReport | ConvertFrom-Json
    if ($readback.result -ne $result) { throw 'EVIDENCE_READBACK_FAILED' }
    $reportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $externalReport).Hash.ToLowerInvariant()
    $checkpoint = [ordered]@{
        task = 'TASK-102'; atomic_unit = 'PMST-N1B'; run_id = $RunId; technical_result = $result; reason_code = $reason
        resolved_temp_root = $runRoot; resolved_external_evidence_root = $evidenceRoot; report_sha256 = "sha256:$reportHash"
        intentional_residuals = @($runRoot, $evidenceRoot)
        service_cleanup = if ($serviceDeleted) { 'PASS' } else { 'RESIDUAL_REQUIRES_HUMAN_RECOVERY' }
        prohibited_effects = @('real Project mutation', 'existing service or ACL mutation', 'Release', 'Deploy', 'Production')
    }
    $checkpoint | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $checkpointPath -Encoding utf8
    $null = Get-Content -Raw -LiteralPath $checkpointPath | ConvertFrom-Json
    $report | ConvertTo-Json -Compress
    if ($result -ne 'PASS' -or -not $serviceDeleted) { exit 1 }
}

if ($Phase -eq 'N1A') { Invoke-N1A; exit 0 }
if (-not (Test-IsAdministrator)) {
    if ($ElevatedInternal) { throw 'BLOCKED_PRIVILEGE' }
    $pwsh = (Get-Process -Id $PID).Path
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Phase N1B -RunId $RunId -ExternalEvidenceRoot `"$ExternalEvidenceRoot`" -ElevatedInternal"
    $process = Start-Process -FilePath $pwsh -Verb RunAs -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'PMST_N1B_ELEVATED_RUN_FAILED' }
    Get-Content -Raw -LiteralPath (Join-Path $evidenceRoot 'pmst-n1b-report.json')
    exit 0
}
Invoke-N1B
