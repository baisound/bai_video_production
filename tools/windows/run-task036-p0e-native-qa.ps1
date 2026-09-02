param(
  [string]$ExpectedSourceCommit,
  [string]$ExpectedFixtureSourceSha256,
  [string]$ExpectedPackageExecutableSha256,
  [string]$ExpectedPackageTreeSha256,
  [string]$FixtureContractVersion = 'task036-p0e-fixture/v1'
)

$ErrorActionPreference = 'Stop'

trap {
  $code = [string]$_.Exception.Message
  if ($code -notmatch '^ERR_TASK036_P0E_[A-Z0-9_]+$') {
    $code = 'ERR_TASK036_P0E_INTERNAL'
  }
  Write-Output ('[ERROR] ' + $code)
  exit 2
}

function Fail([string]$Code) {
  throw $Code
}

function Require-Sha256([string]$Value) {
  if ($Value -notmatch '^sha256:[0-9a-f]{64}$') {
    Fail 'ERR_TASK036_P0E_EXPECTED_DIGEST_INVALID'
  }
}

if ($ExpectedSourceCommit -notmatch '^[0-9a-f]{40}$') {
  Fail 'ERR_TASK036_P0E_EXPECTED_SOURCE_COMMIT_INVALID'
}
if ($FixtureContractVersion -ne 'task036-p0e-fixture/v1') {
  Fail 'ERR_TASK036_P0E_FIXTURE_VERSION_INVALID'
}
Require-Sha256 $ExpectedFixtureSourceSha256
Require-Sha256 $ExpectedPackageExecutableSha256
Require-Sha256 $ExpectedPackageTreeSha256

$projection = [ordered]@{
  receipt_version = 'task036-p0e-native-qa/v1'
  task = 'TASK-036'
  unit = 'P0-E'
  startup_integration_contract = 'TASK036-P0E-AI-SETTINGS-STARTUP-INTEGRATION-V1'
  state = 'PREPARED'
  technical_result = 'NOT_CONFIRMED'
  authority_created = $false
  expected_source_commit = $ExpectedSourceCommit
  source_commit_verified = $false
  fixture_contract_version = $FixtureContractVersion
  expected_fixture_source_sha256 = $ExpectedFixtureSourceSha256
  fixture_snapshot_verified = $false
  expected_package_executable_sha256 = $ExpectedPackageExecutableSha256
  expected_package_tree_sha256 = $ExpectedPackageTreeSha256
  package_snapshot_verified = $false
  receipt_persisted = $false
  task063_terminal_handoff_consumed = $false
  packaged_entry_binding_started = $false
  first_run_binding_started = $false
  single_instance_binding_started = $false
  startup_error_readback_started = $false
  model_setting_persistence_readback_started = $false
  native_execution_started = $false
  provider_execution_started = $false
  paid_execution_authorized = $false
  download_or_install_started = $false
  export_dispatch_started = $false
  resolve_mutation_started = $false
  release_or_deploy_started = $false
  production_activation_started = $false
  host_path_persisted = $false
}

Write-Output ($projection | ConvertTo-Json -Depth 4 -Compress)
