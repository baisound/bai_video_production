param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [Parameter(Mandatory = $true)]
    [string]$InnoCompiler,
    [Parameter(Mandatory = $true)]
    [string]$WorkRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$AppVersion = '0.1.0-dev.1-installer.1',
    [string]$ExpectedPythonSha256 = '',
    [string]$ExpectedCompilerSha256 = 'd06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a'
)

$ErrorActionPreference = 'Stop'

function Assert-AbsoluteFile([string]$Path, [string]$Label) {
    if (-not [IO.Path]::IsPathRooted($Path)) { throw "$Label must be an absolute path: $Path" }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Label was not found: $Path" }
}

Assert-AbsoluteFile $PythonExe 'PythonExe'
Assert-AbsoluteFile $InnoCompiler 'InnoCompiler'
if (-not [IO.Path]::IsPathRooted($WorkRoot)) { throw "WorkRoot must be absolute: $WorkRoot" }
if (-not [IO.Path]::IsPathRooted($OutputDirectory)) { throw "OutputDirectory must be absolute: $OutputDirectory" }
if (Test-Path -LiteralPath $WorkRoot) { throw "WorkRoot must not already exist: $WorkRoot" }
if (Test-Path -LiteralPath $OutputDirectory) { throw "OutputDirectory must not already exist: $OutputDirectory" }

$pythonHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $PythonExe).Hash.ToLowerInvariant()
if ($ExpectedPythonSha256 -and $pythonHash -ne $ExpectedPythonSha256.ToLowerInvariant()) {
    throw "Python hash mismatch: $pythonHash"
}
$compilerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $InnoCompiler).Hash.ToLowerInvariant()
if ($compilerHash -ne $ExpectedCompilerSha256.ToLowerInvariant()) {
    throw "ISCC hash mismatch: $compilerHash"
}
$pyInstallerVersion = (& $PythonExe -c 'import PyInstaller; print(PyInstaller.__version__)').Trim()
if ($LASTEXITCODE -ne 0 -or $pyInstallerVersion -ne '6.22.0') {
    throw "PyInstaller 6.22.0 is required; observed: $pyInstallerVersion"
}
$jsonschemaVersion = (& $PythonExe -c "from importlib.metadata import version; print(version('jsonschema'))").Trim()
if ($LASTEXITCODE -ne 0 -or -not $jsonschemaVersion) {
    throw 'The project runtime dependency jsonschema is required'
}

$sourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$launcher = Join-Path $sourceRoot 'tools\windows\task046_voice_model_builder_launcher.py'
$installerScript = Join-Path $sourceRoot 'packaging\task046_voice_model_builder_installer.iss'
$noticesCollector = Join-Path $sourceRoot 'tools\windows\task046_collect_third_party_notices.py'
$guide = Join-Path $sourceRoot 'docs\user\VOICE-MODEL-BUILDER.md'
$license = Join-Path $sourceRoot 'LICENSE.md'
foreach ($entry in @($launcher, $installerScript, $noticesCollector, $guide, $license)) {
    Assert-AbsoluteFile $entry 'Source input'
}

$distRoot = Join-Path $WorkRoot 'pyinstaller-dist'
$pyWork = Join-Path $WorkRoot 'pyinstaller-work'
$specRoot = Join-Path $WorkRoot 'pyinstaller-spec'
$payloadRoot = Join-Path $WorkRoot 'payload'
$applicationRoot = Join-Path $payloadRoot 'application'
$docsRoot = Join-Path $payloadRoot 'docs'
New-Item -ItemType Directory -Path $distRoot, $pyWork, $specRoot, $applicationRoot, $docsRoot, $OutputDirectory -Force | Out-Null

$savedErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$pyInstallerOutput = & $PythonExe -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name bai-voice-model-builder `
    --paths (Join-Path $sourceRoot 'src') `
    --collect-data ai_video_production `
    --distpath $distRoot --workpath $pyWork --specpath $specRoot `
    $launcher 2>&1
$pyInstallerExitCode = $LASTEXITCODE
$ErrorActionPreference = $savedErrorPreference
if ($pyInstallerExitCode -ne 0) {
    $pyInstallerOutput | ForEach-Object { Write-Error $_ }
    throw "PyInstaller failed with exit code $pyInstallerExitCode"
}

$builtExe = Join-Path $distRoot 'bai-voice-model-builder.exe'
Assert-AbsoluteFile $builtExe 'Packaged executable'
$payloadExe = Join-Path $applicationRoot 'bai-voice-model-builder.exe'
Copy-Item -LiteralPath $builtExe -Destination $payloadExe
Copy-Item -LiteralPath $guide -Destination (Join-Path $docsRoot 'VOICE-MODEL-BUILDER.md')
Copy-Item -LiteralPath $license -Destination (Join-Path $payloadRoot 'LICENSE.md')
$noticePath = Join-Path $payloadRoot 'THIRD-PARTY-NOTICES.txt'
$noticeReceiptJson = & $PythonExe $noticesCollector --output $noticePath
if ($LASTEXITCODE -ne 0) { throw 'Third-party notice collection failed' }
$noticeReceipt = $noticeReceiptJson | ConvertFrom-Json
if ($noticeReceipt.private_path_exposed -ne $false) { throw 'Third-party notice exposed a private path' }

