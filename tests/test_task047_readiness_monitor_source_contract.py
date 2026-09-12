from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTROLLER_ROOT = ROOT / "native" / "task047_obs_voice_capture" / "controller"
BUILD = ROOT / "native" / "task047_obs_voice_capture" / "scripts" / "build-controller.ps1"


def _text(name: str) -> str:
    return (CONTROLLER_ROOT / name).read_text(encoding="utf-8")


def test_exact_readiness_source_family_is_present() -> None:
    expected = {
        "BaiVoiceCaptureController.cs",
        "BaiCaptureOperation.cs",
        "BaiReadinessMonitor.cs",
        "BaiReadinessReceipt.cs",
        "BaiReadinessMonitorSelfTest.cs",
    }
    assert expected <= {path.name for path in CONTROLLER_ROOT.iterdir() if path.is_file()}


def test_controller_uses_immutable_operation_instead_of_inverse_gain_boolean() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    assert "private BaiCaptureOperation currentOperation;" in controller
    assert "private volatile bool gainMeasurement;" not in controller
    assert "if (!gainMeasurement)" not in controller
    receive = controller.split("private void ReceiveLoop(", 1)[1].split(
        "private void UpdateMetrics", 1
    )[0]
    assert "BaiCaptureOperation operation" in receive
    assert "operation.IsRecording" in receive
    assert "operation.IsLegacyGain" in receive
    assert "operation.TryAcquirePacketLease" in receive


def test_only_wav_operation_can_own_recording_sink() -> None:
    operation = _text("BaiCaptureOperation.cs")
    assert "internal sealed class BaiRecordingSinkCapability" in operation
    assert "internal sealed class BaiWavCaptureOperation" in operation
    assert "internal sealed class BaiMetadataOnlyCaptureOperation" in operation
    metadata = operation.split("internal sealed class BaiMetadataOnlyCaptureOperation", 1)[1].split(
        "internal sealed class BaiRecordingSinkCapability", 1
    )[0]
    assert "WaveFloatWriter" not in metadata
    assert "BaiRecordingSinkCapability" not in metadata
    wav = operation.split("internal sealed class BaiWavCaptureOperation", 1)[1]
    assert "BaiRecordingSinkCapability" in wav
    assert "HasRecordingSink" in wav


def test_receiver_is_attached_before_it_can_start() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    start = controller.split("var receiveTask = new Task(", 1)[1].split(
        "await Task.Delay(300)", 1
    )[0]
    assert start.index("operation.AttachReceiver(receiveTask)") < start.index(
        "receiveTask.Start(TaskScheduler.Default)"
    )
    operation = _text("BaiCaptureOperation.cs")
    assert "private Task receiverTask;" in operation
    assert "BeginSettlementAsync" in operation
    assert "AwaitSettlementWithoutDeadlineAsync" in operation


def test_delayed_start_continuation_cannot_launch_obs_after_stop() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    after_delay = controller.split("await Task.Delay(300);", 1)[1].split(
        "if (existingObs != null)", 1
    )[0]
    assert "operation.StopRequested" in after_delay
    assert "stopping" in after_delay
    assert "Object.ReferenceEquals(currentOperation, operation)" in after_delay


def test_stop_fences_then_settles_before_finalize() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    stop = controller.split("private void BeginStop(string reason)", 1)[1].split(
        "private void WriteGainReceipt", 1
    )[0]
    assert stop.index("operation.RequestStop();") < stop.index(
        "operation.BeginSettlementAsync"
    )
    assert "operation.BeginSettlementAsync(TimeSpan.FromMilliseconds(2000))" in stop
    assert stop.index("BeginSettlementAsync") < stop.index("FinalizeSettledOperation")
    operation = _text("BaiCaptureOperation.cs")
    begin = operation.split("internal Task<bool> BeginSettlementAsync", 1)[1].split(
        "private void SignalCancellationAndClosePipeCore", 1
    )[0]
    assert begin.index("Task.Delay(sharedBudget)") < begin.index(
        "Task.Run((Action)SignalCancellationAndClosePipeCore)"
    )
    assert "Task.WhenAll(ObserveLeafAsync(receiver), ObserveLeafAsync(teardown))" in operation
    finalize = stop.split("private void FinalizeSettledOperation", 1)[1]
    assert finalize.index("operation.FinalizeAudioPrefix();") < finalize.index(
        "File.Move(operation.PartialAudioPath, operation.FinalAudioPath)"
    )


