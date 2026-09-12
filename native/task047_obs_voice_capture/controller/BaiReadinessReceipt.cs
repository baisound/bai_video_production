using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32.SafeHandles;

internal sealed class BaiReadinessReceipt
{
    internal const string SchemaId = "bvp.task047.readiness-monitor-receipt.v1";
    internal const string EmbeddedSchemaResource = "BVP.Task047.ReadinessMonitorReceiptV1.Schema";
    internal const string EmbeddedSchemaSha256 = "61e87d762db8d0fbc28a95dc4c3c7642b83c19bb1a6d197e2fdd1ebc6ff18472";
    private static readonly string[] ExactRootKeys = {
        "admission", "authority", "capture_binding", "clocks", "events", "limits",
        "measurement_algorithm", "mode", "operation_id", "privacy", "schema",
        "schema_version", "session_id", "settings_epochs", "terminal", "transport",
        "unknowns", "windows"
    };
    private readonly SortedDictionary<string, object> root;
    private readonly byte[] canonicalBytes;
    private readonly BaiReadinessTerminalProjection sourceProjection;
    private int serializationClaimed;
    private int publicationClaimed;

    private BaiReadinessReceipt(SortedDictionary<string, object> value,
        BaiReadinessTerminalProjection projection = null)
    {
        root = CopyRoot(value);
        sourceProjection = projection;
        Validate();
        var builder = new StringBuilder();
        BaiReadinessCanonicalJson.WriteValue(builder, root);
        builder.Append('\n');
        canonicalBytes = new UTF8Encoding(false, true).GetBytes(builder.ToString());
        if (canonicalBytes.Length > BaiReadinessLimits.MaxReceiptBytes)
            throw new InvalidDataException("MAX_RECEIPT_BYTES");
    }

    internal string OperationId { get { return (string)root["operation_id"]; } }
    internal BaiReadinessTerminalProjection SourceProjection { get { return sourceProjection; } }

    internal static BaiReadinessReceipt CreateForPureTest(IDictionary<string, object> values)
    {
        if (values == null) throw new ArgumentNullException("values");
        return new BaiReadinessReceipt(CopyRoot(values));
    }

    internal static BaiReadinessReceipt CreateFromTerminalProjection(
        IDictionary<string, object> staticContext, BaiReadinessTerminalProjection projection)
    {
        if (projection == null) throw new ArgumentNullException("projection");
        return CreateFromConsumption(staticContext, projection.Consume());
    }

    internal static BaiReadinessReceipt CreateFromConsumption(
        IDictionary<string, object> staticContext, BaiReadinessTerminalProjection.Consumption consumption)
    {
        if (staticContext == null) throw new ArgumentNullException("staticContext");
        if (consumption == null) throw new ArgumentNullException("consumption");
        var copy = CopyRoot(staticContext);
        var capture = copy["capture_binding"] as IDictionary;
        if (capture == null) throw new InvalidDataException("CAPTURE_BINDING_OBJECT");
        consumption.ApplyTo(copy,
            BaiReadinessReceiptSemanticValidator.ComputeCaptureBindingHash(capture));
        return new BaiReadinessReceipt(copy, consumption.Owner);
    }

    internal byte[] SerializeCanonical()
    {
        if (Interlocked.Exchange(ref serializationClaimed, 1) != 0)
            throw new InvalidOperationException("SERIALIZATION_ALREADY_CLAIMED");
        return (byte[])canonicalBytes.Clone();
    }

    internal bool IsFrom(BaiReadinessTerminalProjection projection)
    {
        return projection != null && Object.ReferenceEquals(sourceProjection, projection);
    }

    internal byte[] ClaimPublicationBytes()
    {
        if (Interlocked.Exchange(ref publicationClaimed, 1) != 0)
            throw new InvalidOperationException("PUBLICATION_ALREADY_CLAIMED");
        return (byte[])canonicalBytes.Clone();
    }

    private static SortedDictionary<string, object> CopyRoot(IDictionary<string, object> value)
    {
        return (SortedDictionary<string, object>)CopyJson(value);
    }

    // Closed JSON values only. No caller collection, array, epoch or window is retained.
    internal static object CopyJson(object value, int depth = 0)
    {
        if (depth > 32) throw new InvalidDataException("JSON_DEPTH");
        if (value == null || value is string || value is bool || value is byte ||
            value is short || value is int || value is long || value is ushort ||
            value is uint || value is ulong || value is double || value is float ||
            value is decimal) return value;
        var dictionary = value as IDictionary;
        if (dictionary != null) {
            var copy = new SortedDictionary<string, object>(StringComparer.Ordinal);
            foreach (DictionaryEntry pair in dictionary) {
                var key = pair.Key as string;
                if (String.IsNullOrEmpty(key)) throw new InvalidDataException("OBJECT_KEY");
                copy.Add(key, CopyJson(pair.Value, depth + 1));
            }
            return copy;
        }
        var sequence = value as IEnumerable;
        if (sequence != null) {
            var copy = new List<object>();
            foreach (var item in sequence) {
                if (copy.Count >= BaiReadinessLimits.MaxEvents * 8)
                    throw new InvalidDataException("ARRAY_BOUND");
                copy.Add(CopyJson(item, depth + 1));
            }
            return copy.ToArray();
        }
        throw new InvalidDataException("UNSUPPORTED_JSON_VALUE");
    }

    internal void Validate()
    {
        if (root.Count != ExactRootKeys.Length) throw new InvalidDataException("ROOT_FIELD_COUNT");
        for (int index = 0; index < ExactRootKeys.Length; index++) {
            if (!root.ContainsKey(ExactRootKeys[index])) throw new InvalidDataException("ROOT_FIELD_MISSING");
        }
        foreach (var key in root.Keys) {
            if (Array.BinarySearch(ExactRootKeys, key, StringComparer.Ordinal) < 0)
                throw new InvalidDataException("ROOT_FIELD_UNKNOWN");
        }
        if (!Object.Equals(root["schema"], SchemaId) || !Object.Equals(root["schema_version"], 1L) &&
            !Object.Equals(root["schema_version"], 1))
            throw new InvalidDataException("SCHEMA_IDENTITY");
        if (!Object.Equals(root["mode"], "READINESS_MONITOR")) throw new InvalidDataException("MODE");
        BaiReadinessAdmission.RequireId(root["operation_id"] as string);
        BaiReadinessAdmission.RequireId(root["session_id"] as string);
        if (Object.Equals(root["operation_id"], root["session_id"]))
            throw new InvalidDataException("OPERATION_SESSION_COLLISION");
        ValidateValue(root, 0);
        BaiReadinessReceiptSemanticValidator.Validate(root);
    }

    private static void ValidateValue(object value, int depth)
    {
        if (depth > 32) throw new InvalidDataException("JSON_DEPTH");
        if (value == null || value is string || value is bool) return;
        if (value is double) {
            var number = (double)value;
            if (Double.IsNaN(number) || Double.IsInfinity(number))
                throw new InvalidDataException("NONFINITE_JSON_NUMBER");
            return;
        }
        if (value is float) {
            var number = (float)value;
            if (Single.IsNaN(number) || Single.IsInfinity(number))
                throw new InvalidDataException("NONFINITE_JSON_NUMBER");
            return;
        }
        if (value is byte || value is short || value is int || value is long ||
            value is ushort || value is uint || value is ulong || value is decimal) return;
        var dictionary = value as IDictionary;
        if (dictionary != null) {
            var keys = new HashSet<string>(StringComparer.Ordinal);
            foreach (DictionaryEntry pair in dictionary) {
                var key = pair.Key as string;
                if (String.IsNullOrEmpty(key) || !keys.Add(key))
                    throw new InvalidDataException("OBJECT_KEY");
                ValidateValue(pair.Value, depth + 1);
            }
            return;
        }
        var enumerable = value as IEnumerable;
        if (enumerable != null) {
            int count = 0;
            foreach (var item in enumerable) {
                if (++count > BaiReadinessLimits.MaxEvents * 8)
                    throw new InvalidDataException("ARRAY_BOUND");
                ValidateValue(item, depth + 1);
            }
            return;
        }
        throw new InvalidDataException("UNSUPPORTED_JSON_VALUE");
    }

    internal static byte[] LoadAndVerifyEmbeddedSchema()
    {
        using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(EmbeddedSchemaResource)) {
            if (stream == null) throw new InvalidDataException("READINESS_SCHEMA_RESOURCE_MISSING");
            using (var memory = new MemoryStream()) {
                stream.CopyTo(memory);
                var bytes = memory.ToArray();
                string hash;
                using (var sha = SHA256.Create()) hash = BaiReadinessMetadataSinkCapability.Hex(sha.ComputeHash(bytes));
                if (!String.Equals(hash, EmbeddedSchemaSha256, StringComparison.Ordinal))
                    throw new InvalidDataException("READINESS_SCHEMA_RESOURCE_MISMATCH");
                return bytes;
            }
        }
    }
}

internal static class BaiReadinessReceiptSemanticValidator
{
    private const long MaxExact = BaiReadinessLimits.MaxExactJsonInteger;
    private static readonly string[] StopReasons = {
        "OWNER_STOP", "HARD_CAP_REACHED", "OWNER_REVOCATION", "AUTHORIZATION_EXPIRED",
        "AUTHORIZATION_CURRENTNESS_UNKNOWN", "FORM_CLOSE", "OBS_IDENTITY_DRIFT",
        "SOURCE_BINDING_DRIFT", "FORMAT_DRIFT", "ENVIRONMENT_ATTESTATION_REVOKED",
        "ARM_TIMEOUT", "NO_INPUT_TIMEOUT", "WATCHDOG_OVERRUN", "PIPE_CLOSED",
        "PIPE_FAILURE", "INVALID_HEADER", "INCOMPLETE_PACKET", "HMAC_FAILURE",
        "NONCE_DRIFT", "SEQUENCE_GAP", "SEQUENCE_ORDER_ERROR",
        "SOURCE_TIMESTAMP_REGRESSION", "NONFINITE_INPUT", "ARITHMETIC_OVERFLOW",
        "RESOURCE_LIMIT", "INTERNAL_INVARIANT_FAILURE"
    };
    private static readonly string[] EventCodes = {
        "OWNER_START", "SETTINGS_FROZEN", "ROOM_TONE_STARTED", "ROOM_TONE_ENDED",
        "NORMAL_SPEECH_STARTED", "NORMAL_SPEECH_ENDED", "SETTINGS_CHANGED",
        "WINDOW_WITHDRAWN", "OWNER_DISTORTION_REPORT", "OWNER_RED_REPORT",
        "CURRENTNESS_INVALIDATED", "STOP_REQUESTED", "REVOCATION_LINEARIZED",
        "RECEIVER_SETTLED", "COMMAND_REJECTED"
    };
    private static readonly string[] Rejections = {
        "REJECT_WRONG_OPERATION", "REJECT_WRONG_PHASE", "REJECT_WRONG_EPOCH",
        "REJECT_ALREADY_STOPPING", "REJECT_QUEUE_FULL", "REJECT_LIMIT_REACHED",
        "REJECT_ATTESTATION_MISSING", "REJECT_AUTHORITY_NOT_CURRENT",
        "REJECT_INVALID_COMMAND"
    };