$payloadItems = @(
    [ordered]@{ path = 'application/bai-voice-model-builder.exe'; bytes = (Get-Item -LiteralPath $payloadExe).Length; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $payloadExe).Hash.ToLowerInvariant() },
    [ordered]@{ path = 'docs/VOICE-MODEL-BUILDER.md'; bytes = (Get-Item -LiteralPath (Join-Path $docsRoot 'VOICE-MODEL-BUILDER.md')).Length; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $docsRoot 'VOICE-MODEL-BUILDER.md')).Hash.ToLowerInvariant() },
    [ordered]@{ path = 'LICENSE.md'; bytes = (Get-Item -LiteralPath (Join-Path $payloadRoot 'LICENSE.md')).Length; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $payloadRoot 'LICENSE.md')).Hash.ToLowerInvariant() },
    [ordered]@{ path = 'THIRD-PARTY-NOTICES.txt'; bytes = (Get-Item -LiteralPath $noticePath).Length; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $noticePath).Hash.ToLowerInvariant() }
)
$manifest = [ordered]@{
    schema_version = 1
    task = 'TASK-046/P-VS-4B'
    product = 'BAI Voice Model Builder'
    version = $AppVersion
    platform = 'windows-x64'
    python_sha256 = $pythonHash
    pyinstaller_version = $pyInstallerVersion
    jsonschema_version = $jsonschemaVersion
    iscc_sha256 = $compilerHash
    third_party_notice_sha256 = $noticeReceipt.notice_sha256
    third_party_components = @($noticeReceipt.components | ForEach-Object { [ordered]@{ component = $_.component; version = $_.version; license = $_.license; source_license_sha256 = $_.sha256 } })
    payload = $payloadItems
    installer_launches_application = $false
    model_download_started = $false
    training_started = $false
    audio_access_started = $false
    recording_started = $false
    publication_started = $false
}
$manifestPath = Join-Path $payloadRoot 'package-manifest.json'
$manifestJson = $manifest | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($manifestPath, $manifestJson + "`n", [Text.UTF8Encoding]::new($false))

$executableSha = $payloadItems[0].sha256
$guideSha = $payloadItems[1].sha256
$licenseSha = $payloadItems[2].sha256
$noticeSha = $payloadItems[3].sha256
$manifestSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
$ErrorActionPreference = 'Continue'
$compileOutput = & $InnoCompiler `
    "/DPayloadRoot=$payloadRoot" "/DAppVersion=$AppVersion" `
    "/DExecutableSha=$executableSha" "/DGuideSha=$guideSha" `
    "/DLicenseSha=$licenseSha" "/DManifestSha=$manifestSha" "/DNoticeSha=$noticeSha" `
    "/O$OutputDirectory" $installerScript 2>&1
$isccExitCode = $LASTEXITCODE
$ErrorActionPreference = $savedErrorPreference
if ($isccExitCode -ne 0) {
    $compileOutput | ForEach-Object { Write-Error $_ }
    throw "ISCC failed with exit code $isccExitCode"
}

$installerPath = Join-Path $OutputDirectory "bai-voice-model-builder-$AppVersion-windows-x64-setup.exe"
Assert-AbsoluteFile $installerPath 'Compiled installer'
$result = [ordered]@{
    schema_version = 1
    task = 'TASK-046/P-VS-4B-BEGINNER-CLIENT-RELEASE-R2'
    app_version = $AppVersion
    python_sha256 = $pythonHash
    pyinstaller_version = $pyInstallerVersion
    jsonschema_version = $jsonschemaVersion
    iscc_sha256 = $compilerHash
    executable_bytes = (Get-Item -LiteralPath $payloadExe).Length
    executable_sha256 = $executableSha
    package_manifest_sha256 = $manifestSha
    third_party_notice_sha256 = $noticeSha
    third_party_component_count = @($noticeReceipt.components).Count
    installer_path = $installerPath
    installer_bytes = (Get-Item -LiteralPath $installerPath).Length
    installer_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $installerPath).Hash.ToLowerInvariant()
    installer_authenticode = [string](Get-AuthenticodeSignature -LiteralPath $installerPath).Status
    external_download_performed = $false
    application_launched = $false
    model_download_started = $false
    training_started = $false
    audio_access_started = $false
    publication_started = $false
}
$result | ConvertTo-Json -Depth 6