def test_stop_timeout_keeps_restart_blocked_until_same_operation_settles() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    assert '"STOP_PENDING: " + reason' in controller
    assert '"停止処理未完了・再開始禁止"' in controller
    pending = controller.split("if (!settled)", 1)[1].split(
        "private void FinalizeSettledOperation", 1
    )[0]
    assert "AwaitSettlementWithoutDeadlineAsync" in pending
    assert "currentOperation = null" not in pending


def test_owner_stop_does_not_depend_on_obs_identity_read() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    stop = controller.split("private void StopCapture()", 1)[1].split(
        "private TimeSpan GetActiveElapsed", 1
    )[0]
    assert 'BeginStop("USER_STOP")' in stop
    assert "ValidateSameObsProcess" not in stop


def test_readiness_live_action_fails_closed_before_ipc_or_mic_effect() -> None:
    controller = _text("BaiVoiceCaptureController.cs")
    action = controller.split("private void ReadinessCheckClicked", 1)[1].split(
        "private async void StartOperation", 1
    )[0]
    assert "READINESS_DURABLE_EXCLUSION_NOT_BOUND" in action
    for forbidden in ("StartOperation(", "ReceiveLoop(", "CreateSameUserPipe", "Process.Start"):
        assert forbidden not in action
    assert "最大3分" in controller


def test_readiness_monitor_is_pure_and_does_not_import_effect_capabilities() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    for forbidden in (
        "System.IO",
        "NamedPipe",
        "WaveFloatWriter",
        "BaiRecordingSinkCapability",
        "File.",
        "Directory.",
        "Process.",
        "MessageBox",
    ):
        assert forbidden not in monitor


def test_live_gate_cannot_be_manufactured_from_boolean_claims() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    assert 'LiveUnavailableReason = "READINESS_DURABLE_EXCLUSION_NOT_BOUND"' in monitor
    live = monitor.split("internal static bool TryCreateLive", 1)[1].split(
        "internal static BaiReadinessMonitor CreatePureTest", 1
    )[0]
    assert "monitor = null;" in live
    assert "return false;" in live
    assert "bool currentTask046" not in monitor
    assert "bool currentH1" not in monitor
    assert "bool durableExclusionBound" not in monitor
    for forbidden in ("lock file", "Process.GetProcesses", "Directory.GetFiles", "lease expires"):
        assert forbidden not in monitor


def test_three_minute_cap_is_exact_and_monotonic_input_driven() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    assert "HardCapMinutes = 3;" in monitor
    assert "HardCapMilliseconds = 180000;" in monitor
    hard_cap = monitor.split("internal void ObserveWatchdog", 1)[1].split(
        "internal void RequestStop", 1
    )[0]
    assert "tick - startTick >= MillisecondsToTicks(BaiReadinessLimits.HardCapMilliseconds)" in hard_cap
    assert 'RequestStopUnderGate("HARD_CAP_REACHED", null, tick, true)' in hard_cap
    assert 'RequestStopUnderGate("ARM_TIMEOUT", null, tick, true)' in hard_cap
    assert 'RequestStopUnderGate("NO_INPUT_TIMEOUT", null, tick, true)' in hard_cap


def test_sequence_and_timestamp_failures_have_separate_counters_and_precedence() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    commit = monitor.split("internal bool CommitPacket", 1)[1].split(
        "internal void ObserveSettingsChanged", 1
    )[0]
    assert commit.index("sequence < expectedSequence") < commit.index(
        "timestamp < previousTimestamp"
    )
    assert 'RequestStopUnderGate("SEQUENCE_ORDER_ERROR", null, commitTick, true)' in commit
    assert 'RequestStopUnderGate("SOURCE_TIMESTAMP_REGRESSION", null, commitTick, true)' in commit
    assert "SequenceOrderErrors++" in commit
    assert "SourceTimestampRegressions++" in commit
    assert "sequenceExhausted || sequence < expectedSequence" in commit
    assert commit.index("sequenceExhausted || sequence < expectedSequence") < commit.index(
        "timestamp < previousTimestamp"
    )


def test_packet_scan_is_outside_gate_and_marker_token_is_rechecked() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    scan = monitor.split("internal BaiReadinessPacketScan ScanPacket", 1)[1].split(
        "internal bool CommitPacket", 1
    )[0]
    commit = monitor.split("internal bool CommitScannedPacket", 1)[1].split(
        "internal void ObserveSettingsChanged", 1
    )[0]
    assert "BaiReadinessPacketScan.Create" in scan
    assert "BitConverter.ToSingle" not in commit
    assert "scan.MeasurementToken != measurementToken" in commit
    assert "DiscardedOnTokenChange++" in commit
    assert "openWindow.AddPacket(scan, sequence)" in commit


