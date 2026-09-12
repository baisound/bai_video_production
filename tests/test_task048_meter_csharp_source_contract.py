"""C# source/golden checks only; compiler and native runtime are NOT_EXECUTED."""
import ast
from hashlib import sha256
from pathlib import Path
import re

import pytest

from ai_video_production import task048_meter_protocol as p

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native/task047_obs_voice_capture/controller/BaiMeterRuntimeBridge.cs"
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse((ROOT / "tests/test_task048_meter_protocol.py").read_text(encoding="utf-8"))
GOLDEN = next(ast.literal_eval(node.value) for node in TREE.body
              if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GOLDEN" for t in node.targets))
CS_GOLDEN = {name: (int(length), digest, data) for name, length, digest, data in re.findall(
    r'new BaiMeterGolden\("([A-Z_]+)", ([0-9]+), "([0-9a-f]{64})", "([0-9a-f]+)"\)', TEXT)}


@pytest.mark.parametrize("name", list(GOLDEN))
def test_csharp_seven_literal_vectors_match_independent_design(name):
    assert CS_GOLDEN[name] == GOLDEN[name]
    length, digest, literal = CS_GOLDEN[name]
    data = bytes.fromhex(literal)
    assert len(data) == length and sha256(data).hexdigest() == digest
    # This is Python validation of C# source literals, NOT C# execution.
    assert p.decode_message(data).wire == data


def code_tokens(text):
    """Small literal/comment skipper for static delimiter checks, not a compiler."""
    i, result = 0, []
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i+2)
            assert end >= 0
            i = end + 2
        elif text.startswith('@"', i):
            i += 2
            while i < len(text):
                if text.startswith('""', i):
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                pytest.fail("Unterminated C# verbatim string")
        elif text[i] in "\"'":
            quote = text[i]
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                pytest.fail("Unterminated C# literal")
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def test_csharp_source_has_balanced_delimiters_without_claiming_compilation():
    stack = []
    closing = {")": "(", "]": "[", "}": "{"}
    for token in code_tokens(TEXT):
        if token in "([{":
            stack.append(token)
        elif token in closing:
            assert stack and stack.pop() == closing[token]
    assert stack == []
    assert "Not compiled/native-verified until gated B/C." in TEXT


def test_protocol_sizes_enums_uuid_and_loss_are_frozen():
    for required in [
        "MaxFrameBytes = 65536", "MaxProofBytes = 49152", "MaxInteger = 9007199254740991UL",
        "b.Length == 145", "b.Length == 156", "b.Length == 60", "b.Length == 68", "b.Length == 20",
        "b[268] <= 5", "b[269] >= 1 && b[269] <= 17",
        'value.ToString("N")', "LegacyLossUnknown = 2",
        "body[72] = 1; body[74] = LegacyLossUnknown",
    ]:
        assert required in TEXT
    assert "Math.Log10(" not in TEXT
    assert "Guid.ToByteArray()" not in code_tokens(TEXT)


def test_suspended_launcher_order_precedes_private_bootstrap():
    launch = TEXT[TEXT.index("internal static IBaiMeterOwnedWorker Launch("):]
    operations = [
        "ops.PinExactBundle()", "ops.CreatePrivatePipes()", "ops.PrepareHandleList(",
        "ops.CreateProcessW(", "ops.ObserveProcess(child)", "ops.CheckCurrentUserSidSession(",
        "ops.RevalidatePins(", "ops.AssignOwnedWorkerJob(", "ops.ResumeThread(",
        "ops.WritePrivateBootstrap(",
    ]
    offsets = [launch.index(operation) for operation in operations]
    assert offsets == sorted(offsets)
    for required in [
        "CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW",
        "final.CreationTime == observed.CreationTime", "final.Sid == observed.Sid",
        "final.Session == observed.Session", "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_ACTIVE_PROCESS, 1",
        "ops.ResumeThread(child.Thread) == 1",
    ]:
        assert required in launch
    assert "Process.Start(" not in TEXT
    assert "ProcessStartInfo" not in TEXT


def test_capture_ui_never_waits_for_pipe_or_worker_shutdown():
    offer = TEXT[TEXT.index("internal void OfferNativeV1("):TEXT.index("internal void Invalidate(")]
    for forbidden in [".Read(", ".Write(", "WaitOne(", ".Join(", "ClosePureWorker("]:
        assert forbidden not in offer
    fail = TEXT[TEXT.index("private void FailClosed("):TEXT.index("// Injected Windows operations")]
    assert "ThreadPool.QueueUserWorkItem" in fail
    assert "worker.ClosePureWorker()" in fail
    assert "Thread.Abort(" not in TEXT
    assert "TerminateProcess(" not in TEXT  # Only gated owned-backend cleanup is delegated.
    assert "PCM" not in code_tokens(TEXT)
    assert "quality_pass_issued" not in code_tokens(TEXT)


