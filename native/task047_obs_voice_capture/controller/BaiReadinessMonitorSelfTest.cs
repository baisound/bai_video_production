using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;

internal static class BaiReadinessMonitorSelfTest
{
    private static int executed;

    internal static int Run()
    {
        try {
            Case("T01_mode_immutable", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-1", "session-1", "metadata")) {
                    Require(op.Mode == BaiCaptureMode.LegacyGainCheck);
                }
            });
            Case("T02_gain_has_no_recording_sink", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-2", "session-2", "metadata"))
                    Require(!op.HasRecordingSink && !op.IsRecording);
            });
            Case("T03_readiness_has_no_recording_sink", delegate {
                using (var op = BaiCaptureOperation.CreateReadinessUnavailable("op-3", "session-3", "metadata"))
                    Require(!op.HasRecordingSink && op.IsReadiness);
            });
            Case("T04_recording_sink_is_explicit", delegate {
                using (var op = BaiCaptureOperation.CreateRecording("op-4", "session-4", "a.partial", "a.wav"))
                    Require(op.HasRecordingSink && op.IsRecording);
            });
            Case("T05_stop_fences_new_packet_lease", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-5", "session-5", "metadata")) {
                    var generation = op.Generation; op.RequestStop();
                    BaiCapturePacketLease lease;
                    Require(!op.TryAcquirePacketLease(generation, out lease));
                }
            });
            Case("T06_lease_counts_inflight", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-6", "session-6", "metadata")) {
                    BaiCapturePacketLease lease;
                    Require(op.TryAcquirePacketLease(op.Generation, out lease) && op.InFlightCount == 1);
                    lease.Dispose(); Require(op.InFlightCount == 0);
                }
            });
            Case("T07_stale_generation_rejects", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-7", "session-7", "metadata")) {
                    var generation = op.Generation; op.RequestStop();
                    BaiCapturePacketLease lease; Require(!op.TryAcquirePacketLease(generation, out lease));
                }
            });
            Case("T08_receiver_is_retained", delegate {
                using (var op = BaiCaptureOperation.CreateLegacyGain("op-8", "session-8", "metadata")) {
                    op.AttachReceiver(Task.FromResult(0)); op.RequestStop();
                    Require(op.BeginSettlementAsync(TimeSpan.FromSeconds(1)).GetAwaiter().GetResult());
                }
            });
            Case("T09_session_key_is_operation_owned", delegate {
                using (var left = BaiCaptureOperation.CreateLegacyGain("op-9a", "session-9a", "metadata"))
                using (var right = BaiCaptureOperation.CreateLegacyGain("op-9b", "session-9b", "metadata"))
                    Require(!Object.ReferenceEquals(left.SessionKey, right.SessionKey) &&
                        left.SessionKey.Any(x => x != 0) && right.SessionKey.Any(x => x != 0));
            });
            Case("T10_live_is_unconditionally_unbound", delegate {
                BaiReadinessMonitor monitor; string reason;
                Require(!BaiReadinessMonitor.TryCreateLive(2,
                    out monitor, out reason) && reason == BaiReadinessMonitor.LiveUnavailableReason);
            });
            Case("T11_boolean_authority_constructor_absent", delegate {
                var constructors = typeof(BaiReadinessAdmission).GetConstructors(
                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                Require(constructors.All(x => x.GetParameters().All(p => p.ParameterType != typeof(bool))));
            });
            Case("T12_pure_fixture_cannot_enable_live", delegate {
                var fixture = NewMonitor("12"); fixture.Activate();
                BaiReadinessMonitor monitor; string reason;
                Require(!BaiReadinessMonitor.TryCreateLive(2, out monitor, out reason));
            });
            Case("T13_pure_active_starts_adjustment", delegate {
                var monitor = NewMonitor("13"); monitor.Activate();
                Require(monitor.Lifecycle == BaiReadinessLifecycle.Active &&
                    monitor.Phase == BaiReadinessPhase.AdjustmentOnly);
            });
            Case("T14_freeze_requires_attestation", delegate {
                var monitor = NewMonitor("14"); monitor.Activate();
                RequireThrows(delegate { monitor.FreezeSettings(
                    "epoch-14", "command-14", 0, null); });
            });
            Case("T15_freeze_enters_frozen", delegate {
                var monitor = Frozen("15"); Require(monitor.Phase == BaiReadinessPhase.Frozen);
            });
            Case("T16_room_window_only_from_frozen", delegate {
                var monitor = Frozen("16");
                monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone, "window-16", "command-room-16", 1);
                Require(monitor.Phase == BaiReadinessPhase.RoomToneOpen);
            });
            Case("T17_speech_before_room_close_rejects", delegate {
                var monitor = Frozen("17");
                RequireThrows(delegate { monitor.StartWindow(BaiReadinessWindowPurpose.NormalSpeech,
                    "window-17", "command-speech-17", 1); });
            });
            Case("T18_room_close_enables_speech", delegate {
                var monitor = Frozen("18");
                monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone, "room-18", "start-18", 1);
                monitor.EndWindow("end-18", 2);
                monitor.StartWindow(BaiReadinessWindowPurpose.NormalSpeech, "speech-18", "speech-start-18", 3);
                Require(monitor.Phase == BaiReadinessPhase.NormalSpeechOpen);
            });
            Case("T19_empty_window_is_no_input", delegate {
                var monitor = Frozen("19");
                monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone, "room-19", "start-19", 1);
                monitor.EndWindow("end-19", 2);
                var stats = monitor.Windows[0].FreezeStatistics()[0];
                Require(stats.DerivedState == BaiReadinessDerivedState.NoInput && stats.FrameCount == 0);
            });
            Case("T20_zero_is_measured_zero", delegate {
                var monitor = Room("20"); Require(monitor.CommitPacket(0, 100, 2, 2, Planar(2, 0F, 0F), 2));
                var stats = monitor.Windows[0].FreezeStatistics();
                Require(stats.All(x => x.DerivedState == BaiReadinessDerivedState.MeasuredZero));
            });
            Case("T21_finite_statistics", delegate {
                var monitor = Room("21"); Require(monitor.CommitPacket(0, 100, 2, 2, Planar(2, .5F, -.5F), 2));
                var stats = monitor.Windows[0].FreezeStatistics();
                Require(stats.All(x => x.DerivedState == BaiReadinessDerivedState.ComputedFinite &&
                    Math.Abs(x.RmsLinear.Value - .5) < 1e-12));
            });
            Case("T22_nonfinite_commits_then_stops", delegate {
                var monitor = Room("22"); Require(monitor.CommitPacket(0, 100, 1, 2, Planar(1, Single.NaN, 0F), 2));
                Require(monitor.StopReason == "NONFINITE_INPUT" &&
                    monitor.Windows[0].FreezeStatistics()[0].DerivedState ==
                    BaiReadinessDerivedState.NotComputableNonfinite);
            });
            Case("T23_excursion_inclusive", delegate {
                var monitor = Room("23"); Require(monitor.CommitPacket(0, 100, 1, 2, Planar(1, .9999F, -.9999F), 2));
                Require(monitor.Windows[0].FreezeStatistics().All(x => x.ExcursionCount == 1));
            });
            Case("T24_channels_remain_separate", delegate {
                var monitor = Room("24"); Require(monitor.CommitPacket(0, 100, 1, 2, Planar(1, .25F, .75F), 2));
                var stats = monitor.Windows[0].FreezeStatistics();
                Require(stats[0].PeakLinear == .25 && stats[1].PeakLinear == .75);
            });
            Case("T25_contiguous_sequence_commits", delegate {
                var monitor = Room("25");
                Require(monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2));
                Require(monitor.CommitPacket(8, 101, 1, 2, Planar(1, 0F, 0F), 3));
                Require(monitor.CommittedPackets == 2);
            });
            Case("T26_sequence_gap_is_distinct", delegate {
                var monitor = Room("26"); monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2);
                Require(!monitor.CommitPacket(9, 101, 1, 2, Planar(1, 0F, 0F), 3) &&
                    monitor.StopReason == "SEQUENCE_GAP" && monitor.SequenceGapEvents == 1);
            });
            Case("T27_sequence_order_error_is_distinct", delegate {
                var monitor = Room("27"); monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2);
                Require(!monitor.CommitPacket(7, 101, 1, 2, Planar(1, 0F, 0F), 3) &&
                    monitor.StopReason == "SEQUENCE_ORDER_ERROR" && monitor.SequenceOrderErrors == 1 &&
                    monitor.SourceTimestampRegressions == 0);
                var wrap = Room("27-wrap");
                Require(wrap.CommitPacket(UInt64.MaxValue, 100, 1, 2, Planar(1, 0F, 0F), 2));
                Require(!wrap.CommitPacket(UInt64.MaxValue, 101, 1, 2, Planar(1, 0F, 0F), 3) &&
                    wrap.StopReason == "SEQUENCE_ORDER_ERROR");
            });
            Case("T28_timestamp_regression_is_distinct", delegate {
                var monitor = Room("28"); monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2);
                Require(!monitor.CommitPacket(8, 99, 1, 2, Planar(1, 0F, 0F), 3) &&
                    monitor.StopReason == "SOURCE_TIMESTAMP_REGRESSION" &&
                    monitor.SourceTimestampRegressions == 1 && monitor.SequenceOrderErrors == 0);
            });
            Case("T29_equal_timestamp_allowed", delegate {
                var monitor = Room("29"); monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2);
                Require(monitor.CommitPacket(8, 100, 1, 2, Planar(1, 0F, 0F), 3));
            });
            Case("T30_first_timestamp_is_anchor", delegate {
                var monitor = Room("30"); Require(monitor.CommitPacket(77, 0, 1, 2, Planar(1, 0F, 0F), 2));
                Require(monitor.SourceTimestampRegressions == 0);
            });
            Case("T31_rejected_timestamp_adds_no_frames", delegate {
                var monitor = Room("31"); monitor.CommitPacket(0, 10, 2, 2, Planar(2, 0F, 0F), 2);
                Require(!monitor.CommitPacket(1, 9, 2, 2, Planar(2, 0F, 0F), 3) &&
                    monitor.CommittedFrames == 2);
            });
            Case("T32_stop_rejects_late_packet", delegate {
                var monitor = Room("32"); monitor.RequestStop("OWNER_STOP", 4);
                Require(!monitor.CommitPacket(0, 10, 1, 2, Planar(1, 0F, 0F), 5) &&
                    monitor.DiscardedAfterRevocation == 1);
            });
            Case("T33_first_stop_reason_wins", delegate {
                var monitor = Room("33"); monitor.RequestStop("OWNER_STOP", 4);
                monitor.RequestStop("PIPE_FAILURE", 5); Require(monitor.StopReason == "OWNER_STOP");
            });
            Case("T34_hard_cap_exact_boundary", delegate {
                var monitor = NewMonitor("34"); monitor.Activate();
                Require(monitor.CommitPacket(0, 1, 1, 2, Planar(1, 0F, 0F), 1));
                for (long tick = 100; tick < 180000; tick += 100)
                    monitor.ObserveWatchdog(tick);
                Require(monitor.StopReason == null);
                monitor.ObserveWatchdog(180000);
                Require(monitor.StopReason == "HARD_CAP_REACHED");
            });
            Case("T35_hard_cap_constant_is_three_minutes", delegate {
                Require(BaiReadinessLimits.HardCapMinutes == 3 &&
                    BaiReadinessLimits.HardCapMilliseconds == 180000);
            });
            Case("T36_settings_change_interrupts_open_window", delegate {
                var monitor = Room("36");
                var stale = monitor.ScanPacket(Planar(1, .1F, .2F), 1, 2);
                monitor.ObserveSettingsChanged("settings-change-36", 8);
                Require(monitor.Windows[0].ClosureState == BaiReadinessClosureState.Interrupted &&
                    monitor.Phase == BaiReadinessPhase.AdjustmentOnly &&
                    !monitor.CommitScannedPacket(0, 10, stale, 9) &&
                    monitor.DiscardedOnTokenChange == 1 && monitor.CommittedFrames == 0);
            });
            Case("T37_closed_window_coordinates", delegate {
                var monitor = Room("37"); monitor.CommitPacket(0, 10, 3, 2, Planar(3, .1F, .2F), 2);
                monitor.EndWindow("end-37", 9);
                Require(monitor.Windows[0].StartFrame == 0 && monitor.Windows[0].EndFrame == 3);
            });
            Case("T38_wrong_channel_count_rejects", delegate {
                var monitor = Room("38");
                Require(!monitor.CommitPacket(0, 1, 1, 1, Planar(1, 0F), 2) &&
                    monitor.StopReason == "FORMAT_DRIFT" && monitor.InvalidHeaders == 1);
            });
            Case("T39_wrong_payload_length_rejects", delegate {
                var monitor = Room("39");
                Require(!monitor.CommitPacket(0, 1, 2, 2, new byte[4], 2) &&
                    monitor.StopReason == "INVALID_HEADER" && monitor.InvalidHeaders == 1);
            });
            Case("T40_id_grammar_accepts_opaque_safe_tokens", delegate {
                Require(BaiReadinessAdmission.RequireId("CON") == "CON" &&
                    BaiReadinessAdmission.RequireId("a:b") == "a:b");
            });
            Case("T41_id_grammar_rejects_path_separator", delegate {
                RequireThrows(delegate { BaiReadinessAdmission.RequireId("a/b"); });
            });
            Case("T42_filename_is_hash_only", delegate {
                var token = BaiReadinessMetadataSinkCapability.TokenForOperation("a:b");
                Require(token.Length == 64 && token.All(IsLowerHex) && !token.Contains(":"));
            });
            Case("T43_filename_case_sensitive_preimage", delegate {
                Require(BaiReadinessMetadataSinkCapability.TokenForOperation("Case") !=
                    BaiReadinessMetadataSinkCapability.TokenForOperation("case"));
            });
            Case("T44_canonical_json_sorted_and_newline", delegate {
                var bytes = Receipt("op-44").SerializeCanonical();
                var text = new UTF8Encoding(false, true).GetString(bytes);
                Require(text.StartsWith("{\"admission\":", StringComparison.Ordinal) && text.EndsWith("\n"));
            });
            Case("T45_canonical_json_has_no_bom", delegate {
                var bytes = Receipt("op-45").SerializeCanonical();
                Require(!(bytes.Length >= 3 && bytes[0] == 0xef && bytes[1] == 0xbb && bytes[2] == 0xbf));
            });
            Case("T46_restart_durable_gate_is_external", delegate {
                BaiReadinessMonitor monitor; string reason;
                Require(!BaiReadinessMonitor.TryCreateLive(2,
                    out monitor, out reason) && reason == "READINESS_DURABLE_EXCLUSION_NOT_BOUND");
            });
            Case("T47_no_process_local_substitute", delegate {
                var first = BaiCaptureOperation.CreateReadinessUnavailable("op-47a", "session-47a", "metadata");
                first.RequestStop(); first.Dispose();
                BaiReadinessMonitor monitor; string reason;
                Require(!BaiReadinessMonitor.TryCreateLive(2, out monitor, out reason));
            });
            Case("T48_sequence_first_timestamp_cross_negative", delegate {
                var monitor = Room("48"); monitor.CommitPacket(7, 100, 1, 2, Planar(1, 0F, 0F), 2);
                Require(!monitor.CommitPacket(7, 99, 1, 2, Planar(1, 0F, 0F), 3) &&
                    monitor.SequenceOrderErrors == 1 && monitor.SourceTimestampRegressions == 0);
            });
            Case("T49_owned_arm_watchdog", delegate {
                var monitor = NewMonitor("49"); monitor.BeginArming(0);
                for (long tick = 100; tick <= 10000; tick += 100) monitor.ObserveWatchdog(tick);
                Require(monitor.StopReason == "ARM_TIMEOUT");
            });
            Case("T50_owned_no_input_watchdog", delegate {
                var monitor = NewMonitor("50"); monitor.Activate();
                for (long tick = 100; tick <= 5000; tick += 100) monitor.ObserveWatchdog(tick);
                Require(monitor.StopReason == "NO_INPUT_TIMEOUT");
            });
            Case("T51_watchdog_gap_fails_closed", delegate {
                var monitor = NewMonitor("51"); monitor.Activate();
                monitor.ObserveWatchdog(101);
                Require(monitor.StopReason == "WATCHDOG_OVERRUN");
            });
            Case("T52_terminal_projection_requires_settlement", delegate {
                var monitor = NewMonitor("52"); monitor.Activate();
                monitor.RequestStop("OWNER_STOP", 1);
                RequireThrows(delegate { monitor.FreezeTerminalProjection(); });
            });
            Case("T53_terminal_projection_derives_invalidation_sets", delegate {
                var receipt = Receipt("op-53", delegate(BaiReadinessMonitor monitor,
                    string subjectBindingHash) {
                    var epoch = "epoch-53"; var freeze = "freeze-53";
                    monitor.FreezeSettings(epoch, freeze, 1,
                        BaiReadinessFreezeEvidence.CreatePureTest(
                            epoch, freeze, 1, subjectBindingHash));
                    monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone,
                        "room-53", "room-start-53", 2);
                    monitor.EndWindow("room-end-53", 3);
                    monitor.InvalidateCurrentness("AUTHORIZATION_EXPIRED", 8);
                    monitor.MarkSettling(); monitor.MarkSettled(9);
                });
                var text = new UTF8Encoding(false, true).GetString(receipt.SerializeCanonical());
                Require(text.Contains("\"INVALIDATED_AFTER_CLOSE\"") &&
                    text.Contains("\"CURRENTNESS_INVALIDATED\""));
            });
            Case("T54_projection_enters_publication_lifecycle", delegate {
                BaiReadinessMonitor monitor = null;
                var receipt = Receipt("op-54", delegate(BaiReadinessMonitor value, string hash) {
                    monitor = value;
                    value.RequestStop("OWNER_STOP", 1); value.MarkSettling(); value.MarkSettled(2);
                });
                Require(monitor.Lifecycle == BaiReadinessLifecycle.Settled &&
                    monitor.PublicationOutcome == BaiReadinessPublicationOutcome.NotAttempted);
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown();
                monitor.BeginPublicationAsync(receipt, sink).GetAwaiter().GetResult();
                Require(monitor.Lifecycle == BaiReadinessLifecycle.MetadataUnconfirmed);
                Require(monitor.RetainedPublicationTask.IsCompleted &&
                    monitor.PublicationReason == "IO_OUTCOME_UNKNOWN");
                RequireThrows(delegate { monitor.BeginPublicationAsync(receipt, sink); });
                Require(monitor.Lifecycle == BaiReadinessLifecycle.MetadataUnconfirmed);
            });
            Case("T55_event_ledger_is_append_only_and_terminal_ordered", delegate {
                var monitor = NewMonitor("55"); monitor.Activate();
                monitor.RequestStop("OWNER_STOP", 1); monitor.MarkSettling(); monitor.MarkSettled(2);
                Require(monitor.Events.Count == 4 && monitor.Events[0].Code == "OWNER_START" &&
                    monitor.Events[1].Code == "STOP_REQUESTED" &&
                    monitor.Events[2].Code == "REVOCATION_LINEARIZED" &&
                    monitor.Events[3].Code == "RECEIVER_SETTLED");
            });
            Case("T56_subject_uuid_rejects", delegate {
                RequireThrows(delegate { Receipt("op-56", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var subject = (IDictionary<string, object>)admission["owner_subject_binding"];
                        subject["subject_ref"] = "owner-primary";
                    }); });
            });
            Case("T57_subject_predecessor_matrix_rejects", delegate {
                RequireThrows(delegate { Receipt("op-57", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var subject = (IDictionary<string, object>)admission["owner_subject_binding"];
                        subject["subject_revision"] = 2;
                    }); });
            });
            Case("T58_current_match_reason_required", delegate {
                RequireThrows(delegate { Receipt("op-58", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var readback = (IDictionary<string, object>)admission["start_currentness_readback"];
                        readback["reason_codes"] = new object[0];
                    }); });
            });
            Case("T59_subject_binding_digest_recomputed", delegate {
                RequireThrows(delegate { Receipt("op-59", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var subject = (IDictionary<string, object>)admission["owner_subject_binding"];
                        subject["binding_sha256"] =
                            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
                    }); });
            });
            Case("T60_consent_digest_recomputed", delegate {
                RequireThrows(delegate { Receipt("op-60", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var consent = (IDictionary<string, object>)admission[
                            "owner_capture_consent_evaluation"];
                        consent["evaluation_sha256"] =
                            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
                    }); });
            });
            Case("T61_readback_digest_recomputed", delegate {
                RequireThrows(delegate { Receipt("op-61", null,
                    delegate(IDictionary<string, object> root) {
                        var admission = (IDictionary<string, object>)root["admission"];
                        var readback = (IDictionary<string, object>)admission["start_currentness_readback"];
                        readback["readback_sha256"] =
                            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
                    }); });
            });
            Case("T62_bounded_command_queue_dispatches_typed_freeze", delegate {
                var monitor = NewMonitor("62"); monitor.Activate();
                const string subjectHash =
                    "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
                var evidence = BaiReadinessFreezeEvidence.CreatePureTest(
                    "epoch-62", "freeze-62", 1, subjectHash);
                string rejection;
                Require(monitor.TryEnqueueCommand(BaiReadinessCommand.Freeze(
                    monitor.OperationId, "epoch-62", "freeze-62", 1, evidence), out rejection));
                Require(monitor.PendingCommandCount == 1 &&
                    monitor.ProcessNextCommand(out rejection) &&
                    monitor.Phase == BaiReadinessPhase.Frozen &&
                    monitor.PendingCommandCount == 0);
            });
            Case("T63_command_queue_limit_fails_closed", delegate {
                var monitor = NewMonitor("63"); monitor.Activate(); string rejection;
                for (int index = 0; index < BaiReadinessLimits.MaxPendingCommands; index++)
                    Require(monitor.TryEnqueueCommand(BaiReadinessCommand.Stop(
                        monitor.OperationId, "queued-stop-" + index, index + 1), out rejection));
                Require(!monitor.TryEnqueueCommand(BaiReadinessCommand.Stop(
                    monitor.OperationId, "queued-stop-overflow", 20), out rejection) &&
                    rejection == "REJECT_QUEUE_FULL");
            });
            Case("T64_saturated_currentness_fences_before_optional_event", delegate {
                var monitor = Room("64"); Saturate(monitor, 2);
                monitor.InvalidateCurrentness("AUTHORIZATION_EXPIRED", 3);
                AssertSaturatedStop(monitor, "AUTHORIZATION_EXPIRED", 4);
                Require(monitor.Windows[0].CurrentnessState == "INVALIDATED_WHILE_OPEN");
            });
            Case("T65_saturated_owner_stop_keeps_mandatory_trace", delegate {
                var monitor = Room("65"); Saturate(monitor, 2);
                string rejection;
                Require(monitor.TryEnqueueCommand(BaiReadinessCommand.End(
                    monitor.OperationId, "pending-65", 100), out rejection));
                monitor.RequestStop("OWNER_STOP", 3);
                AssertSaturatedStop(monitor, "OWNER_STOP", 4);
                Require(monitor.PendingCommandCount == 0);
            });
            Case("T66_saturated_watchdog_and_fault_stop_fence", delegate {
                var watchdog = Room("66a"); Saturate(watchdog, 2);
                watchdog.ObserveWatchdog(101);
                AssertSaturatedStop(watchdog, "WATCHDOG_OVERRUN", 102);
                var fault = Room("66b"); Saturate(fault, 2);
                fault.ObserveTransportFault("HMAC_FAILURE", 3);
                AssertSaturatedStop(fault, "HMAC_FAILURE", 4);
            });
            Case("T67_failed_command_does_not_reserve_epoch", delegate {
                var monitor = Frozen("67"); monitor.ObserveSettingsChanged("change-67", 1);
                const string hash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
                RequireThrows(delegate { monitor.FreezeSettings("epoch-next-67", "change-67", 2,
                    BaiReadinessFreezeEvidence.CreatePureTest("epoch-next-67", "change-67", 2, hash)); });
                monitor.FreezeSettings("epoch-next-67", "new-freeze-67", 2,
                    BaiReadinessFreezeEvidence.CreatePureTest("epoch-next-67", "new-freeze-67", 2, hash));
                Require(monitor.SettingsEpochCount == 2);
            });
            Case("T68_saturated_commands_have_no_partial_markers", delegate {
                var monitor = Frozen("68"); Saturate(monitor, 2);
                RequireThrows(delegate { monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone,
                    "room-68", "start-68", 3); });
                Require(monitor.Windows.Count == 0 && !monitor.Events.Any(x => x.CommandId == "start-68"));
                AssertSaturatedStop(monitor, "RESOURCE_LIMIT", 4);
                var room = Room("68b"); Saturate(room, 2);
                RequireThrows(delegate { room.EndWindow("end-68b", 3); });
                Require(!room.Events.Any(x => x.CommandId == "end-68b"));
                AssertSaturatedStop(room, "RESOURCE_LIMIT", 4);
            });
            Case("T69_publication_outcome_cannot_be_substituted", delegate {
                Require(typeof(BaiReadinessMonitor).GetMethod("CompletePublication",
                    BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public) == null);
                Require(typeof(BaiReadinessMetadataSinkCapability.PublicationResult).GetConstructors(
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).All(x => x.IsPrivate));
            });
            Case("T70_terminal_projection_is_one_shot", delegate {
                var monitor = NewMonitor("70"); monitor.Activate();
                monitor.RequestStop("OWNER_STOP", 1); monitor.MarkSettled(2);
                var projection = monitor.FreezeTerminalProjection();
                var root = Fields("clocks", Fields("started_at_utc", "a", "stop_requested_at_utc", "b", "settled_at_utc", "c"));
                projection.ApplyTo(root, new string('a', 64));
                RequireThrows(delegate { projection.ApplyTo(root, new string('a', 64)); });
                RequireThrows(delegate { monitor.FreezeTerminalProjection(); });
            });
            Case("T71_static_context_alias_is_severed", delegate {
                IDictionary<string, object> alias = null;
                var receipt = Receipt("op-71", null, delegate(IDictionary<string, object> root) { alias = root; });
                ((IDictionary<string, object>)alias["privacy"])["receipt_contains_audio"] = true;
                var text = Encoding.UTF8.GetString(receipt.SerializeCanonical());
                Require(text.Contains("\"receipt_contains_audio\":false"));
            });
            Case("T72_frozen_window_and_attestation_aliases_are_severed", delegate {
                BaiReadinessWindow alias = null;
                var receipt = Receipt("op-72", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "72"); alias = monitor.Windows[0];
                    monitor.EndWindow("end-72", 3); monitor.RequestStop("OWNER_STOP", 4); monitor.MarkSettled(5);
                });
                alias.Report(true); alias.Invalidate("forged-event", false, true);
                var text = Encoding.UTF8.GetString(receipt.SerializeCanonical());
                Require(!text.Contains("forged-event") && !text.Contains("OWNER_RED_INDICATOR_REPORTED"));
            });
            Case("T73_owner_report_flags_follow_events", delegate {
                var receipt = Receipt("op-73", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "73");
                    monitor.ReportObservation("room-73", "report-73", 3, true);
                    monitor.EndWindow("end-73", 4); monitor.RequestStop("OWNER_STOP", 5); monitor.MarkSettled(6);
                });
                Require(Encoding.UTF8.GetString(receipt.SerializeCanonical()).Contains("OWNER_RED_INDICATOR_REPORTED"));
                RequireThrows(delegate { Receipt("op-73b", PrepareClosedRoom, null,
                    delegate(IDictionary<string, object> root) {
                        ((IDictionary<string, object>)((object[])root["windows"])[0])["observation_flags"] =
                            new object[] { "OWNER_RED_INDICATOR_REPORTED", "UPSTREAM_LOSS_UNKNOWN" };
                    }); });
            });
            Case("T74_withdrawal_closes_open_window", delegate {
                var receipt = Receipt("op-74", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "74"); monitor.WithdrawWindow("room-74", "withdraw-74", 3);
                    monitor.RequestStop("OWNER_STOP", 4); monitor.MarkSettled(5);
                });
                Require(Encoding.UTF8.GetString(receipt.SerializeCanonical()).Contains("\"currentness_state\":\"WITHDRAWN\""));
            });
            Case("T75_transport_fault_counters_are_observed", delegate {
                foreach (var reason in new[] { "INCOMPLETE_PACKET", "HMAC_FAILURE", "NONCE_DRIFT" }) {
                    var receipt = Receipt("op-75-" + reason, delegate(BaiReadinessMonitor monitor, string hash) {
                        monitor.ObserveTransportFault(reason, 1); monitor.MarkSettled(2);
                    });
                    var text = Encoding.UTF8.GetString(receipt.SerializeCanonical());
                    string field = reason == "INCOMPLETE_PACKET" ? "incomplete_packets" :
                        reason == "HMAC_FAILURE" ? "hmac_failures" : "nonce_mismatches";
                    Require(text.Contains("\"" + field + "\":1") && text.Contains("\"connection_attempts\":1"));
                }
            });
            Case("T76_readback_cannot_outlive_subject", delegate {
                RequireThrows(delegate { Receipt("op-76", null,
                    delegate(IDictionary<string, object> root) { SetFreshnessBounds(root, true); }); });
            });
            Case("T77_readback_cannot_outlive_consent", delegate {
                RequireThrows(delegate { Receipt("op-77", null,
                    delegate(IDictionary<string, object> root) { SetFreshnessBounds(root, false); }); });
            });
            Case("T78_equal_freshness_bounds_are_valid", delegate {
                Require(Receipt("op-78").SerializeCanonical().Length > 0);
            });
            Case("T79_stop_frame_equals_final_cursor", delegate {
                RequireThrows(delegate { Receipt("op-79", delegate(BaiReadinessMonitor monitor, string hash) {
                    monitor.CommitPacket(0, 1, 1, 2, Planar(1, 0F, 0F), 1);
                    monitor.RequestStop("OWNER_STOP", 2); monitor.MarkSettled(3);
                }, null, delegate(IDictionary<string, object> root) {
                    var events = (object[])root["events"];
                    ((IDictionary<string, object>)events[events.Length - 3])["frame"] = 0;
                }); });
            });
            Case("T80_window_creation_order_is_validated", delegate {
                RequireThrows(delegate { Receipt("op-80", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "80"); monitor.EndWindow("end-80", 3);
                    monitor.StartWindow(BaiReadinessWindowPurpose.NormalSpeech, "speech-80", "speech-start-80", 4);
                    monitor.EndWindow("speech-end-80", 5); monitor.RequestStop("OWNER_STOP", 6); monitor.MarkSettled(7);
                }, null, delegate(IDictionary<string, object> root) {
                    var windows = (object[])root["windows"]; var first = windows[0]; windows[0] = windows[1]; windows[1] = first;
                }); });
            });
            Case("T81_speech_requires_prior_closed_room", delegate {
                RequireThrows(delegate { Receipt("op-81", PrepareClosedRoom, null,
                    delegate(IDictionary<string, object> root) {
                        var window = (IDictionary<string, object>)((object[])root["windows"])[0];
                        window["purpose"] = "NORMAL_SPEECH";
                        foreach (IDictionary<string, object> ev in (object[])root["events"]) {
                            if ((string)ev["code"] == "ROOM_TONE_STARTED") ev["code"] = "NORMAL_SPEECH_STARTED";
                            if ((string)ev["code"] == "ROOM_TONE_ENDED") ev["code"] = "NORMAL_SPEECH_ENDED";
                        }
                    }); });
            });
            Case("T82_owner_report_requires_matching_window", delegate {
                RequireThrows(delegate { Receipt("op-82", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "82"); monitor.ReportObservation("room-82", "report-82", 3, false);
                    monitor.EndWindow("end-82", 4); monitor.RequestStop("OWNER_STOP", 5); monitor.MarkSettled(6);
                }, null, delegate(IDictionary<string, object> root) {
                    foreach (IDictionary<string, object> ev in (object[])root["events"])
                        if ((string)ev["code"] == "OWNER_DISTORTION_REPORT") ev["window_id"] = "foreign-window";
                }); });
            });
            Case("T83_receipt_bytes_and_publication_are_one_shot", delegate {
                var receipt = Receipt("op-83"); var bytes = receipt.SerializeCanonical();
                string expectedHash;
                using (var sha = SHA256.Create()) expectedHash = BaiReadinessMetadataSinkCapability.Hex(sha.ComputeHash(bytes));
                bytes[0] = 0;
                RequireThrows(delegate { receipt.SerializeCanonical(); });
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown();
                var result = sink.Publish(receipt);
                Require(result.Outcome == BaiReadinessPublicationOutcome.Unknown && result.Sha256 == expectedHash);
                RequireThrows(delegate { sink.Publish(receipt); });
                RequireThrows(delegate { BaiReadinessMetadataSinkCapability.CreatePureTestUnknown().Publish(receipt); });
            });
            Case("T84_rejected_command_overflow_requests_resource_stop", delegate {
                var monitor = Frozen("84"); Saturate(monitor, 2); string rejection;
                Require(!monitor.TryEnqueueCommand(BaiReadinessCommand.Stop("foreign", "overflow-84", 3), out rejection));
                AssertSaturatedStop(monitor, "RESOURCE_LIMIT", 4);
            });
            Case("T85_publication_timeout_retains_task_without_late_upgrade", delegate {
                BaiReadinessMonitor monitor = null;
                var receipt = Receipt("op-85", delegate(BaiReadinessMonitor value, string hash) {
                    monitor = value; value.RequestStop("OWNER_STOP", 1); value.MarkSettled(2);
                });
                var release = new TaskCompletionSource<bool>();
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown(release.Task);
                try {
                    monitor.BeginPublicationAsync(receipt, sink).GetAwaiter().GetResult();
                    Require(monitor.PublicationReason == "PUBLICATION_TIMEOUT" &&
                        monitor.Lifecycle == BaiReadinessLifecycle.MetadataUnconfirmed &&
                        !monitor.RetainedPublicationTask.IsCompleted);
                } finally { release.SetResult(true); }
                monitor.RetainedLatePublicationObservation.GetAwaiter().GetResult();
                Require(monitor.Lifecycle == BaiReadinessLifecycle.MetadataUnconfirmed &&
                    monitor.PublicationReason == "PUBLICATION_TIMEOUT");
            });
            Case("T86_open_window_closes_on_global_revocation", delegate {
                var receipt = Receipt("op-86", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "86"); monitor.RequestStop("OWNER_STOP", 3); monitor.MarkSettled(4);
                });
                Require(Encoding.UTF8.GetString(receipt.SerializeCanonical()).Contains("INTERRUPTED_AT_REVOKE"));
            });
            Case("T87_epoch_invalidation_applies_to_both_windows", delegate {
                var receipt = Receipt("op-87", delegate(BaiReadinessMonitor monitor, string hash) {
                    PrepareRoom(monitor, hash, "87"); monitor.EndWindow("end-87", 3);
                    monitor.StartWindow(BaiReadinessWindowPurpose.NormalSpeech, "speech-87", "speech-start-87", 4);
                    monitor.ObserveSettingsChanged("change-87", 5);
                    monitor.RequestStop("OWNER_STOP", 6); monitor.MarkSettled(7);
                });
                var text = Encoding.UTF8.GetString(receipt.SerializeCanonical());
                Require(text.Contains("INVALIDATED_AFTER_CLOSE") && text.Contains("INVALIDATED_WHILE_OPEN"));
            });
            Case("T88_owner_stop_then_currentness_invalidates_once", delegate {
                AssertSecondaryRevocation("OWNER_STOP", "OWNER_REVOCATION", "88a");
                AssertSecondaryRevocation("OWNER_STOP", "AUTHORIZATION_EXPIRED", "88b");
            });
            Case("T89_hard_cap_then_currentness_invalidates_once", delegate {
                AssertSecondaryRevocation("HARD_CAP_REACHED", "OWNER_REVOCATION", "89a");
                AssertSecondaryRevocation("HARD_CAP_REACHED", "AUTHORIZATION_EXPIRED", "89b");
            });
            Case("T90_secondary_reason_cannot_keep_current_projection", delegate {
                RequireThrows(delegate { Receipt("op-90", PrepareClosedRoom, null,
                    delegate(IDictionary<string, object> root) {
                        ((IDictionary<string, object>)root["terminal"])["secondary_reasons"] =
                            new object[] { "OWNER_REVOCATION" };
                    }); });
            });
            Case("T91_late_reason_cannot_mutate_frozen_graph", delegate {
                var monitor = Room("91"); monitor.RequestStop("OWNER_STOP", 2); monitor.MarkSettled(3);
                var projection = monitor.FreezeTerminalProjection(); int count = monitor.Events.Count;
                RequireThrows(delegate { monitor.RequestStop("OWNER_REVOCATION", 4); });
                RequireThrows(delegate { monitor.InvalidateCurrentness("AUTHORIZATION_EXPIRED", 4); });
                Require(monitor.Events.Count == count && monitor.Windows[0].CurrentnessState == "SAME_EPOCH_AT_CLOSE");
            });
            Case("T92_freeze_rejects_ac_fixed_role_atomically", delegate { AssertInvalidFreeze(0); });
            Case("T93_freeze_rejects_fan_fixed_role_atomically", delegate { AssertInvalidFreeze(1); });
            Case("T94_freeze_rejects_cross_subject_atomically", delegate { AssertInvalidFreeze(2); });
            Case("T95_freeze_rejects_cross_command_atomically", delegate { AssertInvalidFreeze(3); });
            Case("T96_freeze_rejects_cross_tick_atomically", delegate { AssertInvalidFreeze(4); });
            Case("T97_freeze_rejects_settings_digest_atomically", delegate { AssertInvalidFreeze(5); });
            Case("T98_freeze_rejects_subject_digest_atomically", delegate { AssertInvalidFreeze(6); });
            Case("T99_freeze_rejects_revoked_assertion_atomically", delegate { AssertInvalidFreeze(7); });
            Case("T100_invalid_dto_has_owned_no_artifact_terminal", delegate {
                var monitor = SettledForPublication("100");
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown();
                monitor.BeginPreparedPublicationAsync(Fields("invalid", true), sink).GetAwaiter().GetResult();
                AssertNoArtifact(monitor, "INVALID_DTO_NO_ARTIFACT"); Require(!sink.EffectStarted);
                RequireThrows(delegate { monitor.BeginPreparedPublicationAsync(null, null); });
            });
            Case("T101_missing_sink_has_owned_create_failure_terminal", delegate {
                var monitor = SettledForPublication("101");
                monitor.BeginPreparedPublicationAsync(null, null).GetAwaiter().GetResult();
                AssertNoArtifact(monitor, "CREATE_FAILED_NO_ARTIFACT");
            });
            Case("T102_consumed_projection_cannot_claim_no_artifact", delegate {
                var monitor = SettledForPublication("102"); var projection = monitor.FreezeTerminalProjection();
                projection.Consume();
                RequireThrows(delegate {
                    BaiReadinessMetadataSinkCapability.PublicationResult.StartPrepared(null, projection, null);
                });
            });
            Case("T103_used_sink_cannot_claim_no_artifact", delegate {
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown();
                sink.Publish(Receipt("op-103-first"));
                var monitor = SettledForPublication("103");
                monitor.BeginPreparedPublicationAsync(null, sink).GetAwaiter().GetResult();
                Require(monitor.Lifecycle == BaiReadinessLifecycle.MetadataUnconfirmed &&
                    monitor.PublicationOutcome == BaiReadinessPublicationOutcome.Unknown && monitor.PublicationProof == null);
            });
            Case("T104_pending_sink_cannot_claim_no_artifact", delegate {
                var release = new TaskCompletionSource<bool>();
                var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown(release.Task);
                Task<BaiReadinessMetadataSinkCapability.PublicationResult> pending = null;
                Receipt("op-104", null, null, null,
                    delegate(BaiReadinessMonitor monitor, IDictionary<string, object> root) {
                        pending = BaiReadinessMetadataSinkCapability.PublicationResult.StartPrepared(
                            sink, monitor.FreezeTerminalProjection(), root);
                    });
                try {
                    var next = SettledForPublication("104-next");
                    next.BeginPreparedPublicationAsync(null, sink).GetAwaiter().GetResult();
                    Require(next.PublicationOutcome == BaiReadinessPublicationOutcome.Unknown && next.PublicationProof == null);
                } finally { release.SetResult(true); }
                Require(pending.GetAwaiter().GetResult().Outcome == BaiReadinessPublicationOutcome.Unknown);
            });
            Case("T105_valid_prepared_dto_reaches_owned_sink", delegate {
                Receipt("op-105", null, null, null,
                    delegate(BaiReadinessMonitor monitor, IDictionary<string, object> root) {
                        var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown();
                        monitor.BeginPreparedPublicationAsync(root, sink).GetAwaiter().GetResult();
                        Require(sink.EffectStarted && monitor.PublicationProof != null &&
                            monitor.PublicationOutcome == BaiReadinessPublicationOutcome.Unknown &&
                            monitor.PublicationProof.ByteCount > 0);
                    });
            });
            Case("T106_prepared_dto_severs_caller_alias_before_task", delegate {
                Receipt("op-106", null, null, null,
                    delegate(BaiReadinessMonitor monitor, IDictionary<string, object> root) {
                        var release = new TaskCompletionSource<bool>();
                        var sink = BaiReadinessMetadataSinkCapability.CreatePureTestUnknown(release.Task);
                        var completion = monitor.BeginPreparedPublicationAsync(root, sink);
                        root.Clear(); release.SetResult(true); completion.GetAwaiter().GetResult();
                        Require(monitor.PublicationProof != null && monitor.PublicationProof.ByteCount > 0 &&
                            monitor.PublicationOutcome == BaiReadinessPublicationOutcome.Unknown);
                    });
            });
            Require(executed == 106);
            return 0;
        } catch (Exception) { return 97; }
    }

    private static BaiReadinessMonitor NewMonitor(string suffix)
    {
        return BaiReadinessMonitor.CreatePureTest("op-" + suffix, "session-" + suffix, 2);
    }

    private static BaiReadinessMonitor SettledForPublication(string suffix)
    {
        var monitor = NewMonitor(suffix); monitor.Activate();
        monitor.RequestStop("OWNER_STOP", 1); monitor.MarkSettled(2); return monitor;
    }

    private static void AssertNoArtifact(BaiReadinessMonitor monitor, string reason)
    {
        var proof = monitor.PublicationProof;
        Require(monitor.Lifecycle == BaiReadinessLifecycle.Terminal &&
            monitor.PublicationOutcome == BaiReadinessPublicationOutcome.NotPublishedConfirmed &&
            monitor.PublicationReason == reason && proof != null && proof.Reason == reason &&
            proof.Path == null && proof.PendingPath == null && proof.FinalPath == null &&
            proof.ByteCount == 0 && proof.Sha256 == null && proof.PhysicalIdentity == null);
    }

    private static void AssertSecondaryRevocation(string primary, string secondary, string suffix)
    {
        var receipt = Receipt("op-" + suffix, delegate(BaiReadinessMonitor monitor, string hash) {
            PrepareRoom(monitor, hash, suffix); monitor.EndWindow("end-" + suffix, 3);
            monitor.StartWindow(BaiReadinessWindowPurpose.NormalSpeech,
                "speech-" + suffix, "speech-start-" + suffix, 4);
            monitor.RequestStop(primary, 5); int count = monitor.Events.Count;
            monitor.RequestStop(secondary, 6); monitor.InvalidateCurrentness(secondary, 6);
            Require(monitor.StopReason == primary && monitor.Events.Count == count &&
                monitor.Windows[0].CurrentnessState == "INVALIDATED_AFTER_CLOSE" &&
                monitor.Windows[1].CurrentnessState == "INVALIDATED_WHILE_OPEN");
            monitor.MarkSettled(7);
        });
        string text = Encoding.UTF8.GetString(receipt.SerializeCanonical());
        Require(text.Contains("REVOKED") && text.Contains("INVALIDATED_WHILE_OPEN"));
    }

    private static void AssertInvalidFreeze(int variant)
    {
        string suffix = "bad-freeze-" + variant, epoch = "epoch-" + suffix, command = "freeze-" + suffix;
        string subject = "sha256:" + new string('a', 64), settings = new string('a', 64);
        var monitor = NewMonitor(suffix); monitor.Activate(); int count = monitor.Events.Count;
        var ac = BaiReadinessAttestationRecord.Current(variant == 0 ? "ATTESTED_FIXED" : "ATTESTED_OFF",
            "ac-" + suffix, variant == 2 ? "sha256:" + new string('b', 64) :
                variant == 6 ? "sha256:BAD" : subject,
            variant == 3 ? "wrong-command" : command, variant == 4 ? 2 : 1);
        if (variant == 7) ac.Invalidate("old-event");
        var fan = BaiReadinessAttestationRecord.Current(variant == 1 ? "ATTESTED_FIXED" : "ATTESTED_NOT_OFF",
            "fan-" + suffix, subject, command, 1);
        var fixedSettings = BaiReadinessAttestationRecord.Current("ATTESTED_FIXED", "fixed-" + suffix,
            subject, command, 1);
        var evidence = new BaiReadinessFreezeEvidence("settings-" + suffix,
            variant == 5 ? new string('A', 64) : settings, ac, fan, fixedSettings);
        RequireThrows(delegate { monitor.FreezeSettings(epoch, command, 1, evidence); });
        Require(monitor.Phase == BaiReadinessPhase.AdjustmentOnly && monitor.Events.Count == count &&
            monitor.Windows.Count == 0 && monitor.StopReason == null);
        // Reusing the exact epoch/command proves rejection consumed no IDs or epoch slot.
        monitor.FreezeSettings(epoch, command, 1,
            BaiReadinessFreezeEvidence.CreatePureTest(epoch, command, 1, subject));
        Require(monitor.Phase == BaiReadinessPhase.Frozen && monitor.Events.Count == count + 1);
    }

    private static void Saturate(BaiReadinessMonitor monitor, long tick)
    {
        string rejection; int index = 0;
        while (monitor.Events.Count < BaiReadinessLimits.MaxEvents - 3)
            Require(!monitor.TryEnqueueCommand(BaiReadinessCommand.Stop("foreign-op",
                "rejected-" + index++, tick), out rejection));
        Require(monitor.StopReason == null);
    }

    private static void AssertSaturatedStop(BaiReadinessMonitor monitor, string reason, long settledTick)
    {
        Require(monitor.StopReason == reason && !monitor.CommitPacket(1, 1, 1, 2,
            Planar(1, 0F, 0F), settledTick));
        monitor.MarkSettled(settledTick);
        Require(monitor.Events.Count == 64 && monitor.Events[61].Code == "STOP_REQUESTED" &&
            monitor.Events[62].Code == "REVOCATION_LINEARIZED" && monitor.Events[63].Code == "RECEIVER_SETTLED");
    }

    private static void PrepareRoom(BaiReadinessMonitor monitor, string hash, string suffix)
    {
        monitor.FreezeSettings("epoch-" + suffix, "freeze-" + suffix, 1,
            BaiReadinessFreezeEvidence.CreatePureTest("epoch-" + suffix, "freeze-" + suffix, 1, hash));
        monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone, "room-" + suffix, "start-" + suffix, 2);
    }

    private static void PrepareClosedRoom(BaiReadinessMonitor monitor, string hash)
    {
        PrepareRoom(monitor, hash, "closed"); monitor.EndWindow("end-closed", 3);
        monitor.RequestStop("OWNER_STOP", 4); monitor.MarkSettled(5);
    }

    private static void SetFreshnessBounds(IDictionary<string, object> root, bool shortenSubject)
    {
        var admission = (IDictionary<string, object>)root["admission"];
        var subject = (IDictionary<string, object>)admission["owner_subject_binding"];
        var consent = (IDictionary<string, object>)admission["owner_capture_consent_evaluation"];
        var readback = (IDictionary<string, object>)admission["start_currentness_readback"];
        admission["expires_at_utc"] = "2026-01-01T00:05:00.000000Z";
        if (shortenSubject) subject["fresh_until"] = admission["expires_at_utc"];
        else consent["expires_at"] = admission["expires_at_utc"];
        subject["binding_sha256"] = ExternalDigest(subject, "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1", "binding_sha256");
        consent["evaluation_sha256"] = ExternalDigest(consent, "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1", "evaluation_sha256");
        readback["subject_binding_sha256"] = subject["binding_sha256"];
        readback["consent_evaluation_sha256"] = consent["evaluation_sha256"];
        readback["readback_sha256"] = ExternalDigest(readback, "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1", "readback_sha256");
    }

    private static BaiReadinessMonitor Frozen(string suffix)
    {
        var monitor = NewMonitor(suffix); monitor.Activate();
        const string subjectHash =
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        var epoch = "epoch-" + suffix;
        var command = "freeze-" + suffix;
        monitor.FreezeSettings(epoch, command, 0,
            BaiReadinessFreezeEvidence.CreatePureTest(epoch, command, 0, subjectHash));
        return monitor;
    }

    private static BaiReadinessMonitor Room(string suffix)
    {
        var monitor = Frozen(suffix);
        monitor.StartWindow(BaiReadinessWindowPurpose.RoomTone,
            "room-" + suffix, "room-start-" + suffix, 1);
        return monitor;
    }

    private static byte[] Planar(int frames, params float[] perChannel)
    {
        var result = new byte[frames * perChannel.Length * 4];
        for (int channel = 0; channel < perChannel.Length; channel++)
            for (int frame = 0; frame < frames; frame++)
                Buffer.BlockCopy(BitConverter.GetBytes(perChannel[channel]), 0,
                    result, (channel * frames + frame) * 4, 4);
        return result;
    }

    private static BaiReadinessReceipt Receipt(string operationId)
    {
        return Receipt(operationId, null, null);
    }

    private static BaiReadinessReceipt Receipt(string operationId,
        Action<BaiReadinessMonitor, string> prepare)
    {
        return Receipt(operationId, prepare, null);
    }

    private static BaiReadinessReceipt Receipt(string operationId,
        Action<BaiReadinessMonitor, string> prepare,
        Action<IDictionary<string, object>> tamper,
        Action<IDictionary<string, object>> projectedTamper = null,
        Action<BaiReadinessMonitor, IDictionary<string, object>> preparedPublication = null)
    {
        const string hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        const string externalHash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        const string subjectRef = "11111111-1111-1111-1111-111111111111";
        const string queryRef = "22222222-2222-2222-2222-222222222222";
        const string created = "2026-01-01T00:00:00.000000Z";
        const string observed = "2026-01-01T00:00:01.000000Z";
        const string effect = "2026-01-01T00:00:02.000000Z";
        const string expires = "2026-01-01T00:10:00.000000Z";
        var startCommand = "owner-start-" + operationId;
        var stopCommand = "stop-" + operationId;
        var subject = Fields(
            "record_type", "OwnerVoiceSubjectBindingV1", "schema_version", 1,
            "canonical_owner_task", "TASK-046", "receipt_role", "OWNER_VOICE_SUBJECT_BINDING",
            "project_id", "BAI_VIDEO_PRODUCTION", "subject_ref", subjectRef,
            "subject_revision", 1, "subject_revision_sha256", null,
            "predecessor_subject_revision_sha256", null, "currentness_state", "CURRENT",
            "currentness_readback_sha256", externalHash, "created_at", created,
            "observed_at", observed, "fresh_until", expires,
            "trusted_time_binding_sha256", externalHash, "binding_sha256", null);
        subject["subject_revision_sha256"] = ExternalDigest(Fields(
            "project_id", subject["project_id"], "subject_ref", subject["subject_ref"],
            "subject_revision", subject["subject_revision"],
            "predecessor_subject_revision_sha256", subject["predecessor_subject_revision_sha256"]),
            "TASK046_OWNER_VOICE_SUBJECT_REVISION_V1", null);
        subject["binding_sha256"] = ExternalDigest(subject,
            "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1", "binding_sha256");
        var consent = Fields(
            "record_type", "OwnerVoicePurposeConsentEvaluationV1", "schema_version", 1,
            "canonical_owner_task", "TASK-046", "receipt_role",
            "OWNER_VOICE_PURPOSE_CONSENT_EVALUATION", "project_id", "BAI_VIDEO_PRODUCTION",
            "subject_ref", subjectRef, "subject_revision", 1,
            "subject_revision_sha256", subject["subject_revision_sha256"], "evaluation_revision", 1,
            "purpose", "OWNER_VOICE_CAPTURE", "decision", "ALLOW", "rights_scope",
            "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY", "policy_revision_sha256", externalHash,
            "predecessor_evaluation_sha256", null, "issued_at", created,
            "observed_at", observed, "expires_at", expires,
            "revocation_currentness_sha256", externalHash,
            "trusted_time_binding_sha256", externalHash, "evaluation_sha256", null);
        consent["evaluation_sha256"] = ExternalDigest(consent,
            "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1", "evaluation_sha256");
        var readback = Fields(
            "record_type", "OwnerVoiceCurrentnessReadbackV1", "schema_version", 1,
            "canonical_owner_task", "TASK-046", "receipt_role", "OWNER_VOICE_CURRENTNESS_READBACK",
            "project_id", "BAI_VIDEO_PRODUCTION", "subject_ref", subjectRef,
            "query_ref", queryRef, "subject_binding_sha256", subject["binding_sha256"],
            "consent_evaluation_sha256", consent["evaluation_sha256"], "head_sha256", externalHash,
            "head_event_sequence", 1, "head_event_sha256", externalHash,
            "subject_revision_sha256", subject["subject_revision_sha256"],
            "policy_revision_sha256", externalHash,
            "purpose", "OWNER_VOICE_CAPTURE", "rights_scope",
            "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY", "consent_decision", "ALLOW",
            "currentness_state", "CURRENT", "reason_codes", new object[] { "CURRENT_MATCH" },
            "observed_at", observed, "fresh_until", expires,
            "trusted_time_binding_sha256", externalHash, "readback_sha256", null);
        readback["readback_sha256"] = ExternalDigest(readback,
            "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1", "readback_sha256");
        var root = Fields(
            "admission", Fields(
                "envelope_ref", "envelope-1", "envelope_sha256", hash,
                "owner_start_command_id", startCommand, "authorized_start_count", 1,
                "expires_at_utc", expires, "owner_subject_binding", subject,
                "owner_capture_consent_evaluation", consent, "start_currentness_readback", readback,
                "execution_authorization_ref", "execution-1", "execution_authorization_sha256", hash,
                "admitted_effect_time_utc", effect, "durable_exclusion_token_ref", "exclusion-1",
                "durable_exclusion_readback_sha256", hash, "durable_exclusion_head_sha256", hash),
            "authority", Fields("measurement_facts_only", true, "quality_decision_authority", false,
                "task048_consumer_allocated", false, "dataset_adoption_authority", false,
                "training_authority", false, "production_eligible", false),
            "capture_binding", Fields(
                "controller_sha256", hash, "plugin_sha256", hash, "obs_image_sha256", hash,
                "process_identity_ref", "process-1", "source_chain_ref", "source-1",
                "source_chain_sha256", hash, "source_assurance",
                "OWNER_ATTESTED_SINGLE_SOURCE_NOT_WIRE_PROVEN", "format_ref", "format-1",
                "sample_rate_hz", 48000, "channel_layout_ref", "stereo-1", "channel_count", 2,
                "format_assurance", "EXTERNAL_SNAPSHOT_BOUND_NOT_WIRE_PROVEN", "wire_version", 1,
                "source_clock_mapping_state", "UNBOUND", "queue_freshness_state",
                "NOT_PROVEN_WIRE_V1"),
            "clocks", Fields("started_at_utc", effect, "stop_requested_at_utc", effect,
                "settled_at_utc", effect, "monotonic_frequency", 10000000,
                "start_tick", 0, "stop_request_tick", 10, "revoke_tick", 11, "settled_tick", 12),
            "events", null,
            "limits", Fields("revision", 1, "hard_cap_minutes", 3, "arm_budget_ms", 10000,
                "no_input_budget_ms", 5000, "stop_settlement_budget_ms", 2000,
                "metadata_publication_budget_ms", 2000, "watchdog_max_interval_ms", 100,
                "max_pending_commands", 16, "max_settings_epochs", 8, "max_windows", 16,
                "max_events", 64, "max_receipt_bytes", 262144),
            "measurement_algorithm", Fields("id", "task047.received-float32-aggregate.v1",
                "revision", 1, "sample_representation", "PLANAR_LE_IEEE754_BINARY32",
                "accumulation", "BINARY64_IN_RECEIVED_ORDER", "excursion_comparison",
                "FINITE_ABS_GTE_0_9999", "channel_aggregation", "SEPARATE_CHANNELS"),
            "mode", "READINESS_MONITOR", "operation_id", operationId,
            "privacy", Fields("controller_audio_file_created", false,
                "recording_sink_capability_present", false, "receipt_contains_audio", false,
                "controller_transcript_created", false, "controller_external_audio_transfer", false,
                "controller_session_key_persisted", false, "metadata_only", true,
                "secure_ram_erasure_claimed", false, "whole_machine_audio_persistence_state",
                "NOT_CONFIRMED", "whole_machine_audio_persistence_reason",
                "EXTERNAL_HOST_OS_BEHAVIOR_OUT_OF_SCOPE"),
            "schema", BaiReadinessReceipt.SchemaId, "schema_version", 1,
            "session_id", "session-" + operationId, "settings_epochs", null,
            "terminal", null, "transport", null,
            "unknowns", Fields("source_callback_drop_count_state", "UNKNOWN_WIRE_V1",
                "acoustic_dropout_count_state", "NOT_MEASURED", "speech_occupancy_state",
                "NOT_MEASURED", "noise_policy_state", "UNALLOCATED_TASK048",
                "snr_evaluation_state", "NOT_EVALUATED", "true_peak_state", "NOT_MEASURED",
                "adc_distortion_state", "NOT_MEASURED", "source_wire_identity_state",
                "UNAVAILABLE_WIRE_V1", "source_clock_mapping_state", "UNBOUND",
                "queue_freshness_state", "NOT_PROVEN_WIRE_V1", "producer_stop_ack_state",
                "UNAVAILABLE_LEGACY_WIRE", "window_minimum_eligibility_state",
                "UNALLOCATED_TASK048"),
            "windows", null);
        var monitor = BaiReadinessMonitor.CreatePureTest(
            operationId, "session-" + operationId, 2, (string)subject["binding_sha256"]);
        monitor.Activate();
        if (prepare == null) {
            monitor.RequestStop("OWNER_STOP", stopCommand, 10);
            monitor.MarkSettling();
            monitor.MarkSettled(12);
        } else prepare(monitor, (string)subject["binding_sha256"]);
        if (tamper != null) tamper(root);
        if (preparedPublication != null) { preparedPublication(monitor, root); return null; }
        if (projectedTamper != null) {
            monitor.FreezeTerminalProjection().ApplyTo(root,
                BaiReadinessReceiptSemanticValidator.ComputeCaptureBindingHash(
                    (System.Collections.IDictionary)root["capture_binding"]));
            projectedTamper(root);
            return BaiReadinessReceipt.CreateForPureTest(root);
        }
        return BaiReadinessReceipt.CreateFromTerminalProjection(
            root, monitor.FreezeTerminalProjection());
    }

    private static string ExternalDigest(IDictionary<string, object> source,
        string domain, string excludedKey)
    {
        var preimage = new SortedDictionary<string, object>(StringComparer.Ordinal);
        foreach (var pair in source)
            if (!String.Equals(pair.Key, excludedKey, StringComparison.Ordinal))
                preimage.Add(pair.Key, pair.Value);
        var json = new StringBuilder();
        BaiReadinessCanonicalJson.WriteValue(json, preimage);
        var prefix = Encoding.ASCII.GetBytes(domain);
        var body = new UTF8Encoding(false, true).GetBytes(json.ToString());
        var bytes = new byte[prefix.Length + 1 + body.Length];
        Buffer.BlockCopy(prefix, 0, bytes, 0, prefix.Length);
        Buffer.BlockCopy(body, 0, bytes, prefix.Length + 1, body.Length);
        try {
            using (var sha = SHA256.Create())
                return "sha256:" + BaiReadinessMetadataSinkCapability.Hex(sha.ComputeHash(bytes));
        } finally {
            System.Array.Clear(bytes, 0, bytes.Length);
        }
    }

    private static Dictionary<string, object> Fields(params object[] pairs)
    {
        if (pairs.Length % 2 != 0) throw new InvalidOperationException("Fixture pairs");
        var result = new Dictionary<string, object>(StringComparer.Ordinal);
        for (int index = 0; index < pairs.Length; index += 2)
            result.Add((string)pairs[index], pairs[index + 1]);
        return result;
    }

    private static bool IsLowerHex(char value)
    {
        return value >= '0' && value <= '9' || value >= 'a' && value <= 'f';
    }

    private static void Case(string name, Action action)
    {
        if (String.IsNullOrEmpty(name)) throw new InvalidOperationException();
        action();
        executed++;
    }

    private static void Require(bool condition)
    {
        if (!condition) throw new InvalidOperationException();
    }

    private static void RequireThrows(Action action)
    {
        try { action(); } catch { return; }
        throw new InvalidOperationException("Expected exception");
    }
}
