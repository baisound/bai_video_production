from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_wsl_runner_uses_wslenv_path_translation_not_wslpath_direct_argument():
    text = (ROOT / 'tools/windows/run-wsl2-ipc-probe.ps1').read_text(encoding='utf-8')
    assert 'WSLENV /p translation' in text
    assert 'BAI_WSL_CLIENT_PATH' in text
    assert 'BAI_WSL_PHASE1_PATH' in text
    assert 'BAI_WSL_PHASE2_PATH' in text
    assert 'Add-WslEnvEntry "BAI_WSL_CLIENT_PATH" $true' in text
    assert 'wslpath' not in text.lower()


def test_wsl_runner_validates_phase1_before_reading_host_kind():
    text = (ROOT / 'tools/windows/run-wsl2-ipc-probe.ps1').read_text(encoding='utf-8')
    assert 'if(-not (Test-Path $phase1Win))' in text
    assert 'phase 1 report did not contain host_kind' in text
    assert '$env:BAI_WSL_EXPECT_HOST_KIND=[string]$phase1.host_kind' in text


def test_wsl_runner_restores_temporary_bridge_environment():
    text = (ROOT / 'tools/windows/run-wsl2-ipc-probe.ps1').read_text(encoding='utf-8')
    for name in (
        'BAI_IPC_PROBE_TOKEN',
        'BAI_WSL_CLIENT_PATH',
        'BAI_WSL_PHASE1_PATH',
        'BAI_WSL_PHASE2_PATH',
        'BAI_WSL_IPC_PORT',
        'BAI_WSL_EXPECT_HOST_KIND',
        'WSLENV',
    ):
        assert name in text
    assert 'foreach($name in' in text


def test_sandbox_runner_surfaces_structured_diagnostic_on_failure():
    text = (ROOT / 'tools/windows/run-resolve-sandbox-mutation-probe.ps1').read_text(encoding='utf-8')
    assert 'Show-ProbeDiagnostic' in text
    assert '$diagnostic.mutation_error' in text
    assert '$diagnostic.connection_error' in text
    assert 'Failure code:' in text
    assert 'Category:' in text
    assert 'Message:' in text
    assert 'Diagnostic Evidence:' in text


def test_sandbox_runner_keeps_fail_closed_acknowledgement_and_sandbox_prefix():
    text = (ROOT / 'tools/windows/run-resolve-sandbox-mutation-probe.ps1').read_text(encoding='utf-8')
    assert 'IUnderstandThisCreatesSandboxProject' in text
    assert 'BAI_CAPABILITY_PROBE_' in text
    assert 'fails closed' in text
    assert "'^BAI_CAPABILITY_PROBE_[A-Za-z0-9_-]+$'" in text
    assert '--probe-assets-dir $assetDir' in text
    assert 'Probe assets retained:' in text


def test_task004_audacity_behavior_runner_is_synthetic_and_bounded():
    text = (ROOT / 'tools/windows/run-task004-audacity-openvino-behavior-probe.ps1').read_text(encoding='utf-8')
    assert 'synthetic probe audio only' in text
    assert 'current Audacity project MUST be empty' in text
    assert '--timeout-seconds $TimeoutSeconds' in text
    assert 'task004-live-evidence-behavior' in text
    assert 'do not modify or reinstall audacity/openvino' in text.lower()
    assert 'Resolve-FFprobeExecutable' in text
    assert 'BAI_FFPROBE_EXECUTABLE' in text
    assert '--ffprobe-executable $ffprobe' in text
    assert 'will not bypass canonical media validation' in text