def test_pure_self_test_declares_all_106_cases() -> None:
    self_test = _text("BaiReadinessMonitorSelfTest.cs")
    names = re.findall(r'Case\("(T\d{2,3}_[^"]+)"', self_test)
    assert len(names) == 106
    assert [name.split("_", 1)[0] for name in names] == [f"T{number:02d}" for number in range(1, 107)]
    assert "Require(executed == 106);" in self_test


def test_secondary_currentness_reuses_single_revocation_before_freeze() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    receipt = _text("BaiReadinessReceipt.cs")
    secondary = monitor.split("private void ObserveSecondaryStop", 1)[1].split(
        "private void ApplyGlobalRevocationIfRequired", 1
    )[0]
    assert secondary.index('"TERMINAL_ALREADY_FROZEN"') < secondary.index("secondaryStopReasons.Add")
    assert "ApplyGlobalRevocationIfRequired();" in secondary
    assert "AppendEvent" not in secondary
    apply = monitor.split("private void ApplyGlobalRevocationIfRequired", 1)[1].split(
        "internal BaiReadinessTerminalProjection FreezeTerminalProjection", 1
    )[0]
    assert "globalRevocationApplied || revocationEventId == null" in apply
    assert "foreach (var reason in secondaryStopReasons)" in apply
    assert "ApplyAllEpochInvalidation(revocationEventId)" in apply
    assert "globalRevocationApplied = true" in apply
    assert 'foreach (string reason in (IList)terminal["secondary_reasons"])' in receipt
    assert receipt.count("bool globalRevocation = HasCurrentnessStopReason(terminal)") == 2


def test_freeze_evidence_is_validated_before_every_admission_mutation() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    freeze = monitor.split("internal void FreezeSettings", 1)[1].split("internal void StartWindow", 1)[0]
    validation = freeze.index("preparedEpoch.Evidence.ValidateForFreeze")
    for mutation in ("RequireOptionalSlot", "epochIds.Add", "commandIds.Add", "AppendEvent",
                     "settingsEpochs.Add", "measurementToken++", "Phase = BaiReadinessPhase.Frozen"):
        assert validation < freeze.index(mutation)
    for invariant in ("value.OwnerSubjectBindingSha256 != subjectBindingSha256",
                      "value.CommandId != commandId", "value.ObservedTick != tick",
                      'value.State == "ATTESTED_OFF" || value.State == "ATTESTED_NOT_OFF"',
                      "RequireDigest(SettingsSha256, false)", "RequireDigest(value.OwnerSubjectBindingSha256, true)"):
        assert invariant in monitor


def test_no_artifact_proof_precedes_sink_task_and_cannot_reuse_ownership() -> None:
    receipt = _text("BaiReadinessReceipt.cs")
    prepared = receipt.split("internal static Task<PublicationResult> StartPrepared", 1)[1].split(
        "private static Task<PublicationResult> InvalidDto", 1
    )[0]
    assert prepared.index("ref sink.publicationClaimed") < prepared.index("projection.Consume()")
    assert prepared.index("projection.Consume()") < prepared.index("try {")
    assert prepared.index("CreateFromConsumption") < prepared.index("Task.Run")
    assert "CREATE_FAILED_NO_ARTIFACT" in prepared
    assert "INVALID_DTO_NO_ARTIFACT" in receipt
    assert "NO_ARTIFACT_PROOF_INCOMPLETE" in receipt
    assert "ownedSink.EffectStarted" in receipt
    execution = receipt.split("private static PublicationResult ExecuteOwned", 1)[1].split(
        "internal BaiReadinessMetadataSinkCapability(string exactParent)", 1
    )[0]
    assert "NotPublishedConfirmed" not in execution
    assert execution.index("ref sink.effectStarted") < execution.index("sink.PublishOwned")
    assert "BaiReadinessPublicationOutcome.Unknown" in execution