    internal static void Validate(IDictionary<string, object> root)
    {
        var admission = Object(root["admission"], "admission",
            "envelope_ref", "envelope_sha256", "owner_start_command_id",
            "authorized_start_count", "expires_at_utc", "owner_subject_binding",
            "owner_capture_consent_evaluation", "start_currentness_readback",
            "execution_authorization_ref", "execution_authorization_sha256",
            "admitted_effect_time_utc", "durable_exclusion_token_ref",
            "durable_exclusion_readback_sha256", "durable_exclusion_head_sha256");
        ValidateAdmission(admission);
        ValidateLimits(Object(root["limits"], "limits", "revision", "hard_cap_minutes",
            "arm_budget_ms", "no_input_budget_ms", "stop_settlement_budget_ms",
            "metadata_publication_budget_ms", "watchdog_max_interval_ms",
            "max_pending_commands", "max_settings_epochs", "max_windows", "max_events",
            "max_receipt_bytes"));
        var clocks = Object(root["clocks"], "clocks", "started_at_utc",
            "stop_requested_at_utc", "settled_at_utc", "monotonic_frequency", "start_tick",
            "stop_request_tick", "revoke_tick", "settled_tick");
        ValidateClocks(clocks, admission);
        var terminal = Object(root["terminal"], "terminal", "primary_reason",
            "secondary_reasons", "receiver_settled", "in_flight_count",
            "local_admission_revoked", "open_window_disposition", "producer_stop_ack_state");
        ValidateTerminal(terminal);
        var capture = Object(root["capture_binding"], "capture_binding", "controller_sha256",
            "plugin_sha256", "obs_image_sha256", "process_identity_ref", "source_chain_ref",
            "source_chain_sha256", "source_assurance", "format_ref", "sample_rate_hz",
            "channel_layout_ref", "channel_count", "format_assurance", "wire_version",
            "source_clock_mapping_state", "queue_freshness_state");
        int channelCount = ValidateCapture(capture);
        var transport = Object(root["transport"], "transport", "connection_attempts",
            "authenticated_packets", "committed_packets", "committed_frames",
            "incomplete_packets", "invalid_headers", "hmac_failures", "nonce_mismatches",
            "sequence_order_errors", "source_timestamp_regressions", "sequence_gap_events",
            "missing_packets_lower_bound", "discarded_after_revocation",
            "discarded_on_token_change", "first_sequence", "last_sequence",
            "first_source_timestamp", "last_source_timestamp", "upstream_callback_drop_state",
            "acoustic_dropout_state");
        long committedFrames = ValidateTransport(transport);
        foreach (var pair in new[] { new[] { "incomplete_packets", "INCOMPLETE_PACKET" },
            new[] { "hmac_failures", "HMAC_FAILURE" }, new[] { "nonce_mismatches", "NONCE_DRIFT" },
            new[] { "sequence_order_errors", "SEQUENCE_ORDER_ERROR" },
            new[] { "source_timestamp_regressions", "SOURCE_TIMESTAMP_REGRESSION" },
            new[] { "sequence_gap_events", "SEQUENCE_GAP" } }) {
            bool reasonObserved = (string)terminal["primary_reason"] == pair[1] ||
                ContainsList((IList)terminal["secondary_reasons"], pair[1]);
            Require((Count(transport, pair[0]) > 0) == reasonObserved,
                "TRANSPORT_FAULT_REASON_PROVENANCE");
        }
        var events = Array(root["events"], "events", 4, BaiReadinessLimits.MaxEvents);
        var eventIndex = ValidateEvents(events, clocks, terminal, admission, committedFrames);
        var epochs = ValidateEpochs(Array(root["settings_epochs"], "settings_epochs", 0,
            BaiReadinessLimits.MaxSettingsEpochs), capture, admission, clocks, eventIndex,
            committedFrames, terminal);
        ValidateWindows(Array(root["windows"], "windows", 0, BaiReadinessLimits.MaxWindows),
            epochs, eventIndex, terminal, clocks, transport, channelCount, committedFrames);
        ValidateFixedObjects(root);
    }

    private static void ValidateLimits(IDictionary value)
    {
        ConstantInteger(value, "revision", 1); ConstantInteger(value, "hard_cap_minutes", 3);
        ConstantInteger(value, "arm_budget_ms", 10000);
        ConstantInteger(value, "no_input_budget_ms", 5000);
        ConstantInteger(value, "stop_settlement_budget_ms", 2000);
        ConstantInteger(value, "metadata_publication_budget_ms", 2000);
        ConstantInteger(value, "watchdog_max_interval_ms", 100);
        ConstantInteger(value, "max_pending_commands", 16);
        ConstantInteger(value, "max_settings_epochs", 8);
        ConstantInteger(value, "max_windows", 16);
        ConstantInteger(value, "max_events", 64);
        ConstantInteger(value, "max_receipt_bytes", 262144);
    }

    private static void ValidateClocks(IDictionary clocks, IDictionary admission)
    {
        var started = Utc(clocks["started_at_utc"], "started_at_utc");
        Utc(clocks["stop_requested_at_utc"], "stop_requested_at_utc");
        Utc(clocks["settled_at_utc"], "settled_at_utc");
        Integer(clocks["monotonic_frequency"], 1, MaxExact, "monotonic_frequency");
        ConstantInteger(clocks, "start_tick", 0);
        long stop = Integer(clocks["stop_request_tick"], 0, MaxExact, "stop_request_tick");
        long revoke = Integer(clocks["revoke_tick"], 0, MaxExact, "revoke_tick");
        long settled = Integer(clocks["settled_tick"], 0, MaxExact, "settled_tick");
        Require(stop <= revoke && revoke <= settled, "CLOCK_ORDER");
        Require(started == Utc(admission["admitted_effect_time_utc"],
            "admitted_effect_time_utc"), "START_TIME_BINDING");
    }

    private static void ValidateTerminal(IDictionary terminal)
    {
        var primary = Enum(terminal["primary_reason"], StopReasons, "primary_reason");
        var secondary = Array(terminal["secondary_reasons"], "secondary_reasons", 0, 25);
        string previous = null;
        foreach (var item in secondary) {
            var reason = Enum(item, StopReasons, "secondary_reason");
            Require(!System.String.Equals(reason, primary, StringComparison.Ordinal),
                "SECONDARY_EQUALS_PRIMARY");
            Require(previous == null || StringComparer.Ordinal.Compare(previous, reason) < 0,
                "SECONDARY_NOT_SORTED_UNIQUE");
            previous = reason;
        }
        Constant(terminal, "receiver_settled", true);
        ConstantInteger(terminal, "in_flight_count", 0);
        Constant(terminal, "local_admission_revoked", true);
        Enum(terminal["open_window_disposition"],
            new[] { "NONE_OPEN_AT_REVOKE", "INTERRUPTED_AT_REVOKE" },
            "open_window_disposition");
        Constant(terminal, "producer_stop_ack_state", "UNAVAILABLE_LEGACY_WIRE");
    }

    private static int ValidateCapture(IDictionary capture)
    {
        Hash(capture["controller_sha256"], "controller_sha256");
        Hash(capture["plugin_sha256"], "plugin_sha256");
        Hash(capture["obs_image_sha256"], "obs_image_sha256");
        Id(capture["process_identity_ref"], "process_identity_ref");
        Id(capture["source_chain_ref"], "source_chain_ref");
        Hash(capture["source_chain_sha256"], "source_chain_sha256");
        Constant(capture, "source_assurance", "OWNER_ATTESTED_SINGLE_SOURCE_NOT_WIRE_PROVEN");
        Id(capture["format_ref"], "format_ref"); ConstantInteger(capture, "sample_rate_hz", 48000);
        Id(capture["channel_layout_ref"], "channel_layout_ref");
        int channels = checked((int)Integer(capture["channel_count"], 1, 8, "channel_count"));
        Constant(capture, "format_assurance", "EXTERNAL_SNAPSHOT_BOUND_NOT_WIRE_PROVEN");
        ConstantInteger(capture, "wire_version", 1);
        Constant(capture, "source_clock_mapping_state", "UNBOUND");
        Constant(capture, "queue_freshness_state", "NOT_PROVEN_WIRE_V1");
        return channels;
    }

    private static long ValidateTransport(IDictionary transport)
    {
        Integer(transport["connection_attempts"], 0, 1, "connection_attempts");
        long authenticated = Count(transport, "authenticated_packets");
        long committed = Count(transport, "committed_packets");
        long frames = Count(transport, "committed_frames");
        foreach (var key in new[] { "incomplete_packets", "invalid_headers", "hmac_failures",
            "nonce_mismatches", "sequence_order_errors", "source_timestamp_regressions",
            "discarded_after_revocation", "discarded_on_token_change" }) Count(transport, key);
        long gaps = Count(transport, "sequence_gap_events");
        long missing = Count(transport, "missing_packets_lower_bound");
        Require(committed <= authenticated, "COMMITTED_GT_AUTHENTICATED");
        Require(authenticated == 0 || Count(transport, "connection_attempts") == 1,
            "AUTHENTICATION_WITHOUT_CONNECTION");
        Require(frames >= committed && (decimal)frames <= (decimal)committed * 8192M,
            "COMMITTED_PACKET_FRAME_BOUNDS");
        Require((committed == 0) == (frames == 0), "COMMITTED_FRAME_ZERO_MATRIX");
        Require((gaps == 0) == (missing == 0), "GAP_MISSING_MATRIX");
        ValidateEndpointPair(transport["first_sequence"], transport["last_sequence"],
            committed, "sequence");
        ValidateEndpointPair(transport["first_source_timestamp"],
            transport["last_source_timestamp"], committed, "source_timestamp");
        Constant(transport, "upstream_callback_drop_state", "UNKNOWN_WIRE_V1");
        Constant(transport, "acoustic_dropout_state", "NOT_MEASURED");
        return frames;
    }

    private static void ValidateEndpointPair(object firstValue, object lastValue,
        long committedPackets, string name)
    {
        if (committedPackets == 0) {
            Require(firstValue == null && lastValue == null, name + "_EMPTY_ENDPOINTS");
            return;
        }
        ulong first = U64(firstValue, "first_" + name);
        ulong last = U64(lastValue, "last_" + name);
        Require(first <= last, name + "_ORDER");
    }

    private static void ValidateFixedObjects(IDictionary<string, object> root)
    {
        var algorithm = Object(root["measurement_algorithm"], "measurement_algorithm", "id",
            "revision", "sample_representation", "accumulation", "excursion_comparison",
            "channel_aggregation");
        Constant(algorithm, "id", "task047.received-float32-aggregate.v1");
        ConstantInteger(algorithm, "revision", 1);
        Constant(algorithm, "sample_representation", "PLANAR_LE_IEEE754_BINARY32");
        Constant(algorithm, "accumulation", "BINARY64_IN_RECEIVED_ORDER");
        Constant(algorithm, "excursion_comparison", "FINITE_ABS_GTE_0_9999");
        Constant(algorithm, "channel_aggregation", "SEPARATE_CHANNELS");

        var unknowns = Object(root["unknowns"], "unknowns",
            "source_callback_drop_count_state", "acoustic_dropout_count_state",
            "speech_occupancy_state", "noise_policy_state", "snr_evaluation_state",
            "true_peak_state", "adc_distortion_state", "source_wire_identity_state",
            "source_clock_mapping_state", "queue_freshness_state", "producer_stop_ack_state",
            "window_minimum_eligibility_state");
        Constant(unknowns, "source_callback_drop_count_state", "UNKNOWN_WIRE_V1");
        Constant(unknowns, "acoustic_dropout_count_state", "NOT_MEASURED");
        Constant(unknowns, "speech_occupancy_state", "NOT_MEASURED");
        Constant(unknowns, "noise_policy_state", "UNALLOCATED_TASK048");
        Constant(unknowns, "snr_evaluation_state", "NOT_EVALUATED");
        Constant(unknowns, "true_peak_state", "NOT_MEASURED");
        Constant(unknowns, "adc_distortion_state", "NOT_MEASURED");
        Constant(unknowns, "source_wire_identity_state", "UNAVAILABLE_WIRE_V1");
        Constant(unknowns, "source_clock_mapping_state", "UNBOUND");
        Constant(unknowns, "queue_freshness_state", "NOT_PROVEN_WIRE_V1");
        Constant(unknowns, "producer_stop_ack_state", "UNAVAILABLE_LEGACY_WIRE");
        Constant(unknowns, "window_minimum_eligibility_state", "UNALLOCATED_TASK048");

        var privacy = Object(root["privacy"], "privacy", "controller_audio_file_created",
            "recording_sink_capability_present", "receipt_contains_audio",
            "controller_transcript_created", "controller_external_audio_transfer",
            "controller_session_key_persisted", "metadata_only", "secure_ram_erasure_claimed",
            "whole_machine_audio_persistence_state", "whole_machine_audio_persistence_reason");
        foreach (var key in new[] { "controller_audio_file_created",
            "recording_sink_capability_present", "receipt_contains_audio",
            "controller_transcript_created", "controller_external_audio_transfer",
            "controller_session_key_persisted", "secure_ram_erasure_claimed" })
            Constant(privacy, key, false);
        Constant(privacy, "metadata_only", true);
        Constant(privacy, "whole_machine_audio_persistence_state", "NOT_CONFIRMED");
        Constant(privacy, "whole_machine_audio_persistence_reason",
            "EXTERNAL_HOST_OS_BEHAVIOR_OUT_OF_SCOPE");

        var authority = Object(root["authority"], "authority", "measurement_facts_only",
            "quality_decision_authority", "task048_consumer_allocated",
            "dataset_adoption_authority", "training_authority", "production_eligible");
        Constant(authority, "measurement_facts_only", true);
        foreach (var key in new[] { "quality_decision_authority", "task048_consumer_allocated",
            "dataset_adoption_authority", "training_authority", "production_eligible" })
            Constant(authority, key, false);
    }