def test_latest_one_deadline_and_transport_ack_do_not_claim_p2_drain():
    assert "current = pending = new BaiMeterPending(body, now)" in TEXT
    assert "requests.Count <= 2" in TEXT
    assert "requestIds.Count < 65536" in TEXT
    assert "NOT the P2" in TEXT
    assert "evaluation/lease" in TEXT
    assert "(ulong)(now - observed) < (ulong)frequency / 4" in TEXT
    for literal in ["249000000", "250000000", "251000000"]:
        assert literal in TEXT
    assert "new BaiMeterDisplay(ready && !closed, band, reason)" in TEXT


def test_no_console_exception_or_private_bootstrap_dump():
    assert "Console." not in TEXT
    assert "error.Message" not in TEXT and "exception.Message" not in TEXT
    assert "ERR_TASK048_C1_PROTOCOL_FAILURE" in TEXT


def test_unknown_or_pseudo_process_handle_is_not_a_cleanup_target():
    assert "childHandleOwned = child != null && child.Process.ToInt64() > 0" in TEXT
    assert "ops.CleanupOwnedFailure(childHandleOwned ? child : null, attemptedResume)" in TEXT


def test_legitimate_bootstrap_status_one_is_not_protocol_failure():
    branch = TEXT[TEXT.index("if (source.Type == 1)"):TEXT.index("else if (source.Type == 4)")]
    expected_order = ["if (b[0] == 2)", "BaiMeterProtocol.Require(b[1] == 1)",
                      "requests.Remove(sourceTx)", 'FailClosed("BOOTSTRAP_REJECTED")',
                      "return;", "BaiMeterProtocol.Require(b[0] == 0"]
    assert [branch.index(item) for item in expected_order] == sorted(branch.index(item) for item in expected_order)
    fail = TEXT[TEXT.index("private void FailClosed("):TEXT.index("public void Dispose()")]
    assert "if (closed) return; closed = true; ready = false; band = 0; reason = code" in fail
    assert "requests.Clear()" in fail
    assert "ThreadPool.QueueUserWorkItem" in fail


def test_snapshot_and_watchdog_atomically_expire_band_and_reason():
    helper = TEXT[TEXT.index("internal static BaiMeterDisplay ExpireWindow("):TEXT.index("internal void OfferNativeV1(")]
    assert "if (hasCurrent && !Within(observed, now, frequency))" in helper
    assert 'new BaiMeterDisplay(display.Connected, 0, "WINDOW_EXPIRED")' in helper
    assert "return display;" in helper  # Null-current initial/refusal reason is unchanged.
    assert "band = value.Band; reason = value.Reason" in helper
    for start, end, call in [
        ("internal BaiMeterDisplay Snapshot()", "private void Partial(", "RefreshDisplayExpiry(clock.Now)"),
        ("private void Watchdog(", "private void WriteLoop()", "RefreshDisplayExpiry(now)"),
    ]:
        body = TEXT[TEXT.index(start):TEXT.index(end)]
        assert body.index("lock (gate)") < body.index(call)
    assert "ClosePureWorker(" not in helper and "FailClosed(" not in helper


@pytest.mark.parametrize("boundary", [249000000, 250000000, 251000000])
def test_embedded_csharp_selftest_covers_display_reason_expiry_boundary(boundary):
    # Static source verification only; these C# assertions execute at gated C.
    selftest = TEXT[TEXT.index("internal static int Run()") :]
    assert str(boundary) in selftest
    assert "BaiMeterRuntimeBridge.ExpireWindow(classified," in selftest
    assert "true, 0, expiryBoundaries[i], 1000000000)" in selftest
    assert "display.Connected" in selftest
    assert "display.Band == (i == 0 ? 2 : 0)" in selftest
    assert 'display.Reason == (i == 0 ? "P2_REASON_17" : "WINDOW_EXPIRED")' in selftest


def test_embedded_csharp_selftest_preserves_no_current_window_reasons():
    selftest = TEXT[TEXT.index("internal static int Run()") :]
    assert 'new string[] { "CONNECTED_NOT_CLASSIFIED", "BOOTSTRAP_REJECTED" }' in selftest
    assert "Object.ReferenceEquals(initial," in selftest
    assert "ExpireWindow(initial, false, 0, 251000000, 1000000000)" in selftest
