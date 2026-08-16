param(
  [Parameter(Mandatory=$true)][string]$InputRoot,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][ValidateSet('SOURCE','RUNTIME')][string]$PackageKind,
  [Parameter(Mandatory=$true)][string]$Version
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = (Resolve-Path -LiteralPath $InputRoot).Path
$files = @(Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File | Sort-Object FullName | ForEach-Object {
  $relative = [IO.Path]::GetRelativePath($resolvedRoot, $_.FullName).Replace('\','/')
  [ordered]@{
    path = $relative
    bytes = $_.Length
    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  }
})
if ($files.Count -eq 0) { throw 'Manifest input set is empty' }

$manifest = [ordered]@{
  schema = 'BAI_OBS_PLUGIN_PACKAGE_MANIFEST_V1'
  module = 'bai-voice-capture'
  version = $Version
  kind = $PackageKind
  target = 'windows-x64-obs-32.2.1'
  license = 'GPL-2.0-or-later'
  file_count = $files.Count
  files = $files
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "MANIFEST_PASS kind=$PackageKind files=$($files.Count)"