    private static void ValidateAdmission(IDictionary admission)
    {
        Id(admission["envelope_ref"], "envelope_ref");
        Hash(admission["envelope_sha256"], "envelope_sha256");
        Id(admission["owner_start_command_id"], "owner_start_command_id");
        ConstantInteger(admission, "authorized_start_count", 1);
        DateTime expires = Utc(admission["expires_at_utc"], "expires_at_utc");
        Id(admission["execution_authorization_ref"], "execution_authorization_ref");
        Hash(admission["execution_authorization_sha256"], "execution_authorization_sha256");
        DateTime effect = Utc(admission["admitted_effect_time_utc"], "admitted_effect_time_utc");
        Require(effect < expires, "ADMISSION_EXPIRED_AT_EFFECT");
        Id(admission["durable_exclusion_token_ref"], "durable_exclusion_token_ref");
        Hash(admission["durable_exclusion_readback_sha256"],
            "durable_exclusion_readback_sha256");
        Hash(admission["durable_exclusion_head_sha256"], "durable_exclusion_head_sha256");

        var subject = Object(admission["owner_subject_binding"], "owner_subject_binding",
            "record_type", "schema_version", "canonical_owner_task", "receipt_role",
            "project_id", "subject_ref", "subject_revision", "subject_revision_sha256",
            "predecessor_subject_revision_sha256", "currentness_state",
            "currentness_readback_sha256", "created_at", "observed_at", "fresh_until",
            "trusted_time_binding_sha256", "binding_sha256");
        Constant(subject, "record_type", "OwnerVoiceSubjectBindingV1");
        ConstantInteger(subject, "schema_version", 1);
        Constant(subject, "canonical_owner_task", "TASK-046");
        Constant(subject, "receipt_role", "OWNER_VOICE_SUBJECT_BINDING");
        var project = ExternalString(subject["project_id"], "project_id");
        var subjectRef = ExternalUuid(subject["subject_ref"], "subject_ref");
        long subjectRevision = Integer(subject["subject_revision"], 1, MaxExact,
            "subject_revision");
        var subjectRevisionHash = ExternalHash(subject["subject_revision_sha256"],
            "subject_revision_sha256");
        var subjectPredecessor = subject["predecessor_subject_revision_sha256"] == null
            ? null : ExternalHash(subject["predecessor_subject_revision_sha256"],
                "predecessor_subject_revision_sha256");
        Require((subjectRevision == 1) == (subjectPredecessor == null),
            "SUBJECT_PREDECESSOR_REVISION_MATRIX");
        var subjectRevisionPreimage = new Dictionary<string, object>(StringComparer.Ordinal) {
            { "project_id", project }, { "subject_ref", subjectRef },
            { "subject_revision", subjectRevision },
            { "predecessor_subject_revision_sha256", subjectPredecessor }
        };
        Require(ExternalDomainDigest(subjectRevisionPreimage, null,
            "TASK046_OWNER_VOICE_SUBJECT_REVISION_V1") == subjectRevisionHash,
            "SUBJECT_REVISION_DIGEST_MISMATCH");
        Constant(subject, "currentness_state", "CURRENT");
        ExternalHash(subject["currentness_readback_sha256"], "currentness_readback_sha256");
        DateTime subjectCreated = Utc(subject["created_at"], "created_at");
        DateTime subjectObserved = Utc(subject["observed_at"], "observed_at");
        DateTime subjectFresh = Utc(subject["fresh_until"], "fresh_until");
        var trustedTime = ExternalHash(subject["trusted_time_binding_sha256"],
            "trusted_time_binding_sha256");
        var bindingHash = ExternalHash(subject["binding_sha256"], "binding_sha256");
        Require(ExternalDomainDigest(subject, "binding_sha256",
            "TASK046_OWNER_VOICE_SUBJECT_BINDING_V1") == bindingHash,
            "SUBJECT_BINDING_DIGEST_MISMATCH");
        Require(subjectCreated <= subjectObserved && subjectObserved <= effect && effect < subjectFresh,
            "SUBJECT_CURRENTNESS_TIME");

        var consent = Object(admission["owner_capture_consent_evaluation"],
            "owner_capture_consent_evaluation", "record_type", "schema_version",
            "canonical_owner_task", "receipt_role", "project_id", "subject_ref",
            "subject_revision", "subject_revision_sha256", "evaluation_revision", "purpose",
            "decision", "rights_scope", "policy_revision_sha256",
            "predecessor_evaluation_sha256", "issued_at", "observed_at", "expires_at",
            "revocation_currentness_sha256", "trusted_time_binding_sha256", "evaluation_sha256");
        Constant(consent, "record_type", "OwnerVoicePurposeConsentEvaluationV1");
        ConstantInteger(consent, "schema_version", 1);
        Constant(consent, "canonical_owner_task", "TASK-046");
        Constant(consent, "receipt_role", "OWNER_VOICE_PURPOSE_CONSENT_EVALUATION");
        Require(ExternalString(consent["project_id"], "project_id") == project &&
            ExternalUuid(consent["subject_ref"], "subject_ref") == subjectRef,
            "CONSENT_SUBJECT_MISMATCH");
        Require(Integer(consent["subject_revision"], 1, MaxExact, "subject_revision") ==
            subjectRevision, "CONSENT_REVISION_MISMATCH");
        Require(ExternalHash(consent["subject_revision_sha256"], "subject_revision_sha256") ==
            subjectRevisionHash, "CONSENT_REVISION_HASH_MISMATCH");
        long evaluationRevision = Integer(consent["evaluation_revision"], 1, MaxExact,
            "evaluation_revision");
        Constant(consent, "purpose", "OWNER_VOICE_CAPTURE");
        Constant(consent, "decision", "ALLOW");
        Constant(consent, "rights_scope", "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY");
        var policyHash = ExternalHash(consent["policy_revision_sha256"],
            "policy_revision_sha256");
        var evaluationPredecessor = consent["predecessor_evaluation_sha256"] == null
            ? null : ExternalHash(consent["predecessor_evaluation_sha256"],
                "predecessor_evaluation_sha256");
        Require((evaluationRevision == 1) == (evaluationPredecessor == null),
            "CONSENT_PREDECESSOR_REVISION_MATRIX");
        DateTime consentIssued = Utc(consent["issued_at"], "issued_at");
        DateTime consentObserved = Utc(consent["observed_at"], "observed_at");
        DateTime consentExpires = Utc(consent["expires_at"], "expires_at");
        ExternalHash(consent["revocation_currentness_sha256"],
            "revocation_currentness_sha256");
        Require(ExternalHash(consent["trusted_time_binding_sha256"],
            "trusted_time_binding_sha256") == trustedTime, "CONSENT_TRUSTED_TIME_MISMATCH");
        var evaluationHash = ExternalHash(consent["evaluation_sha256"], "evaluation_sha256");
        Require(ExternalDomainDigest(consent, "evaluation_sha256",
            "TASK046_OWNER_VOICE_PURPOSE_CONSENT_EVALUATION_V1") == evaluationHash,
            "CONSENT_EVALUATION_DIGEST_MISMATCH");
        Require(consentIssued <= consentObserved && consentObserved <= effect &&
            effect < consentExpires && expires <= consentExpires, "CONSENT_CURRENTNESS_TIME");

        var readback = Object(admission["start_currentness_readback"],
            "start_currentness_readback", "record_type", "schema_version",
            "canonical_owner_task", "receipt_role", "project_id", "subject_ref", "query_ref",
            "subject_binding_sha256", "consent_evaluation_sha256", "head_sha256",
            "head_event_sequence", "head_event_sha256", "subject_revision_sha256",
            "policy_revision_sha256", "purpose", "rights_scope", "consent_decision",
            "currentness_state", "reason_codes", "observed_at", "fresh_until",
            "trusted_time_binding_sha256", "readback_sha256");
        Constant(readback, "record_type", "OwnerVoiceCurrentnessReadbackV1");
        ConstantInteger(readback, "schema_version", 1);
        Constant(readback, "canonical_owner_task", "TASK-046");
        Constant(readback, "receipt_role", "OWNER_VOICE_CURRENTNESS_READBACK");
        Require(ExternalString(readback["project_id"], "project_id") == project &&
            ExternalUuid(readback["subject_ref"], "subject_ref") == subjectRef,
            "READBACK_SUBJECT_MISMATCH");
        ExternalUuid(readback["query_ref"], "query_ref");
        Require(ExternalHash(readback["subject_binding_sha256"],
            "subject_binding_sha256") == bindingHash, "READBACK_BINDING_MISMATCH");
        Require(ExternalHash(readback["consent_evaluation_sha256"],
            "consent_evaluation_sha256") == evaluationHash, "READBACK_CONSENT_MISMATCH");
        ExternalHash(readback["head_sha256"], "head_sha256");
        Integer(readback["head_event_sequence"], 1, MaxExact, "head_event_sequence");
        ExternalHash(readback["head_event_sha256"], "head_event_sha256");
        Require(ExternalHash(readback["subject_revision_sha256"],
            "subject_revision_sha256") == subjectRevisionHash, "READBACK_REVISION_MISMATCH");
        Require(ExternalHash(readback["policy_revision_sha256"],
            "policy_revision_sha256") == policyHash, "READBACK_POLICY_MISMATCH");
        Constant(readback, "purpose", "OWNER_VOICE_CAPTURE");
        Constant(readback, "rights_scope", "LOCAL_CAPTURE_AND_BOUND_PRIVATE_CUSTODY_ONLY");
        Constant(readback, "consent_decision", "ALLOW");
        Constant(readback, "currentness_state", "CURRENT");
        var readbackReasons = Array(readback["reason_codes"], "reason_codes", 1, 1);
        Require((readbackReasons[0] as string) == "CURRENT_MATCH",
            "CURRENT_READBACK_REASON_MATRIX");
        DateTime readbackObserved = Utc(readback["observed_at"], "observed_at");
        DateTime readbackFresh = Utc(readback["fresh_until"], "fresh_until");
        Require(readbackObserved <= effect && effect < readbackFresh && expires <= readbackFresh,
            "READBACK_CURRENTNESS_TIME");
        Require(readbackFresh <= subjectFresh && readbackFresh <= consentExpires,
            "READBACK_CONTROLLING_EXPIRY_BOUND");
        Require(ExternalHash(readback["trusted_time_binding_sha256"],
            "trusted_time_binding_sha256") == trustedTime, "READBACK_TRUSTED_TIME_MISMATCH");
        var readbackHash = ExternalHash(readback["readback_sha256"], "readback_sha256");
        Require(ExternalDomainDigest(readback, "readback_sha256",
            "TASK046_OWNER_VOICE_CURRENTNESS_READBACK_V1") == readbackHash,
            "CURRENTNESS_READBACK_DIGEST_MISMATCH");
        Require(expires <= subjectFresh, "SUBJECT_EXPIRES_BEFORE_ENVELOPE");
    }

    private sealed class EventView
    {
        internal int Index;
        internal string Id;
        internal string CommandId;
        internal long Tick;
        internal long Frame;
        internal string EpochId;
        internal string WindowId;
        internal string Code;
        internal string Reason;
    }