def test_monitor_owns_event_epoch_watchdog_and_terminal_projection() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    receipt = _text("BaiReadinessReceipt.cs")
    for required in (
        "BaiReadinessEventRecord",
        "BaiReadinessSettingsEpoch",
        "BaiReadinessFreezeEvidence",
        "BaiReadinessCommand",
        "TryEnqueueCommand",
        "MaxPendingCommands",
        "ObserveWatchdog",
        "FreezeTerminalProjection",
        "BaiReadinessTerminalProjection",
        "CURRENTNESS_INVALIDATED",
        "INVALIDATED_AFTER_CLOSE",
    ):
        assert required in monitor
    assert "CreateFromTerminalProjection" in receipt
    assert "ExpectedInvalidations" in receipt
    assert "ValidateExactEventReferences" in receipt


def test_build_script_compiles_and_embeds_exact_readiness_sources() -> None:
    build = BUILD.read_text(encoding="utf-8")
    for name in (
        "BaiCaptureOperation.cs",
        "BaiReadinessMonitor.cs",
        "BaiReadinessReceipt.cs",
        "BaiReadinessMonitorSelfTest.cs",
        "task047-readiness-monitor-receipt-v1.schema.json",
    ):
        assert name in build
    assert "BVP.Task047.ReadinessMonitorReceiptV1.Schema" in build
    assert "--readiness-self-test" in build
    assert "task047-readiness-build-" in build
    assert "TASK047_READINESS_OUTPUT_ROOT" in build


def test_receipt_semantics_and_windows_identity_are_fail_closed() -> None:
    receipt = _text("BaiReadinessReceipt.cs")
    assert "BaiReadinessReceiptSemanticValidator.Validate(root);" in receipt
    for oracle in (
        "ADMISSION_EXPIRED_AT_EFFECT",
        "READBACK_CURRENTNESS_TIME",
        "SUBJECT_REVISION_DIGEST_MISMATCH",
        "SUBJECT_BINDING_DIGEST_MISMATCH",
        "CONSENT_EVALUATION_DIGEST_MISMATCH",
        "CURRENTNESS_READBACK_DIGEST_MISMATCH",
        "STOP_TRACE_POSITION",
        "CAPTURE_BINDING_HASH_MISMATCH",
        "WINDOW_FRAME_COUNT",
        "CHANNEL_COUNT_PARTITION",
        "COMPUTED_FINITE_MATRIX",
        "SECONDARY_NOT_SORTED_UNIQUE",
        "INVALIDATION_SET_INCOMPLETE",
        "WINDOW_CURRENTNESS_DERIVATION",
    ):
        assert oracle in receipt
    assert "BaiReadinessPhysicalIdentity.ForDirectory(parent)" in receipt
    assert "READINESS_METADATA_PARENT_IDENTITY_CHANGED" in receipt
    assert "FileFlagOpenReparsePoint" in receipt
    assert "actual.LinkCount != 1" in receipt
    publish = receipt.split("private string PublishOwned", 1)[1].split(
        "internal static string Hex", 1
    )[0]
    assert publish.index("AssertStableParent();") < publish.index("FileMode.CreateNew")
    assert publish.count("AssertStableParent();") >= 4
    assert "File.Move(pending, final)" in publish


def test_existing_task048_build_defaults_remain_present() -> None:
    build = BUILD.read_text(encoding="utf-8")
    assert "$taskIdentity = 'TASK-048'" in build
    assert "$operationPrefix = 'task048-build-'" in build
    assert "$family = 'task048-controller'" in build
    assert "TASK048_OUTPUT_ROOT=" in build
    assert "TASK048_RUNTIME_ROOT=" in build
    readiness_compile = build.split("$arguments = @", 1)[1].split(
        "if ($MeterWorkerBundle)", 1
    )[0]
    assert "$arguments += $readinessSources" in readiness_compile
    assert "/define:BVP_TASK047_READINESS" in readiness_compile
    assert "/resource:" in readiness_compile
    assert "if ($ReadinessBuild) { $selfTestModes += '--readiness-self-test' }" in build
    assert "if ($ReadinessBuild) { $closureFields.readiness_schema_sha256 = $schemaSha }" in build
    controller = _text("BaiVoiceCaptureController.cs")
    dispatch = controller.split('args.Any(x => x == "--meter-self-test")', 1)[1].split(
        'args.Any(x => x == "--self-test")', 1
    )[0]
    assert "#if BVP_TASK047_READINESS" in dispatch
    readiness_ui = controller.split("private readonly Button readinessCheck", 1)[0]
    assert readiness_ui.rstrip().endswith("#if BVP_TASK047_READINESS")


