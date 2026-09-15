param(
    [Parameter(Mandatory = $true)]
    [string]$IsccPath,
    [Parameter(Mandatory = $true)]
    [string]$TrainingPayloadRoot,
    [Parameter(Mandatory = $true)]
    [string]$TriviaPayloadRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$Version = '0.24.1'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$compiler = (Resolve-Path -LiteralPath $IsccPath).Path
$iss = Join-Path $repoRoot 'packaging\task092_dbd_utility_installer.iss'
$output = [IO.Path]::GetFullPath($OutputDirectory).TrimEnd('\')
$repoPrefix = $repoRoot.TrimEnd('\') + [IO.Path]::DirectorySeparatorChar
if (-not $output.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Installer output must be contained by the repository worktree: $output"
}
if (Test-Path -LiteralPath $output) {
    throw "Installer output already exists; use a fresh operation directory: $output"
}
$outputParent = Split-Path -Parent $output
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    New-Item -ItemType Directory -Path $outputParent | Out-Null
}
New-Item -ItemType Directory -Path $output | Out-Null

function Get-PayloadTreeSha([string]$PayloadRoot, [string]$ExpectedExecutable) {
    $payload = (Resolve-Path -LiteralPath $PayloadRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $payload $ExpectedExecutable) -PathType Leaf)) {
        throw "Expected executable is missing from payload: $payload / $ExpectedExecutable"
    }
    $files = @(Get-ChildItem -LiteralPath $payload -Recurse -File | Sort-Object FullName)
    if ($files.Count -eq 0) { throw "Payload is empty: $payload" }
    $lines = foreach ($file in $files) {
        $relative = $file.FullName.Substring($payload.Length).TrimStart('\').Replace('\', '/')
        $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        "$relative`t$digest"
    }
    $manifestText = ($lines -join "`n") + "`n"
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $treeSha = ([BitConverter]::ToString(
            $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($manifestText))
        )).Replace('-', '').ToLowerInvariant()
    } finally {
        $hasher.Dispose()
    }
    return [pscustomobject]@{ root = $payload; files = $files.Count; sha256 = $treeSha }
}

$products = @(
    [pscustomobject]@{
        name = 'BAI DbD Training Studio'
        id = 'C6B19B19-D58E-4A73-B97C-BE18FDD5019E'
        executable = 'BAI DbD Training Studio.exe'
        output = "bai-dbd-training-studio-$Version-windows-x64-setup"
        payload = Get-PayloadTreeSha $TrainingPayloadRoot 'BAI DbD Training Studio.exe'
    },
    [pscustomobject]@{
        name = 'BAI DbD Trivia Editor'
        id = 'D419E021-D94F-46F2-92D6-E60533342402'
        executable = 'BAI DbD Trivia Editor.exe'
        output = "bai-dbd-trivia-editor-$Version-windows-x64-setup"
        payload = Get-PayloadTreeSha $TriviaPayloadRoot 'BAI DbD Trivia Editor.exe'
    }
)

$results = @()
foreach ($product in $products) {
    & $compiler "/DAppVersion=$Version" "/DAppName=$($product.name)" "/DAppIdValue=$($product.id)" `
        "/DExecutableName=$($product.executable)" "/DOutputBaseName=$($product.output)" `
        "/DPayloadRoot=$($product.payload.root)" "/DPayloadTreeSha=$($product.payload.sha256)" `
        "/O$output" $iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed for $($product.name): $LASTEXITCODE" }
    $installer = Join-Path $output ($product.output + '.exe')
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw "Expected installer was not produced: $installer"
    }
    $results += [pscustomobject]@{
        product = $product.name
        installer = $installer
        installer_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
        payload_tree_sha256 = $product.payload.sha256
        payload_files = $product.payload.files
    }
}

$results | ConvertTo-Json -Depth 4