    private static Dictionary<string, EventView> ValidateEvents(IList events, IDictionary clocks,
        IDictionary terminal, IDictionary admission, long committedFrames)
    {
        var result = new Dictionary<string, EventView>(StringComparer.Ordinal);
        var commands = new HashSet<string>(StringComparer.Ordinal);
        long previousTick = -1, previousFrame = -1;
        for (int index = 0; index < events.Count; index++) {
            var item = Object(events[index], "event", "event_id", "command_id", "tick", "frame",
                "epoch_id", "window_id", "code", "reason_code");
            var view = new EventView {
                Index = index,
                Id = Id(item["event_id"], "event_id"),
                CommandId = NullableId(item["command_id"], "command_id"),
                Tick = Integer(item["tick"], 0, MaxExact, "event.tick"),
                Frame = Integer(item["frame"], 0, committedFrames, "event.frame"),
                EpochId = NullableId(item["epoch_id"], "epoch_id"),
                WindowId = NullableId(item["window_id"], "window_id"),
                Code = Enum(item["code"], EventCodes, "event.code"),
                Reason = NullableString(item["reason_code"], "reason_code")
            };
            Require(!result.ContainsKey(view.Id), "EVENT_ID_DUPLICATE");
            result.Add(view.Id, view);
            if (view.CommandId != null) Require(commands.Add(view.CommandId), "COMMAND_ID_DUPLICATE");
            Require(view.Tick >= previousTick && view.Frame >= previousFrame,
                "EVENT_COORDINATE_ORDER");
            Require(view.Tick <= Integer(clocks["settled_tick"], 0, MaxExact, "settled_tick"),
                "EVENT_AFTER_SETTLEMENT");
            previousTick = view.Tick; previousFrame = view.Frame;
            ValidateEventMatrix(view);
        }

        var first = EventAt(events, result, 0);
        Require(first.Code == "OWNER_START" && first.Tick == 0 && first.Frame == 0 &&
            first.CommandId == (string)admission["owner_start_command_id"], "OWNER_START_EVENT");
        var stop = EventAt(events, result, events.Count - 3);
        var revoke = EventAt(events, result, events.Count - 2);
        var settled = EventAt(events, result, events.Count - 1);
        Require(stop.Code == "STOP_REQUESTED" && revoke.Code == "REVOCATION_LINEARIZED" &&
            settled.Code == "RECEIVER_SETTLED", "STOP_TRACE_POSITION");
        Require(stop.Reason == (string)terminal["primary_reason"], "STOP_REASON_MISMATCH");
        Require(stop.Tick == Integer(clocks["stop_request_tick"], 0, MaxExact, "stop_request_tick") &&
            revoke.Tick == Integer(clocks["revoke_tick"], 0, MaxExact, "revoke_tick") &&
            settled.Tick == Integer(clocks["settled_tick"], 0, MaxExact, "settled_tick"),
            "STOP_TRACE_TICK_MISMATCH");
        Require(stop.Frame == committedFrames && revoke.Frame == committedFrames && settled.Frame == committedFrames,
            "STOP_TRACE_FRAME_MISMATCH");
        Require(CountCode(result, "OWNER_START") == 1 && CountCode(result, "STOP_REQUESTED") == 1 &&
            CountCode(result, "REVOCATION_LINEARIZED") == 1 &&
            CountCode(result, "RECEIVER_SETTLED") == 1, "MANDATORY_EVENT_COUNT");
        return result;
    }

    private static EventView EventAt(IList events, Dictionary<string, EventView> index, int offset)
    {
        var raw = events[offset] as IDictionary;
        Require(raw != null, "EVENT_OBJECT");
        return index[(string)raw["event_id"]];
    }

    private static int CountCode(Dictionary<string, EventView> events, string code)
    {
        int count = 0;
        foreach (var item in events.Values) if (item.Code == code) count++;
        return count;
    }

    private static void ValidateEventMatrix(EventView item)
    {
        switch (item.Code) {
            case "OWNER_START":
                Require(item.CommandId != null && item.EpochId == null && item.WindowId == null &&
                    item.Reason == null, "OWNER_START_EVENT_MATRIX");
                return;
            case "SETTINGS_FROZEN":
                Require(item.CommandId != null && item.EpochId != null && item.WindowId == null &&
                    item.Reason == null, "SETTINGS_FROZEN_EVENT_MATRIX");
                return;
            case "ROOM_TONE_STARTED": case "ROOM_TONE_ENDED":
            case "NORMAL_SPEECH_STARTED": case "NORMAL_SPEECH_ENDED":
            case "WINDOW_WITHDRAWN":
                Require(item.CommandId != null && item.EpochId != null && item.WindowId != null &&
                    item.Reason == null, "WINDOW_EVENT_MATRIX");
                return;
            case "SETTINGS_CHANGED":
                Require(item.CommandId != null && item.EpochId != null && item.Reason == null,
                    "SETTINGS_CHANGED_EVENT_MATRIX");
                return;
            case "OWNER_DISTORTION_REPORT": case "OWNER_RED_REPORT":
                Require(item.CommandId != null && item.Reason == null &&
                    (item.WindowId == null || item.EpochId != null), "OWNER_REPORT_EVENT_MATRIX");
                return;
            case "CURRENTNESS_INVALIDATED":
                Require(item.CommandId == null && item.Reason != null &&
                    IsCurrentnessStopReason(item.Reason), "CURRENTNESS_EVENT_MATRIX");
                return;
            case "STOP_REQUESTED":
                Require(item.EpochId == null && item.WindowId == null && item.Reason != null &&
                    Contains(StopReasons, item.Reason), "STOP_EVENT_MATRIX");
                Require(item.Reason == "OWNER_STOP" ? item.CommandId != null : item.CommandId == null,
                    "STOP_COMMAND_MATRIX");
                return;
            case "REVOCATION_LINEARIZED": case "RECEIVER_SETTLED":
                Require(item.CommandId == null && item.EpochId == null && item.WindowId == null &&
                    item.Reason == null, "SETTLEMENT_EVENT_MATRIX");
                return;
            case "COMMAND_REJECTED":
                Require(item.EpochId == null && item.WindowId == null && item.Reason != null &&
                    Contains(Rejections, item.Reason), "REJECTION_EVENT_MATRIX");
                return;
            default: throw new InvalidDataException("EVENT_CODE");
        }
    }

    private static bool IsCurrentnessStopReason(string reason)
    {
        return Contains(new[] { "OBS_IDENTITY_DRIFT", "SOURCE_BINDING_DRIFT", "FORMAT_DRIFT",
            "OWNER_REVOCATION", "AUTHORIZATION_EXPIRED", "AUTHORIZATION_CURRENTNESS_UNKNOWN",
            "ENVIRONMENT_ATTESTATION_REVOKED", "PIPE_CLOSED", "PIPE_FAILURE", "INVALID_HEADER",
            "INCOMPLETE_PACKET", "HMAC_FAILURE", "NONCE_DRIFT", "SEQUENCE_GAP",
            "SEQUENCE_ORDER_ERROR", "SOURCE_TIMESTAMP_REGRESSION" }, reason);
    }

    private static Dictionary<string, IDictionary> ValidateEpochs(IList epochs, IDictionary capture,
        IDictionary admission, IDictionary clocks, Dictionary<string, EventView> events,
        long committedFrames, IDictionary terminal)
    {
        var result = new Dictionary<string, IDictionary>(StringComparer.Ordinal);
        string expectedCaptureHash = ComputeCaptureBindingHash(capture);
        string subjectBindingHash = (string)((IDictionary)admission["owner_subject_binding"])["binding_sha256"];
        long revokeTick = Integer(clocks["revoke_tick"], 0, MaxExact, "revoke_tick");
        bool globalRevocation = HasCurrentnessStopReason(terminal);
        int previousFreezeIndex = -1;
        IList<string> previousInvalidations = null;
        foreach (var raw in epochs) {
            var epoch = Object(raw, "settings_epoch", "epoch_id", "freeze_command_id",
                "freeze_frame", "freeze_tick", "capture_binding_sha256", "settings_ref",
                "settings_sha256", "settings_assurance", "owner_ac_attestation",
                "owner_fan_attestation", "owner_fixed_settings_attestation",
                "invalidation_event_ids");
            string id = Id(epoch["epoch_id"], "epoch_id");
            Require(!result.ContainsKey(id), "EPOCH_ID_DUPLICATE");
            result.Add(id, epoch);
            string command = Id(epoch["freeze_command_id"], "freeze_command_id");
            long frame = Integer(epoch["freeze_frame"], 0, committedFrames, "freeze_frame");
            long tick = Integer(epoch["freeze_tick"], 0, revokeTick, "freeze_tick");
            Require(Hash(epoch["capture_binding_sha256"], "capture_binding_sha256") ==
                expectedCaptureHash, "CAPTURE_BINDING_HASH_MISMATCH");
            Id(epoch["settings_ref"], "settings_ref"); Hash(epoch["settings_sha256"], "settings_sha256");
            Constant(epoch, "settings_assurance", "OWNER_ATTESTED_WITH_AVAILABLE_SOFTWARE_FACTS");
            var expectedInvalidations = ExpectedInvalidations(events, id, null, globalRevocation);
            ValidateAttestation(epoch["owner_ac_attestation"], false, id, command, tick,
                subjectBindingHash, events, expectedInvalidations);
            ValidateAttestation(epoch["owner_fan_attestation"], false, id, command, tick,
                subjectBindingHash, events, expectedInvalidations);
            ValidateAttestation(epoch["owner_fixed_settings_attestation"], true, id, command, tick,
                subjectBindingHash, events, expectedInvalidations);
            ValidateExactEventReferences(Array(epoch["invalidation_event_ids"],
                "epoch.invalidation_event_ids", 0, BaiReadinessLimits.MaxEvents),
                expectedInvalidations, events, id, null);
            EventView freezeEvent = FindCommandEvent(events, command, "SETTINGS_FROZEN");
            Require(freezeEvent.EpochId == id && freezeEvent.Frame == frame && freezeEvent.Tick == tick,
                "FREEZE_EVENT_MISMATCH");
            Require(freezeEvent.Index > previousFreezeIndex, "EPOCH_CREATION_ORDER");
            if (previousInvalidations != null)
                Require(previousInvalidations.Count > 0 &&
                    events[previousInvalidations[0]].Index < freezeEvent.Index,
                    "EPOCH_OVERLAP_WITHOUT_INVALIDATION");
            foreach (var eventId in expectedInvalidations)
                Require(events[eventId].Index > freezeEvent.Index, "INVALIDATION_BEFORE_FREEZE");
            previousFreezeIndex = freezeEvent.Index;
            previousInvalidations = expectedInvalidations;
        }
        Require(CountCode(events, "SETTINGS_FROZEN") == epochs.Count, "ORPHAN_FREEZE_EVENT");
        return result;
    }

    private static void ValidateAttestation(object raw, bool fixedSettings, string epochId,
        string freezeCommand, long freezeTick, string subjectBindingHash,
        Dictionary<string, EventView> events, IList<string> expectedInvalidations)
    {
        var value = Object(raw, "attestation", "state", "attestation_ref",
            "owner_subject_binding_sha256", "command_id", "observed_tick", "currentness_state",
            "invalidation_event_ids", "epoch_id");
        string state = String(value["state"], "attestation.state");
        string currentness = String(value["currentness_state"], "attestation.currentness_state");
        Require(Id(value["epoch_id"], "attestation.epoch_id") == epochId,
            "ATTESTATION_EPOCH_MISMATCH");
        var invalidations = Array(value["invalidation_event_ids"],
            "attestation.invalidation_event_ids", 0, BaiReadinessLimits.MaxEvents);
        if (!fixedSettings && state == "NOT_ATTESTED") {
            Require(value["attestation_ref"] == null &&
                value["owner_subject_binding_sha256"] == null && value["command_id"] == null &&
                value["observed_tick"] == null && currentness == "NOT_ATTESTED" &&
                invalidations.Count == 0, "NOT_ATTESTED_MATRIX");
            return;
        }
        if (fixedSettings) Require(state == "ATTESTED_FIXED", "FIXED_ATTESTATION_STATE");
        else Require(state == "ATTESTED_OFF" || state == "ATTESTED_NOT_OFF",
            "ENVIRONMENT_ATTESTATION_STATE");
        Id(value["attestation_ref"], "attestation_ref");
        Require(ExternalHash(value["owner_subject_binding_sha256"],
            "owner_subject_binding_sha256") == subjectBindingHash,
            "ATTESTATION_SUBJECT_BINDING_MISMATCH");
        Require(Id(value["command_id"], "attestation.command_id") == freezeCommand,
            "ATTESTATION_COMMAND_MISMATCH");
        Require(Integer(value["observed_tick"], 0, MaxExact, "attestation.observed_tick") ==
            freezeTick, "ATTESTATION_TICK_MISMATCH");
        Require(currentness == "CURRENT" || currentness == "REVOKED",
            "ATTESTATION_CURRENTNESS");
        Require((currentness == "CURRENT") == (expectedInvalidations.Count == 0),
            "ATTESTATION_INVALIDATION_MATRIX");
        ValidateExactEventReferences(invalidations, expectedInvalidations, events, epochId, null);
    }