def test_optional_saturation_cannot_precede_stop_fence() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    invalidate = monitor.split("internal void InvalidateCurrentness", 1)[1].split(
        "internal void MarkSettling", 1
    )[0]
    assert invalidate.index("FenceAdmission();") < invalidate.index("AppendEvent(")
    assert "events.Count >= BaiReadinessLimits.MaxEvents - 3" in invalidate
    stop = monitor.split("private void RequestStopUnderGate", 1)[1].split(
        "internal BaiReadinessTerminalProjection FreezeTerminalProjection", 1
    )[0]
    assert stop.index("FenceAdmission();") < stop.index("RejectPendingCommandsBeforeStop")
    reserve = monitor.split("private void RequireOptionalSlot", 1)[1].split(
        "private BaiReadinessEventRecord AppendEvent", 1
    )[0]
    assert reserve.index('RequestStopUnderGate("RESOURCE_LIMIT"') < reserve.index("throw new")
    for start, end, mutation in (
        ("internal void FreezeSettings", "internal void StartWindow", "epochIds.Add"),
        ("internal void StartWindow", "internal void EndWindow", "windowIds.Add"),
        ("internal void EndWindow", "internal BaiReadinessPacketScan ScanPacket", "commandIds.Add"),
        ("internal void ObserveSettingsChanged", "internal void ReportObservation", "commandIds.Add"),
    ):
        body = monitor.split(start, 1)[1].split(end, 1)[0]
        assert body.index("RequireOptionalSlot(tick)") < body.index(mutation)


def test_publication_uses_owned_task_and_sink_proof_only() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    receipt = _text("BaiReadinessReceipt.cs")
    assert "CompletePublication(" not in monitor
    assert "private PublicationResult(" in receipt
    assert "proof.BelongsTo(receipt, sink)" in monitor
    assert "receipt.IsFrom(terminalProjection)" in monitor
    assert "publicationTask = Task.Run(() => sink.Publish(receipt));" in monitor
    assert "METADATA_UNCONFIRMED" not in monitor or "MetadataUnconfirmed" in monitor
    assert "publicationTask == null" in monitor
    assert "SINK_PUBLICATION_ALREADY_CLAIMED" in receipt
    assert "PUBLICATION_ALREADY_CLAIMED" in receipt
    assert "PUBLICATION_PROOF_INCOMPLETE" in receipt


def test_terminal_graph_and_receipt_bytes_sever_mutable_aliases() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    receipt = _text("BaiReadinessReceipt.cs")
    projection = monitor.split("internal sealed class BaiReadinessTerminalProjection", 1)[1].split(
        "internal sealed class BaiReadinessMonitor", 1
    )[0]
    assert "events = (object[])BaiReadinessReceipt.CopyJson(eventObjects)" in projection
    assert "epochs = (object[])BaiReadinessReceipt.CopyJson(epochObjects)" in projection
    assert "windows = (object[])BaiReadinessReceipt.CopyJson(windowObjects)" in projection
    assert "TERMINAL_PROJECTION_ALREADY_CONSUMED" in projection
    assert "root = CopyRoot(value);" in receipt
    assert "private readonly byte[] canonicalBytes;" in receipt
    assert "SERIALIZATION_ALREADY_CLAIMED" in receipt


def test_epoch_terminal_parameter_and_projection_invariants_are_present() -> None:
    receipt = _text("BaiReadinessReceipt.cs")
    assert "committedFrames, terminal);" in receipt
    assert "long committedFrames, IDictionary terminal)" in receipt
    for invariant in (
        "stop.Frame == committedFrames", "WINDOW_DISJOINT_CREATION_ORDER",
        "NORMAL_SPEECH_REQUIRES_CLOSED_ROOM_TONE", "OWNER_REPORT_FLAG_EQUIVALENCE",
        "TRANSPORT_FAULT_REASON_PROVENANCE", "EVENT_WINDOW_PROVENANCE",
        "EPOCH_OVERLAP_WITHOUT_INVALIDATION",
    ):
        assert invariant in receipt


def test_transport_projection_uses_observed_counters_and_owner_command_routes() -> None:
    monitor = _text("BaiReadinessMonitor.cs")
    for field, member in (
        ("connection_attempts", "ConnectionAttempts"), ("incomplete_packets", "IncompletePackets"),
        ("hmac_failures", "HmacFailures"), ("nonce_mismatches", "NonceMismatches"),
    ):
        assert f'{{ "{field}", {member} }}' in monitor
        assert f"{member}++" in monitor
    assert "internal void WithdrawWindow(" in monitor
    assert "internal void ReportObservation(" in monitor