    private static EventView FindCommandEvent(Dictionary<string, EventView> events,
        string commandId, string code)
    {
        EventView found = null;
        foreach (var item in events.Values) {
            if (item.CommandId == commandId && item.Code == code) {
                Require(found == null, "COMMAND_EVENT_DUPLICATE");
                found = item;
            }
        }
        Require(found != null, "COMMAND_EVENT_MISSING");
        return found;
    }

    internal static string ComputeCaptureBindingHash(IDictionary capture)
    {
        var json = new StringBuilder();
        BaiReadinessCanonicalJson.WriteValue(json, capture);
        var domain = Encoding.ASCII.GetBytes("BVP_TASK047_READINESS_CAPTURE_BINDING_V1");
        var body = new UTF8Encoding(false, true).GetBytes(json.ToString());
        var bytes = new byte[domain.Length + 1 + body.Length];
        Buffer.BlockCopy(domain, 0, bytes, 0, domain.Length);
        Buffer.BlockCopy(body, 0, bytes, domain.Length + 1, body.Length);
        try {
            using (var sha = SHA256.Create())
                return BaiReadinessMetadataSinkCapability.Hex(sha.ComputeHash(bytes));
        } finally {
            System.Array.Clear(bytes, 0, bytes.Length);
        }
    }

    private static void ValidateWindows(IList windows, Dictionary<string, IDictionary> epochs,
        Dictionary<string, EventView> events, IDictionary terminal, IDictionary clocks,
        IDictionary transport, int channelCount, long committedFrames)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal);
        var purposeByEpoch = new HashSet<string>(StringComparer.Ordinal);
        var windowIndex = new Dictionary<string, IDictionary>(StringComparer.Ordinal);
        var roomWindows = new Dictionary<string, IDictionary>(StringComparer.Ordinal);
        long previousEndFrame = 0, previousEndTick = 0;
        int previousClosureIndex = -1;
        long totalWindowFrames = 0;
        int interruptedAtRevoke = 0;
        long revokeTick = Integer(clocks["revoke_tick"], 0, MaxExact, "revoke_tick");
        foreach (var raw in windows) {
            var window = Object(raw, "window", "window_id", "epoch_id", "purpose",
                "coordinate_domain", "start_frame", "end_frame", "start_command_id",
                "end_command_id", "start_event_id", "closure_event_id", "start_tick",
                "end_tick", "first_sequence", "last_sequence", "frame_count", "closure_state",
                "currentness_state", "observation_flags", "invalidation_event_ids",
                "channel_statistics");
            string id = Id(window["window_id"], "window_id");
            Require(ids.Add(id), "WINDOW_ID_DUPLICATE");
            windowIndex.Add(id, window);
            string epochId = Id(window["epoch_id"], "window.epoch_id");
            Require(epochs.ContainsKey(epochId), "WINDOW_EPOCH_MISSING");
            string purpose = Enum(window["purpose"], new[] { "ROOM_TONE", "NORMAL_SPEECH" },
                "window.purpose");
            Require(purposeByEpoch.Add(epochId + "\0" + purpose), "WINDOW_PURPOSE_DUPLICATE");
            Constant(window, "coordinate_domain", "ACCEPTED_AUTHENTICATED_FRAME_V1");
            long startFrame = Integer(window["start_frame"], 0, committedFrames, "start_frame");
            long endFrame = Integer(window["end_frame"], startFrame, committedFrames, "end_frame");
            long frameCount = Integer(window["frame_count"], 0, MaxExact, "frame_count");
            Require(frameCount == endFrame - startFrame, "WINDOW_FRAME_COUNT");
            totalWindowFrames = checked(totalWindowFrames + frameCount);
            string startCommand = Id(window["start_command_id"], "start_command_id");
            string endCommand = NullableId(window["end_command_id"], "end_command_id");
            string startEventId = Id(window["start_event_id"], "start_event_id");
            string closureEventId = Id(window["closure_event_id"], "closure_event_id");
            long startTick = Integer(window["start_tick"], 0, revokeTick, "start_tick");
            long endTick = Integer(window["end_tick"], startTick, revokeTick, "end_tick");
            var epoch = epochs[epochId];
            Require(Integer(epoch["freeze_frame"], 0, committedFrames, "freeze_frame") <= startFrame &&
                Integer(epoch["freeze_tick"], 0, revokeTick, "freeze_tick") <= startTick,
                "WINDOW_BEFORE_FREEZE");
            if (frameCount == 0) Require(window["first_sequence"] == null &&
                window["last_sequence"] == null, "EMPTY_WINDOW_SEQUENCE");
            else Require(U64(window["first_sequence"], "window.first_sequence") <=
                U64(window["last_sequence"], "window.last_sequence"), "WINDOW_SEQUENCE_ORDER");
            string closure = Enum(window["closure_state"], new[] { "CLOSED", "INTERRUPTED" },
                "closure_state");
            Require((closure == "CLOSED") == (endCommand != null), "WINDOW_END_COMMAND_MATRIX");
            string currentness = Enum(window["currentness_state"], new[] {
                "SAME_EPOCH_AT_CLOSE", "INVALIDATED_AFTER_CLOSE", "INVALIDATED_WHILE_OPEN",
                "WITHDRAWN" }, "window.currentness_state");
            var flags = Array(window["observation_flags"], "observation_flags", 1, 5);
            ValidateSortedUniqueEnum(flags, new[] { "RECEIVED_EXCURSION_PRESENT",
                "OWNER_DISTORTION_REPORTED", "OWNER_RED_INDICATOR_REPORTED",
                "SIGNAL_NOT_FINITE", "UPSTREAM_LOSS_UNKNOWN" }, "observation_flags");
            Require(ContainsList(flags, "UPSTREAM_LOSS_UNKNOWN"), "UPSTREAM_UNKNOWN_FLAG_MISSING");
            var invalidations = Array(window["invalidation_event_ids"],
                "window.invalidation_event_ids", 0, BaiReadinessLimits.MaxEvents);
            ValidateStatistics(Array(window["channel_statistics"], "channel_statistics",
                channelCount, channelCount), channelCount, frameCount, flags);

            Require(events.ContainsKey(startEventId) && events[startEventId].WindowId == id &&
                events[startEventId].EpochId == epochId && events[startEventId].CommandId == startCommand &&
                events[startEventId].Tick == startTick && events[startEventId].Frame == startFrame &&
                events[startEventId].Code == (purpose == "ROOM_TONE" ?
                    "ROOM_TONE_STARTED" : "NORMAL_SPEECH_STARTED"), "WINDOW_START_EVENT");
            Require(events.ContainsKey(closureEventId), "WINDOW_CLOSURE_EVENT_MISSING");
            var closeEvent = events[closureEventId];
            bool globalRevoke = closeEvent.Code == "REVOCATION_LINEARIZED";
            Require((globalRevoke ? closeEvent.WindowId == null && closeEvent.EpochId == null :
                closeEvent.WindowId == id && closeEvent.EpochId == epochId) &&
                closeEvent.Tick == endTick && closeEvent.Frame == endFrame, "WINDOW_CLOSURE_EVENT");
            var startEvent = events[startEventId];
            var freezeEvent = FindCommandEvent(events, (string)epoch["freeze_command_id"], "SETTINGS_FROZEN");
            Require(freezeEvent.Index < startEvent.Index && startEvent.Index < closeEvent.Index &&
                previousClosureIndex < startEvent.Index && previousEndFrame <= startFrame &&
                previousEndTick <= startTick, "WINDOW_DISJOINT_CREATION_ORDER");
            previousClosureIndex = closeEvent.Index;
            previousEndFrame = endFrame; previousEndTick = endTick;
            if (purpose == "ROOM_TONE") roomWindows.Add(epochId, window);
            else {
                Require(roomWindows.ContainsKey(epochId), "NORMAL_SPEECH_BEFORE_ROOM_TONE");
                var room = roomWindows[epochId];
                Require((string)room["closure_state"] == "CLOSED" &&
                    events[(string)room["closure_event_id"]].Index < startEvent.Index,
                    "NORMAL_SPEECH_REQUIRES_CLOSED_ROOM_TONE");
            }
            bool distortionReported = false, redReported = false;
            foreach (var report in events.Values) {
                if (report.WindowId != id) continue;
                distortionReported |= report.Code == "OWNER_DISTORTION_REPORT";
                redReported |= report.Code == "OWNER_RED_REPORT";
            }
            Require(ContainsList(flags, "OWNER_DISTORTION_REPORTED") == distortionReported &&
                ContainsList(flags, "OWNER_RED_INDICATOR_REPORTED") == redReported,
                "OWNER_REPORT_FLAG_EQUIVALENCE");
            if (closure == "CLOSED") Require(closeEvent.CommandId == endCommand &&
                closeEvent.Code == (purpose == "ROOM_TONE" ? "ROOM_TONE_ENDED" :
                    "NORMAL_SPEECH_ENDED"), "WINDOW_END_EVENT");
            else Require(closeEvent.Code == "SETTINGS_CHANGED" ||
                closeEvent.Code == "CURRENTNESS_INVALIDATED" ||
                closeEvent.Code == "WINDOW_WITHDRAWN" ||
                closeEvent.Code == "REVOCATION_LINEARIZED", "WINDOW_INTERRUPT_EVENT");
            bool globalRevocation = HasCurrentnessStopReason(terminal);
            var expectedInvalidations = ExpectedInvalidations(
                events, epochId, id, globalRevocation);
            ValidateExactEventReferences(invalidations, expectedInvalidations,
                events, epochId, id);
            bool withdrawn = false;
            int firstInvalidationIndex = Int32.MaxValue;
            foreach (var invalidationId in expectedInvalidations) {
                var invalidation = events[invalidationId];
                withdrawn |= invalidation.Code == "WINDOW_WITHDRAWN";
                firstInvalidationIndex = Math.Min(firstInvalidationIndex, invalidation.Index);
            }
            string expectedCurrentness;
            if (withdrawn) expectedCurrentness = "WITHDRAWN";
            else if (expectedInvalidations.Count == 0) expectedCurrentness = "SAME_EPOCH_AT_CLOSE";
            else expectedCurrentness = firstInvalidationIndex <= closeEvent.Index
                ? "INVALIDATED_WHILE_OPEN" : "INVALIDATED_AFTER_CLOSE";
            Require(currentness == expectedCurrentness, "WINDOW_CURRENTNESS_DERIVATION");
            if (expectedInvalidations.Count > 0 && firstInvalidationIndex <= closeEvent.Index)
                Require(closeEvent.Id == expectedInvalidations[0],
                    "WINDOW_INVALIDATION_CLOSURE");
            if (closure == "INTERRUPTED" && closeEvent.Code == "REVOCATION_LINEARIZED")
                interruptedAtRevoke++;
        }
        foreach (var item in events.Values) {
            if (item.EpochId != null) {
                Require(epochs.ContainsKey(item.EpochId), "EVENT_EPOCH_MISSING");
                var freeze = FindCommandEvent(events,
                    (string)epochs[item.EpochId]["freeze_command_id"], "SETTINGS_FROZEN");
                Require(item.Index >= freeze.Index, "EVENT_BEFORE_EPOCH");
            }
            if (item.WindowId != null) {
                Require(windowIndex.ContainsKey(item.WindowId), "EVENT_WINDOW_MISSING");
                var window = windowIndex[item.WindowId];
                Require(item.EpochId == (string)window["epoch_id"] &&
                    item.Index >= events[(string)window["start_event_id"]].Index,
                    "EVENT_WINDOW_PROVENANCE");
                if (item.Code == "ROOM_TONE_STARTED" || item.Code == "NORMAL_SPEECH_STARTED")
                    Require(item.Id == (string)window["start_event_id"], "ORPHAN_WINDOW_START");
                if (item.Code == "ROOM_TONE_ENDED" || item.Code == "NORMAL_SPEECH_ENDED")
                    Require(item.Id == (string)window["closure_event_id"], "ORPHAN_WINDOW_END");
            }
        }
        Require(totalWindowFrames <= committedFrames, "WINDOW_FRAME_SUM");
        string disposition = (string)terminal["open_window_disposition"];
        Require((disposition == "INTERRUPTED_AT_REVOKE" && interruptedAtRevoke == 1) ||
            (disposition == "NONE_OPEN_AT_REVOKE" && interruptedAtRevoke == 0),
            "OPEN_WINDOW_DISPOSITION");
        long committed = Count(transport, "committed_packets");
        if (committed == 0) Require(windows.Count == 0 || totalWindowFrames == 0,
            "WINDOWS_WITHOUT_PACKETS");
    }

    private static void ValidateStatistics(IList statistics, int channelCount, long windowFrames,
        IList flags)
    {
        bool anyExcursion = false, anyNonfinite = false;
        for (int index = 0; index < statistics.Count; index++) {
            var value = Object(statistics[index], "channel_statistics", "channel_index",
                "frame_count", "finite_count", "nan_count", "positive_inf_count",
                "negative_inf_count", "sum_finite", "sum_squares_finite",
                "signed_min_finite", "signed_max_finite", "max_abs_finite",
                "excursion_threshold_abs", "excursion_count", "derived_state", "mean_dc",
                "rms_linear", "peak_linear", "rms_dbfs", "peak_dbfs");
            Require(Integer(value["channel_index"], 0, MaxExact, "channel_index") == index,
                "CHANNEL_INDEX_ORDER");
            long frames = Count(value, "frame_count");
            Require(frames == windowFrames, "CHANNEL_FRAME_COUNT");
            long finite = Count(value, "finite_count");
            long nan = Count(value, "nan_count");
            long positive = Count(value, "positive_inf_count");
            long negative = Count(value, "negative_inf_count");
            Require(checked(finite + nan + positive + negative) == frames,
                "CHANNEL_COUNT_PARTITION");
            double sum = Number(value["sum_finite"], "sum_finite");
            double squares = Number(value["sum_squares_finite"], "sum_squares_finite");
            Require(squares >= 0.0, "SUM_SQUARES_NEGATIVE");
            double? minimum = NullableNumber(value["signed_min_finite"], "signed_min_finite");
            double? maximum = NullableNumber(value["signed_max_finite"], "signed_max_finite");
            double? maximumAbsolute = NullableNumber(value["max_abs_finite"], "max_abs_finite");
            if (maximumAbsolute.HasValue) Require(maximumAbsolute.Value >= 0.0,
                "MAX_ABS_NEGATIVE");
            Require(Math.Abs(Number(value["excursion_threshold_abs"],
                "excursion_threshold_abs") - 0.9999) <= 1e-15, "EXCURSION_THRESHOLD");
            long excursions = Count(value, "excursion_count");
            Require(excursions <= finite, "EXCURSION_GT_FINITE");
            anyExcursion |= excursions > 0;
            anyNonfinite |= nan + positive + negative > 0;
            string state = Enum(value["derived_state"], new[] { "COMPUTED_FINITE",
                "MEASURED_ZERO", "NO_INPUT", "NOT_COMPUTABLE_NONFINITE" }, "derived_state");
            double? mean = NullableNumber(value["mean_dc"], "mean_dc");
            double? rms = NullableNumber(value["rms_linear"], "rms_linear");
            double? peak = NullableNumber(value["peak_linear"], "peak_linear");
            double? rmsDb = NullableNumber(value["rms_dbfs"], "rms_dbfs");
            double? peakDb = NullableNumber(value["peak_dbfs"], "peak_dbfs");

            if (finite == 0) Require(sum == 0.0 && squares == 0.0 && !minimum.HasValue &&
                !maximum.HasValue && !maximumAbsolute.HasValue, "ZERO_FINITE_MATRIX");
            else {
                Require(minimum.HasValue && maximum.HasValue && maximumAbsolute.HasValue &&
                    minimum.Value <= maximum.Value && NearlyEqual(maximumAbsolute.Value,
                        Math.Max(Math.Abs(minimum.Value), Math.Abs(maximum.Value)), 1e-12),
                    "FINITE_EXTREMA");
            }
            if (frames == 0) {
                Require(state == "NO_INPUT" && finite == 0 && !mean.HasValue && !rms.HasValue &&
                    !peak.HasValue && !rmsDb.HasValue && !peakDb.HasValue, "NO_INPUT_MATRIX");
            } else if (nan + positive + negative > 0) {
                Require(state == "NOT_COMPUTABLE_NONFINITE" && !mean.HasValue && !rms.HasValue &&
                    !peak.HasValue && !rmsDb.HasValue && !peakDb.HasValue,
                    "NONFINITE_MATRIX");
            } else if (maximumAbsolute.Value == 0.0) {
                Require(state == "MEASURED_ZERO" && mean == 0.0 && rms == 0.0 && peak == 0.0 &&
                    !rmsDb.HasValue && !peakDb.HasValue, "MEASURED_ZERO_MATRIX");
            } else {
                double expectedMean = sum / finite;
                double expectedRms = Math.Sqrt(squares / finite);
                double expectedPeak = maximumAbsolute.Value;
                Require(state == "COMPUTED_FINITE" && mean.HasValue && rms.HasValue &&
                    peak.HasValue && rmsDb.HasValue && peakDb.HasValue &&
                    NearlyEqual(mean.Value, expectedMean, 1e-12) &&
                    NearlyEqual(rms.Value, expectedRms, 1e-12) &&
                    NearlyEqual(peak.Value, expectedPeak, 1e-12) &&
                    NearlyEqual(rmsDb.Value, 20.0 * Math.Log10(expectedRms), 1e-9) &&
                    NearlyEqual(peakDb.Value, 20.0 * Math.Log10(expectedPeak), 1e-9),
                    "COMPUTED_FINITE_MATRIX");
            }
        }
        Require(ContainsList(flags, "RECEIVED_EXCURSION_PRESENT") == anyExcursion,
            "EXCURSION_FLAG_MISMATCH");
        Require(ContainsList(flags, "SIGNAL_NOT_FINITE") == anyNonfinite,
            "NONFINITE_FLAG_MISMATCH");
        Require(statistics.Count == channelCount, "CHANNEL_COUNT_MISMATCH");
    }

    private static bool HasCurrentnessStopReason(IDictionary terminal)
    {
        if (IsCurrentnessStopReason((string)terminal["primary_reason"])) return true;
        foreach (string reason in (IList)terminal["secondary_reasons"])
            if (IsCurrentnessStopReason(reason)) return true;
        return false;
    }

    private static IList<string> ExpectedInvalidations(
        Dictionary<string, EventView> events, string epochId, string windowId,
        bool globalRevocation)
    {
        var ordered = new List<EventView>(events.Values);
        ordered.Sort(delegate(EventView left, EventView right) {
            return left.Index.CompareTo(right.Index);
        });
        var result = new List<string>();
        foreach (var item in ordered) {
            bool applies = (item.Code == "SETTINGS_CHANGED" ||
                    item.Code == "CURRENTNESS_INVALIDATED") && item.EpochId == epochId;
            if (windowId != null && item.Code == "WINDOW_WITHDRAWN" &&
                item.EpochId == epochId && item.WindowId == windowId) applies = true;
            if (item.Code == "REVOCATION_LINEARIZED" &&
                globalRevocation) applies = true;
            if (applies) result.Add(item.Id);
        }
        return result.AsReadOnly();
    }

    private static void ValidateExactEventReferences(IList references,
        IList<string> expected, Dictionary<string, EventView> events,
        string epochId, string windowId)
    {
        ValidateEventReferences(references, events, epochId, windowId);
        Require(references.Count == expected.Count, "INVALIDATION_SET_INCOMPLETE");
        for (int index = 0; index < expected.Count; index++)
            Require((references[index] as string) == expected[index],
                "INVALIDATION_SET_DERIVATION");
    }

    private static void ValidateEventReferences(IList references,
        Dictionary<string, EventView> events, string epochId, string windowId)
    {
        int previous = -1;
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var raw in references) {
            string id = Id(raw, "invalidation_event_id");
            Require(seen.Add(id) && events.ContainsKey(id), "INVALIDATION_EVENT_REFERENCE");
            var item = events[id];
            Require(item.Index > previous, "INVALIDATION_EVENT_ORDER");
            Require(item.Code == "SETTINGS_CHANGED" || item.Code == "CURRENTNESS_INVALIDATED" ||
                item.Code == "WINDOW_WITHDRAWN" || item.Code == "REVOCATION_LINEARIZED",
                "INVALIDATION_EVENT_CODE");
            Require(item.EpochId == null || item.EpochId == epochId,
                "INVALIDATION_EPOCH_MISMATCH");
            Require(item.Code != "WINDOW_WITHDRAWN" || windowId == null || item.WindowId == windowId,
                "INVALIDATION_WINDOW_MISMATCH");
            previous = item.Index;
        }
    }

    private static bool NearlyEqual(double left, double right, double tolerance)
    {
        return Math.Abs(left - right) <= Math.Max(tolerance,
            tolerance * Math.Max(Math.Abs(left), Math.Abs(right)));
    }

    private static IDictionary Object(object raw, string name, params string[] exactKeys)
    {
        var value = raw as IDictionary;
        if (value == null) throw new InvalidDataException(name + "_OBJECT");
        Require(value.Count == exactKeys.Length, name + "_FIELD_COUNT");
        var expected = new HashSet<string>(exactKeys, StringComparer.Ordinal);
        foreach (DictionaryEntry pair in value) {
            var key = pair.Key as string;
            Require(key != null && expected.Remove(key), name + "_FIELD_UNKNOWN_OR_DUPLICATE");
        }
        Require(expected.Count == 0, name + "_FIELD_MISSING");
        return value;
    }

    private static IList Array(object raw, string name, int minimum, int maximum)
    {
        var value = raw as IList;
        if (value == null) throw new InvalidDataException(name + "_ARRAY");
        Require(value.Count >= minimum && value.Count <= maximum, name + "_ARRAY_BOUND");
        return value;
    }

    private static long Count(IDictionary value, string key)
    {
        return Integer(value[key], 0, MaxExact, key);
    }

    private static long Integer(object raw, long minimum, long maximum, string name)
    {
        if (raw == null || raw is bool || raw is float || raw is double || raw is decimal)
            throw new InvalidDataException(name + "_INTEGER");
        decimal value;
        try { value = Convert.ToDecimal(raw, CultureInfo.InvariantCulture); }
        catch { throw new InvalidDataException(name + "_INTEGER"); }
        Require(decimal.Truncate(value) == value && value >= minimum && value <= maximum,
            name + "_INTEGER_BOUND");
        return decimal.ToInt64(value);
    }

    private static double Number(object raw, string name)
    {
        if (raw == null || raw is bool || raw is float || raw is decimal)
            throw new InvalidDataException(name + "_NUMBER");
        double value;
        try { value = Convert.ToDouble(raw, CultureInfo.InvariantCulture); }
        catch { throw new InvalidDataException(name + "_NUMBER"); }
        Require(!Double.IsNaN(value) && !Double.IsInfinity(value), name + "_FINITE");
        return value == 0.0 ? 0.0 : value;
    }

    private static double? NullableNumber(object raw, string name)
    {
        return raw == null ? (double?)null : Number(raw, name);
    }

    private static string String(object raw, string name)
    {
        var value = raw as string;
        if (value == null) throw new InvalidDataException(name + "_STRING");
        return value;
    }

    private static string NullableString(object raw, string name)
    {
        return raw == null ? null : String(raw, name);
    }

    private static string Id(object raw, string name)
    {
        var value = String(raw, name);
        try { return BaiReadinessAdmission.RequireId(value); }
        catch { throw new InvalidDataException(name + "_ID"); }
    }

    private static string NullableId(object raw, string name)
    {
        return raw == null ? null : Id(raw, name);
    }

    private static string Hash(object raw, string name)
    {
        string value = String(raw, name);
        Require(value.Length == 64 && IsLowerHex(value), name + "_HASH");
        return value;
    }

    private static string ExternalHash(object raw, string name)
    {
        string value = String(raw, name);
        Require(value.StartsWith("sha256:", StringComparison.Ordinal) && value.Length == 71 &&
            IsLowerHex(value.Substring(7)), name + "_EXTERNAL_HASH");
        return value;
    }

    private static void NullableExternalHash(object raw, string name)
    {
        if (raw != null) ExternalHash(raw, name);
    }

    private static bool IsLowerHex(string value)
    {
        foreach (char c in value) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            return false;
        return true;
    }

    private static string ExternalString(object raw, string name)
    {
        var value = String(raw, name);
        Require(value.Length > 0, name + "_EMPTY");
        return value;
    }

    private static string ExternalUuid(object raw, string name)
    {
        var value = ExternalString(raw, name);
        Guid parsed;
        Require(Guid.TryParseExact(value, "D", out parsed) &&
            System.String.Equals(parsed.ToString("D"), value, StringComparison.Ordinal),
            name + "_CANONICAL_UUID");
        return value;
    }

    private static string ExternalDomainDigest(IDictionary source, string excludedKey,
        string domain)
    {
        var preimage = new Dictionary<string, object>(StringComparer.Ordinal);
        foreach (DictionaryEntry pair in source) {
            var key = pair.Key as string;
            Require(key != null, "EXTERNAL_DIGEST_KEY");
            if (!System.String.Equals(key, excludedKey, StringComparison.Ordinal))
                preimage.Add(key, pair.Value);
        }
        var json = new StringBuilder();
        BaiReadinessCanonicalJson.WriteValue(json, preimage);
        var prefix = Encoding.ASCII.GetBytes(domain);
        var body = new UTF8Encoding(false, true).GetBytes(json.ToString());
        var bytes = new byte[prefix.Length + 1 + body.Length];
        Buffer.BlockCopy(prefix, 0, bytes, 0, prefix.Length);
        Buffer.BlockCopy(body, 0, bytes, prefix.Length + 1, body.Length);
        try {
            using (var sha = SHA256.Create())
                return "sha256:" + BaiReadinessMetadataSinkCapability.Hex(
                    sha.ComputeHash(bytes));
        } finally {
            System.Array.Clear(bytes, 0, bytes.Length);
        }
    }

    private static DateTime Utc(object raw, string name)
    {
        DateTime value;
        string text = String(raw, name);
        if (!DateTime.TryParseExact(text, "yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'",
            CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal |
            DateTimeStyles.AdjustToUniversal, out value))
            throw new InvalidDataException(name + "_UTC");
        return value;
    }

    private static ulong U64(object raw, string name)
    {
        string value = String(raw, name);
        Require(value == "0" || value.Length > 0 && value[0] >= '1' && value[0] <= '9',
            name + "_U64_CANONICAL");
        foreach (char c in value) Require(c >= '0' && c <= '9', name + "_U64_CANONICAL");
        ulong parsed;
        Require(UInt64.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out parsed),
            name + "_U64_BOUND");
        return parsed;
    }

    private static string Enum(object raw, string[] allowed, string name)
    {
        string value = String(raw, name);
        Require(Contains(allowed, value), name + "_ENUM");
        return value;
    }

    private static bool Contains(string[] values, string expected)
    {
        foreach (var value in values) if (System.String.Equals(value, expected, StringComparison.Ordinal))
            return true;
        return false;
    }

    private static bool ContainsList(IList values, string expected)
    {
        foreach (var value in values) if (System.Object.Equals(value, expected)) return true;
        return false;
    }

    private static void ValidateSortedUniqueEnum(IList values, string[] allowed, string name)
    {
        string previous = null;
        foreach (var raw in values) {
            string value = Enum(raw, allowed, name);
            Require(previous == null || StringComparer.Ordinal.Compare(previous, value) < 0,
                name + "_NOT_SORTED_UNIQUE");
            previous = value;
        }
    }

    private static void Constant(IDictionary value, string key, object expected)
    {
        Require(System.Object.Equals(value[key], expected), key + "_CONST");
    }

    private static void ConstantInteger(IDictionary value, string key, long expected)
    {
        Require(Integer(value[key], expected, expected, key) == expected, key + "_CONST");
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}

internal static class BaiReadinessCanonicalJson
{
    internal static void WriteValue(StringBuilder target, object value)
    {
        if (value == null) { target.Append("null"); return; }
        var text = value as string;
        if (text != null) { WriteString(target, text); return; }
        if (value is bool) { target.Append((bool)value ? "true" : "false"); return; }
        if (value is byte || value is short || value is int || value is long ||
            value is ushort || value is uint || value is ulong) {
            target.Append(Convert.ToString(value, CultureInfo.InvariantCulture)); return;
        }
        if (value is decimal) {
            target.Append(((decimal)value).ToString(CultureInfo.InvariantCulture)); return;
        }
        if (value is double) { WriteDouble(target, (double)value); return; }
        if (value is float) { WriteDouble(target, (float)value); return; }
        var dictionary = value as IDictionary;
        if (dictionary != null) {
            var keys = new List<string>();
            foreach (DictionaryEntry pair in dictionary) {
                var key = pair.Key as string;
                if (key == null) throw new InvalidDataException("NONSTRING_KEY");
                keys.Add(key);
            }
            keys.Sort(StringComparer.Ordinal);
            target.Append('{');
            for (int index = 0; index < keys.Count; index++) {
                if (index != 0) target.Append(',');
                WriteString(target, keys[index]);
                target.Append(':');
                WriteValue(target, dictionary[keys[index]]);
            }
            target.Append('}');
            return;
        }
        var sequence = value as IEnumerable;
        if (sequence != null) {
            target.Append('[');
            bool first = true;
            foreach (var item in sequence) {
                if (!first) target.Append(',');
                first = false;
                WriteValue(target, item);
            }
            target.Append(']');
            return;
        }
        throw new InvalidDataException("UNSUPPORTED_JSON_VALUE");
    }

    private static void WriteDouble(StringBuilder target, double value)
    {
        if (Double.IsNaN(value) || Double.IsInfinity(value))
            throw new InvalidDataException("NONFINITE_JSON_NUMBER");
        if (value == 0.0) { target.Append('0'); return; }
        target.Append(value.ToString("R", CultureInfo.InvariantCulture));
    }

    private static void WriteString(StringBuilder target, string value)
    {
        target.Append('"');
        foreach (char c in value) {
            switch (c) {
                case '"': target.Append("\\\""); break;
                case '\\': target.Append("\\\\"); break;
                case '\b': target.Append("\\b"); break;
                case '\f': target.Append("\\f"); break;
                case '\n': target.Append("\\n"); break;
                case '\r': target.Append("\\r"); break;
                case '\t': target.Append("\\t"); break;
                default:
                    if (c < 0x20) target.Append("\\u" + ((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else target.Append(c);
                    break;
            }
        }
        target.Append('"');
    }
}

internal sealed class BaiReadinessMetadataSinkCapability
{
    private const string Domain = "BVP_TASK047_READINESS_METADATA_FILENAME_V1";
    private readonly string parent;
    private readonly BaiReadinessPhysicalIdentity parentIdentity;
    private readonly bool pureTestUnknown;
    private readonly Task pureTestCompletion;
    private int publicationClaimed;
    private int effectStarted;
    internal bool EffectStarted { get { return Volatile.Read(ref effectStarted) != 0; } }

    private BaiReadinessMetadataSinkCapability(Task completion)
    {
        pureTestUnknown = true;
        pureTestCompletion = completion;
    }

    internal static BaiReadinessMetadataSinkCapability CreatePureTestUnknown(Task completion = null)
    {
        return new BaiReadinessMetadataSinkCapability(completion);
    }

    internal sealed class PublicationResult
    {
        private readonly BaiReadinessReceipt receipt;
        private readonly BaiReadinessMetadataSinkCapability sink;
        private readonly BaiReadinessTerminalProjection projection;

        private PublicationResult(BaiReadinessReceipt ownedReceipt,
            BaiReadinessMetadataSinkCapability ownedSink, BaiReadinessPublicationOutcome outcome,
            string reason, string path, int byteCount, string sha256,
            BaiReadinessPhysicalIdentity physicalIdentity,
            BaiReadinessTerminalProjection noArtifactProjection = null)
        {
            receipt = ownedReceipt; sink = ownedSink; Outcome = outcome; Reason = reason;
            projection = ownedReceipt == null ? noArtifactProjection : ownedReceipt.SourceProjection;
            Path = path; ByteCount = byteCount; Sha256 = sha256; PhysicalIdentity = physicalIdentity;
            if (ownedSink != null && ownedReceipt != null && !ownedSink.pureTestUnknown) {
                string token = TokenForOperation(ownedReceipt.OperationId);
                PendingPath = System.IO.Path.Combine(ownedSink.parent, "readiness-" + token + ".receipt.pending");
                FinalPath = System.IO.Path.Combine(ownedSink.parent, "readiness-" + token + ".receipt.json");
            }
            bool verified = outcome == BaiReadinessPublicationOutcome.Verified;
            if (verified && (reason != "NONE" || path == null || byteCount <= 0 ||
                sha256 == null || physicalIdentity == null))
                throw new InvalidOperationException("PUBLICATION_PROOF_INCOMPLETE");
            bool absent = outcome == BaiReadinessPublicationOutcome.NotPublishedConfirmed;
            if (absent && (projection == null || ownedReceipt != null || path != null ||
                byteCount != 0 || sha256 != null || physicalIdentity != null ||
                (ownedSink != null && ownedSink.EffectStarted) ||
                (reason != "INVALID_DTO_NO_ARTIFACT" && reason != "CREATE_FAILED_NO_ARTIFACT") ||
                (reason == "CREATE_FAILED_NO_ARTIFACT" && ownedSink != null)))
                throw new InvalidOperationException("NO_ARTIFACT_PROOF_INCOMPLETE");
            if (!verified && !absent && outcome != BaiReadinessPublicationOutcome.Unknown)
                throw new InvalidOperationException("UNPROVEN_PUBLICATION_OUTCOME");
        }

        internal BaiReadinessPublicationOutcome Outcome { get; private set; }
        internal string Reason { get; private set; }
        internal string Path { get; private set; }
        internal int ByteCount { get; private set; }
        internal string Sha256 { get; private set; }
        internal BaiReadinessPhysicalIdentity PhysicalIdentity { get; private set; }
        internal string PendingPath { get; private set; }
        internal string FinalPath { get; private set; }

        internal bool BelongsTo(BaiReadinessReceipt ownedReceipt,
            BaiReadinessMetadataSinkCapability ownedSink)
        {
            return Object.ReferenceEquals(receipt, ownedReceipt) && Object.ReferenceEquals(sink, ownedSink);
        }

        internal bool BelongsTo(BaiReadinessTerminalProjection ownedProjection,
            BaiReadinessMetadataSinkCapability ownedSink)
        {
            return ownedProjection != null && Object.ReferenceEquals(projection, ownedProjection) &&
                Object.ReferenceEquals(sink, ownedSink);
        }

        internal static Task<PublicationResult> StartPrepared(BaiReadinessMetadataSinkCapability sink,
            BaiReadinessTerminalProjection projection, IDictionary<string, object> staticContext)
        {
            if (projection == null) throw new ArgumentNullException("projection");
            // Reuse failures are outside the no-artifact catch. A prior attempt may own artifacts.
            if (sink != null && Interlocked.Exchange(ref sink.publicationClaimed, 1) != 0)
                throw new InvalidOperationException("SINK_PUBLICATION_ALREADY_CLAIMED");
            var consumption = projection.Consume();
            if (sink == null)
                return Task.FromResult(new PublicationResult(null, null,
                    BaiReadinessPublicationOutcome.NotPublishedConfirmed, "CREATE_FAILED_NO_ARTIFACT",
                    null, 0, null, null, consumption.Owner));
            BaiReadinessReceipt receipt;
            try { receipt = BaiReadinessReceipt.CreateFromConsumption(staticContext, consumption); }
            catch (ArgumentException) { return InvalidDto(sink, consumption); }
            catch (InvalidDataException) { return InvalidDto(sink, consumption); }
            catch (InvalidOperationException) { return InvalidDto(sink, consumption); }
            catch (KeyNotFoundException) { return InvalidDto(sink, consumption); }
            catch (InvalidCastException) { return InvalidDto(sink, consumption); }
            // No caller collection remains; only now may a sink task exist.
            return Task.Run(() => ExecuteOwned(sink, receipt));
        }

        private static Task<PublicationResult> InvalidDto(BaiReadinessMetadataSinkCapability sink,
            BaiReadinessTerminalProjection.Consumption consumption)
        {
            return Task.FromResult(new PublicationResult(null, sink,
                BaiReadinessPublicationOutcome.NotPublishedConfirmed, "INVALID_DTO_NO_ARTIFACT",
                null, 0, null, null, consumption.Owner));
        }

        internal static PublicationResult Execute(BaiReadinessMetadataSinkCapability sink,
            BaiReadinessReceipt receipt)
        {
            if (sink == null || receipt == null) throw new ArgumentNullException("publication");
            if (Interlocked.Exchange(ref sink.publicationClaimed, 1) != 0)
                throw new InvalidOperationException("SINK_PUBLICATION_ALREADY_CLAIMED");
            return ExecuteOwned(sink, receipt);
        }

        private static PublicationResult ExecuteOwned(BaiReadinessMetadataSinkCapability sink,
            BaiReadinessReceipt receipt)
        {
            var bytes = receipt.ClaimPublicationBytes();
            string digest;
            using (var sha = SHA256.Create()) digest = Hex(sha.ComputeHash(bytes));
            string reason = "IO_OUTCOME_UNKNOWN";
            BaiReadinessPhysicalIdentity identity = null;
            try {
                Interlocked.Exchange(ref sink.effectStarted, 1);
                if (sink.pureTestUnknown) {
                    if (sink.pureTestCompletion != null) sink.pureTestCompletion.GetAwaiter().GetResult();
                    return new PublicationResult(receipt, sink, BaiReadinessPublicationOutcome.Unknown,
                        reason, null, bytes.Length, digest, null);
                }
                string path = sink.PublishOwned(receipt, bytes, out identity, ref reason);
                reason = "IO_OUTCOME_UNKNOWN";
                return new PublicationResult(receipt, sink, BaiReadinessPublicationOutcome.Verified,
                    "NONE", path, bytes.Length, digest, identity);
            } catch {
                // No absence proof is inferred from an exception; retained partial
                // artifacts and ownership stay UNKNOWN, never success or safe retry.
                return new PublicationResult(receipt, sink, BaiReadinessPublicationOutcome.Unknown,
                    reason, null, bytes.Length, digest, identity);
            }
        }
    }

    internal BaiReadinessMetadataSinkCapability(string exactParent)
    {
        if (String.IsNullOrWhiteSpace(exactParent) || !Path.IsPathRooted(exactParent) ||
            exactParent.StartsWith("\\\\", StringComparison.Ordinal))
            throw new ArgumentException("Absolute metadata parent required");
        parent = Path.GetFullPath(exactParent).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var drive = Path.GetPathRoot(parent).TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var parentDirectoryValue = Path.GetDirectoryName(parent);
        if (String.IsNullOrEmpty(parentDirectoryValue))
            throw new InvalidDataException("DRIVE_ROOT_PLACEMENT_DENIED");
        var parentDirectory = parentDirectoryValue.TrimEnd(
            Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        if (String.Equals(parent, drive, StringComparison.OrdinalIgnoreCase) ||
            String.Equals(parentDirectory, drive, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("DRIVE_ROOT_PLACEMENT_DENIED");
        if (!Directory.Exists(parent)) throw new DirectoryNotFoundException();
        AssertNoReparseAncestors(parent);
        parentIdentity = BaiReadinessPhysicalIdentity.ForDirectory(parent);
    }

    internal string Parent { get { return parent; } }

    internal static string TokenForOperation(string operationId)
    {
        BaiReadinessAdmission.RequireId(operationId);
        var domain = Encoding.ASCII.GetBytes(Domain);
        var identity = Encoding.ASCII.GetBytes(operationId);
        var bytes = new byte[domain.Length + 1 + identity.Length];
        Buffer.BlockCopy(domain, 0, bytes, 0, domain.Length);
        Buffer.BlockCopy(identity, 0, bytes, domain.Length + 1, identity.Length);
        try {
            using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(bytes));
        } finally {
            Array.Clear(bytes, 0, bytes.Length);
        }
    }

    internal PublicationResult Publish(BaiReadinessReceipt receipt)
    {
        return PublicationResult.Execute(this, receipt);
    }

    private string PublishOwned(BaiReadinessReceipt receipt, byte[] bytes,
        out BaiReadinessPhysicalIdentity publishedIdentity, ref string reason)
    {
        if (receipt == null) throw new ArgumentNullException("receipt");
        publishedIdentity = null;
        reason = "IDENTITY_MISMATCH";
        AssertStableParent();
        reason = "VALIDATION_FAILED";
        BaiReadinessReceipt.LoadAndVerifyEmbeddedSchema();
        var token = TokenForOperation(receipt.OperationId);
        var pending = Path.Combine(parent, "readiness-" + token + ".receipt.pending");
        var final = Path.Combine(parent, "readiness-" + token + ".receipt.json");
        reason = "TARGET_COLLISION";
        if (File.Exists(pending) || File.Exists(final))
            throw new IOException("READINESS_METADATA_TARGET_COLLISION");
        BaiReadinessPhysicalIdentity pendingIdentity;
        reason = "PENDING_WRITE_INCOMPLETE";
        using (var output = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.Read,
            4096, FileOptions.WriteThrough)) {
            AssertStableParent();
            output.Write(bytes, 0, bytes.Length);
            output.Flush(true);
            pendingIdentity = BaiReadinessPhysicalIdentity.ForFileHandle(output.SafeFileHandle);
            if (pendingIdentity.LinkCount != 1)
                throw new IOException("READINESS_METADATA_LINK_COUNT");
        }
        publishedIdentity = pendingIdentity;
        reason = "IDENTITY_MISMATCH";
        AssertStableParent();
        RequireRegularOwnedFile(pending, pendingIdentity);
        reason = "READBACK_FAILED";
        var readback = File.ReadAllBytes(pending);
        if (!FixedEquals(bytes, readback)) throw new IOException("READINESS_METADATA_READBACK_FAILED");
        AssertStableParent();
        reason = "TARGET_COLLISION";
        if (File.Exists(final)) throw new IOException("READINESS_METADATA_TARGET_COLLISION");
        reason = "IO_OUTCOME_UNKNOWN";
        File.Move(pending, final);
        reason = "IDENTITY_MISMATCH";
        AssertStableParent();
        RequireRegularOwnedFile(final, pendingIdentity);
        reason = "READBACK_FAILED";
        var finalBytes = File.ReadAllBytes(final);
        if (!FixedEquals(bytes, finalBytes)) throw new IOException("READINESS_METADATA_FINAL_READBACK_FAILED");
        RequireRegularOwnedFile(final, pendingIdentity);
        reason = "NONE";
        return final;
    }

    private void AssertStableParent()
    {
        AssertNoReparseAncestors(parent);
        if (!parentIdentity.Equals(BaiReadinessPhysicalIdentity.ForDirectory(parent)))
            throw new IOException("READINESS_METADATA_PARENT_IDENTITY_CHANGED");
    }

    private static void RequireRegularOwnedFile(string path, BaiReadinessPhysicalIdentity expected)
    {
        var info = new FileInfo(path);
        if (!info.Exists || (info.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new IOException("READINESS_METADATA_TARGET_NOT_REGULAR");
        var actual = BaiReadinessPhysicalIdentity.ForFile(path);
        if (!expected.Equals(actual) || actual.LinkCount != 1)
            throw new IOException("READINESS_METADATA_TARGET_IDENTITY_CHANGED");
    }

    private static void AssertNoReparseAncestors(string path)
    {
        for (var cursor = new DirectoryInfo(path); cursor != null; cursor = cursor.Parent) {
            if (!cursor.Exists || (cursor.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("REPARSE_PARENT_DENIED");
        }
    }

    internal static string Hex(byte[] bytes)
    {
        var builder = new StringBuilder(bytes.Length * 2);
        foreach (var value in bytes) builder.Append(value.ToString("x2", CultureInfo.InvariantCulture));
        return builder.ToString();
    }

    private static bool FixedEquals(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        int different = 0;
        for (int index = 0; index < left.Length; index++) different |= left[index] ^ right[index];
        return different == 0;
    }
}

[StructLayout(LayoutKind.Sequential)]
internal struct BaiReadinessByHandleFileInformation
{
    internal uint FileAttributes;
    internal System.Runtime.InteropServices.ComTypes.FILETIME CreationTime;
    internal System.Runtime.InteropServices.ComTypes.FILETIME LastAccessTime;
    internal System.Runtime.InteropServices.ComTypes.FILETIME LastWriteTime;
    internal uint VolumeSerialNumber;
    internal uint FileSizeHigh;
    internal uint FileSizeLow;
    internal uint NumberOfLinks;
    internal uint FileIndexHigh;
    internal uint FileIndexLow;
}

internal sealed class BaiReadinessPhysicalIdentity
{
    private const uint FileFlagBackupSemantics = 0x02000000;
    private const uint FileFlagOpenReparsePoint = 0x00200000;
    private const uint OpenExisting = 3;
    private const uint ShareReadWriteDelete = 1 | 2 | 4;

    private BaiReadinessPhysicalIdentity(uint volume, uint high, uint low, uint links)
    {
        Volume = volume; High = high; Low = low; LinkCount = links;
    }

    private uint Volume { get; set; }
    private uint High { get; set; }
    private uint Low { get; set; }
    internal uint LinkCount { get; private set; }

    internal static BaiReadinessPhysicalIdentity ForDirectory(string path)
    {
        using (var handle = CreateFile(path, 0, ShareReadWriteDelete, IntPtr.Zero, OpenExisting,
            FileFlagBackupSemantics | FileFlagOpenReparsePoint, IntPtr.Zero)) {
            if (handle.IsInvalid) throw new IOException("READINESS_METADATA_PARENT_OPEN_FAILED");
            return ForFileHandle(handle);
        }
    }

    internal static BaiReadinessPhysicalIdentity ForFile(string path)
    {
        using (var handle = CreateFile(path, 0, ShareReadWriteDelete, IntPtr.Zero, OpenExisting,
            FileFlagOpenReparsePoint, IntPtr.Zero)) {
            if (handle.IsInvalid) throw new IOException("READINESS_METADATA_TARGET_OPEN_FAILED");
            return ForFileHandle(handle);
        }
    }

    internal static BaiReadinessPhysicalIdentity ForFileHandle(SafeFileHandle handle)
    {
        BaiReadinessByHandleFileInformation value;
        if (handle == null || handle.IsInvalid || !GetFileInformationByHandle(handle, out value))
            throw new IOException("READINESS_METADATA_IDENTITY_READ_FAILED");
        return new BaiReadinessPhysicalIdentity(value.VolumeSerialNumber,
            value.FileIndexHigh, value.FileIndexLow, value.NumberOfLinks);
    }

    public override bool Equals(object value)
    {
        var other = value as BaiReadinessPhysicalIdentity;
        return other != null && Volume == other.Volume && High == other.High && Low == other.Low;
    }

    public override int GetHashCode()
    {
        return unchecked((int)(Volume ^ High ^ Low));
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFile(string name, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle,
        out BaiReadinessByHandleFileInformation information);
}
