using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

internal enum BaiReadinessLifecycle
{
    Created, Arming, Active, Revoking, Settling, StopPending, Settled,
    Publishing, MetadataUnconfirmed, Terminal
}

internal enum BaiReadinessPhase
{
    AdjustmentOnly, Frozen, RoomToneOpen, RoomToneClosed, NormalSpeechOpen, PairClosed
}

internal enum BaiReadinessWindowPurpose { RoomTone, NormalSpeech }
internal enum BaiReadinessClosureState { Closed, Interrupted }
internal enum BaiReadinessDerivedState { ComputedFinite, MeasuredZero, NoInput, NotComputableNonfinite }
internal enum BaiReadinessPublicationOutcome
{
    NotAttempted, InProgress, Verified, NotPublishedConfirmed, Unknown
}

internal sealed class BaiReadinessLimits
{
    internal const long MaxExactJsonInteger = 9007199254740991L;
    internal const int HardCapMinutes = 3;
    internal const int HardCapMilliseconds = 180000;
    internal const int ArmBudgetMilliseconds = 10000;
    internal const int NoInputBudgetMilliseconds = 5000;
    internal const int StopSettlementBudgetMilliseconds = 2000;
    internal const int MetadataPublicationBudgetMilliseconds = 2000;
    internal const int WatchdogMaxIntervalMilliseconds = 100;
    internal const int MaxPendingCommands = 16;
    internal const int MaxSettingsEpochs = 8;
    internal const int MaxWindows = 16;
    internal const int MaxEvents = 64;
    internal const int MaxReceiptBytes = 262144;
    internal const float ExcursionThreshold = 0.9999F;
}

internal sealed class BaiReadinessEventRecord
{
    internal BaiReadinessEventRecord(string id, string commandId, long tick, long frame,
        string epochId, string windowId, string code, string reason)
    {
        EventId = BaiReadinessAdmission.RequireId(id);
        CommandId = commandId;
        Tick = tick;
        Frame = frame;
        EpochId = epochId;
        WindowId = windowId;
        Code = code;
        Reason = reason;
    }

    internal string EventId { get; private set; }
    internal string CommandId { get; private set; }
    internal long Tick { get; private set; }
    internal long Frame { get; private set; }
    internal string EpochId { get; private set; }
    internal string WindowId { get; private set; }
    internal string Code { get; private set; }
    internal string Reason { get; private set; }

    internal IDictionary<string, object> ToObject()
    {
        return new Dictionary<string, object>(StringComparer.Ordinal) {
            { "event_id", EventId }, { "command_id", CommandId }, { "tick", Tick },
            { "frame", Frame }, { "epoch_id", EpochId }, { "window_id", WindowId },
            { "code", Code }, { "reason_code", Reason }
        };
    }
}

internal sealed class BaiReadinessAttestationRecord
{
    private readonly List<string> invalidationEventIds = new List<string>();

    private BaiReadinessAttestationRecord(string state, string reference,
        string ownerSubjectBindingSha256, string commandId, long? observedTick)
    {
        State = state;
        AttestationRef = reference;
        OwnerSubjectBindingSha256 = ownerSubjectBindingSha256;
        CommandId = commandId;
        ObservedTick = observedTick;
        CurrentnessState = state == "NOT_ATTESTED" ? "NOT_ATTESTED" : "CURRENT";
    }

    internal string State { get; private set; }
    internal string AttestationRef { get; private set; }
    internal string OwnerSubjectBindingSha256 { get; private set; }
    internal string CommandId { get; private set; }
    internal long? ObservedTick { get; private set; }
    internal string CurrentnessState { get; private set; }

    internal static BaiReadinessAttestationRecord NotAttested()
    {
        return new BaiReadinessAttestationRecord("NOT_ATTESTED", null, null, null, null);
    }

    internal static BaiReadinessAttestationRecord Current(string state, string reference,
        string ownerSubjectBindingSha256, string commandId, long observedTick)
    {
        if (state != "ATTESTED_OFF" && state != "ATTESTED_NOT_OFF" &&
            state != "ATTESTED_FIXED") throw new ArgumentException("ATTESTATION_STATE");
        BaiReadinessAdmission.RequireId(reference);
        BaiReadinessAdmission.RequireId(commandId);
        if (String.IsNullOrEmpty(ownerSubjectBindingSha256) ||
            !ownerSubjectBindingSha256.StartsWith("sha256:", StringComparison.Ordinal))
            throw new ArgumentException("ATTESTATION_SUBJECT_BINDING");
        return new BaiReadinessAttestationRecord(state, reference,
            ownerSubjectBindingSha256, commandId, observedTick);
    }

    internal void Invalidate(string eventId)
    {
        if (State == "NOT_ATTESTED") return;
        invalidationEventIds.Add(BaiReadinessAdmission.RequireId(eventId));
        CurrentnessState = "REVOKED";
    }

    internal BaiReadinessAttestationRecord Copy()
    {
        var copy = new BaiReadinessAttestationRecord(State, AttestationRef,
            OwnerSubjectBindingSha256, CommandId, ObservedTick);
        foreach (var id in invalidationEventIds) copy.Invalidate(id);
        return copy;
    }

    internal IDictionary<string, object> ToObject(string epochId)
    {
        return new Dictionary<string, object>(StringComparer.Ordinal) {
            { "state", State }, { "attestation_ref", AttestationRef },
            { "owner_subject_binding_sha256", OwnerSubjectBindingSha256 },
            { "command_id", CommandId }, { "observed_tick", ObservedTick },
            { "currentness_state", CurrentnessState },
            { "invalidation_event_ids", invalidationEventIds.ToArray() },
            { "epoch_id", epochId }
        };
    }
}

internal sealed class BaiReadinessFreezeEvidence
{
    internal BaiReadinessFreezeEvidence(string settingsRef, string settingsSha256,
        BaiReadinessAttestationRecord ac, BaiReadinessAttestationRecord fan,
        BaiReadinessAttestationRecord fixedSettings)
    {
        SettingsRef = BaiReadinessAdmission.RequireId(settingsRef);
        SettingsSha256 = settingsSha256;
        Ac = (ac ?? throw new ArgumentNullException("ac")).Copy();
        Fan = (fan ?? throw new ArgumentNullException("fan")).Copy();
        FixedSettings = (fixedSettings ?? throw new ArgumentNullException("fixedSettings")).Copy();
        if (FixedSettings.State != "ATTESTED_FIXED" ||
            FixedSettings.CurrentnessState != "CURRENT")
            throw new ArgumentException("FIXED_ATTESTATION_REQUIRED");
    }

    internal string SettingsRef { get; private set; }
    internal string SettingsSha256 { get; private set; }
    internal BaiReadinessAttestationRecord Ac { get; private set; }
    internal BaiReadinessAttestationRecord Fan { get; private set; }
    internal BaiReadinessAttestationRecord FixedSettings { get; private set; }

    internal BaiReadinessFreezeEvidence Copy()
    {
        return new BaiReadinessFreezeEvidence(SettingsRef, SettingsSha256, Ac, Fan, FixedSettings);
    }

    internal void ValidateForFreeze(string subjectBindingSha256, string commandId, long tick)
    {
        BaiReadinessAdmission.RequireDigest(SettingsSha256, false);
        ValidateAssertion(Ac, false, subjectBindingSha256, commandId, tick);
        ValidateAssertion(Fan, false, subjectBindingSha256, commandId, tick);
        ValidateAssertion(FixedSettings, true, subjectBindingSha256, commandId, tick);
    }

    private static void ValidateAssertion(BaiReadinessAttestationRecord value, bool fixedRole,
        string subjectBindingSha256, string commandId, long tick)
    {
        if (!fixedRole && value.State == "NOT_ATTESTED") {
            if (value.CurrentnessState != "NOT_ATTESTED" || value.AttestationRef != null ||
                value.OwnerSubjectBindingSha256 != null || value.CommandId != null || value.ObservedTick != null)
                throw new InvalidOperationException("REJECT_ATTESTATION_MISSING");
            return;
        }
        bool roleMatches = fixedRole ? value.State == "ATTESTED_FIXED" :
            value.State == "ATTESTED_OFF" || value.State == "ATTESTED_NOT_OFF";
        if (!roleMatches || value.CurrentnessState != "CURRENT" ||
            value.OwnerSubjectBindingSha256 != subjectBindingSha256 ||
            value.CommandId != commandId || value.ObservedTick != tick)
            throw new InvalidOperationException("REJECT_ATTESTATION_MISSING");
        BaiReadinessAdmission.RequireDigest(value.OwnerSubjectBindingSha256, true);
        BaiReadinessAdmission.RequireId(value.AttestationRef);
    }

    internal static BaiReadinessFreezeEvidence CreatePureTest(string epochId,
        string commandId, long tick, string subjectBindingSha256)
    {
        const string hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        return new BaiReadinessFreezeEvidence("settings-" + epochId, hash,
            BaiReadinessAttestationRecord.NotAttested(),
            BaiReadinessAttestationRecord.NotAttested(),
            BaiReadinessAttestationRecord.Current("ATTESTED_FIXED",
                "fixed-" + epochId, subjectBindingSha256, commandId, tick));
    }
}

internal enum BaiReadinessCommandKind
{
    FreezeSettings, StartRoomTone, StartNormalSpeech, EndWindow,
    SettingsChanged, WithdrawWindow, OwnerDistortionReport, OwnerRedReport, OwnerStop
}

internal sealed class BaiReadinessCommand
{
    private BaiReadinessCommand(BaiReadinessCommandKind kind, string operationId,
        string commandId, long tick, string epochId, string windowId,
        BaiReadinessFreezeEvidence freezeEvidence)
    {
        Kind = kind;
        OperationId = BaiReadinessAdmission.RequireId(operationId);
        CommandId = BaiReadinessAdmission.RequireId(commandId);
        if (tick < 0 || tick > BaiReadinessLimits.MaxExactJsonInteger)
            throw new ArgumentOutOfRangeException("tick");
        Tick = tick;
        EpochId = epochId;
        WindowId = windowId;
        FreezeEvidence = freezeEvidence;
    }

    internal BaiReadinessCommandKind Kind { get; private set; }
    internal string OperationId { get; private set; }
    internal string CommandId { get; private set; }
    internal long Tick { get; private set; }
    internal string EpochId { get; private set; }
    internal string WindowId { get; private set; }
    internal BaiReadinessFreezeEvidence FreezeEvidence { get; private set; }

    internal static BaiReadinessCommand Freeze(string operationId, string epochId,
        string commandId, long tick, BaiReadinessFreezeEvidence evidence)
    {
        return new BaiReadinessCommand(BaiReadinessCommandKind.FreezeSettings,
            operationId, commandId, tick, BaiReadinessAdmission.RequireId(epochId),
            null, evidence ?? throw new ArgumentNullException("evidence"));
    }

    internal static BaiReadinessCommand StartWindow(string operationId,
        BaiReadinessWindowPurpose purpose, string windowId, string commandId, long tick)
    {
        return new BaiReadinessCommand(
            purpose == BaiReadinessWindowPurpose.RoomTone ?
                BaiReadinessCommandKind.StartRoomTone :
                BaiReadinessCommandKind.StartNormalSpeech,
            operationId, commandId, tick, null,
            BaiReadinessAdmission.RequireId(windowId), null);
    }

    internal static BaiReadinessCommand End(string operationId, string commandId, long tick)
    {
        return new BaiReadinessCommand(BaiReadinessCommandKind.EndWindow,
            operationId, commandId, tick, null, null, null);
    }

    internal static BaiReadinessCommand SettingsChanged(
        string operationId, string commandId, long tick)
    {
        return new BaiReadinessCommand(BaiReadinessCommandKind.SettingsChanged,
            operationId, commandId, tick, null, null, null);
    }

    internal static BaiReadinessCommand Stop(string operationId, string commandId, long tick)
    {
        return new BaiReadinessCommand(BaiReadinessCommandKind.OwnerStop,
            operationId, commandId, tick, null, null, null);
    }

    internal static BaiReadinessCommand Report(string operationId, string commandId,
        long tick, string windowId, bool redIndicator)
    {
        return new BaiReadinessCommand(redIndicator ? BaiReadinessCommandKind.OwnerRedReport :
            BaiReadinessCommandKind.OwnerDistortionReport, operationId, commandId, tick,
            null, windowId == null ? null : BaiReadinessAdmission.RequireId(windowId), null);
    }

    internal static BaiReadinessCommand Withdraw(string operationId, string commandId,
        long tick, string windowId)
    {
        return new BaiReadinessCommand(BaiReadinessCommandKind.WithdrawWindow, operationId,
            commandId, tick, null, BaiReadinessAdmission.RequireId(windowId), null);
    }
}

internal sealed class BaiReadinessSettingsEpoch
{
    private readonly List<string> invalidationEventIds = new List<string>();

    internal BaiReadinessSettingsEpoch(string epochId, string freezeCommandId,
        long freezeFrame, long freezeTick, BaiReadinessFreezeEvidence evidence)
    {
        EpochId = BaiReadinessAdmission.RequireId(epochId);
        FreezeCommandId = BaiReadinessAdmission.RequireId(freezeCommandId);
        FreezeFrame = freezeFrame;
        FreezeTick = freezeTick;
        Evidence = (evidence ?? throw new ArgumentNullException("evidence")).Copy();
    }

    internal string EpochId { get; private set; }
    internal string FreezeCommandId { get; private set; }
    internal long FreezeFrame { get; private set; }
    internal long FreezeTick { get; private set; }
    internal BaiReadinessFreezeEvidence Evidence { get; private set; }

    internal void Invalidate(string eventId)
    {
        invalidationEventIds.Add(BaiReadinessAdmission.RequireId(eventId));
        Evidence.Ac.Invalidate(eventId);
        Evidence.Fan.Invalidate(eventId);
        Evidence.FixedSettings.Invalidate(eventId);
    }

    internal IDictionary<string, object> ToObject(string captureBindingSha256)
    {
        return new Dictionary<string, object>(StringComparer.Ordinal) {
            { "epoch_id", EpochId }, { "freeze_command_id", FreezeCommandId },
            { "freeze_frame", FreezeFrame }, { "freeze_tick", FreezeTick },
            { "capture_binding_sha256", captureBindingSha256 },
            { "settings_ref", Evidence.SettingsRef },
            { "settings_sha256", Evidence.SettingsSha256 },
            { "settings_assurance", "OWNER_ATTESTED_WITH_AVAILABLE_SOFTWARE_FACTS" },
            { "owner_ac_attestation", Evidence.Ac.ToObject(EpochId) },
            { "owner_fan_attestation", Evidence.Fan.ToObject(EpochId) },
            { "owner_fixed_settings_attestation", Evidence.FixedSettings.ToObject(EpochId) },
            { "invalidation_event_ids", invalidationEventIds.ToArray() }
        };
    }
}

internal sealed class BaiReadinessAdmission
{
    private BaiReadinessAdmission(
        string operationId, string sessionId, string ownerStartCommandId, string subjectBindingSha256)
    {
        OperationId = RequireId(operationId);
        SessionId = RequireId(sessionId);
        OwnerStartCommandId = RequireId(ownerStartCommandId);
        SubjectBindingSha256 = RequireDigest(subjectBindingSha256, true);
    }

    internal string OperationId { get; private set; }
    internal string SessionId { get; private set; }
    internal string OwnerStartCommandId { get; private set; }
    internal string SubjectBindingSha256 { get; private set; }

    internal static BaiReadinessAdmission CreatePureTest(
        string operationId, string sessionId, string ownerStartCommandId, string subjectBindingSha256)
    {
        return new BaiReadinessAdmission(operationId, sessionId, ownerStartCommandId, subjectBindingSha256);
    }

    internal static string RequireDigest(string value, bool external)
    {
        int offset = external ? 7 : 0;
        if (value == null || value.Length != offset + 64 ||
            (external && !value.StartsWith("sha256:", StringComparison.Ordinal)))
            throw new InvalidOperationException("REJECT_ATTESTATION_MISSING");
        for (int index = offset; index < value.Length; index++) {
            char c = value[index];
            if (!(c >= '0' && c <= '9') && !(c >= 'a' && c <= 'f'))
                throw new InvalidOperationException("REJECT_ATTESTATION_MISSING");
        }
        return value;
    }

    internal static string RequireId(string value)
    {
        if (String.IsNullOrEmpty(value) || value.Length > 100) throw new ArgumentException("ID_INVALID");
        if (!IsAlphaNumeric(value[0])) throw new ArgumentException("ID_INVALID");
        foreach (char c in value) {
            if (!(IsAlphaNumeric(c) || c == '.' || c == '_' || c == ':' || c == '-'))
                throw new ArgumentException("ID_INVALID");
        }
        return value;
    }

    private static bool IsAlphaNumeric(char c)
    {
        return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9');
    }
}

internal sealed class BaiReadinessChannelAggregate
{
    private double sum;
    private double sumSquares;
    private double minimum;
    private double maximum;
    private double maximumAbsolute;
    private bool hasFinite;

    internal long FrameCount { get; private set; }
    internal long FiniteCount { get; private set; }
    internal long NanCount { get; private set; }
    internal long PositiveInfinityCount { get; private set; }
    internal long NegativeInfinityCount { get; private set; }
    internal long ExcursionCount { get; private set; }
    internal double SumFinite { get { return sum; } }
    internal double SumSquaresFinite { get { return sumSquares; } }
    internal double? SignedMinimum { get { return hasFinite ? (double?)minimum : null; } }
    internal double? SignedMaximum { get { return hasFinite ? (double?)maximum : null; } }
    internal double? MaximumAbsolute { get { return hasFinite ? (double?)maximumAbsolute : null; } }

    internal void Merge(BaiReadinessPacketChannelAggregate packet)
    {
        if (packet == null) throw new ArgumentNullException("packet");
        long nextFrames = checked(FrameCount + packet.FrameCount);
        long nextFinite = checked(FiniteCount + packet.FiniteCount);
        long nextNan = checked(NanCount + packet.NanCount);
        long nextPositive = checked(PositiveInfinityCount + packet.PositiveInfinityCount);
        long nextNegative = checked(NegativeInfinityCount + packet.NegativeInfinityCount);
        long nextExcursions = checked(ExcursionCount + packet.ExcursionCount);
        double nextSum = sum + packet.SumFinite;
        double nextSquares = sumSquares + packet.SumSquaresFinite;
        if (Double.IsNaN(nextSum) || Double.IsInfinity(nextSum) ||
            Double.IsNaN(nextSquares) || Double.IsInfinity(nextSquares))
            throw new ArithmeticException("ARITHMETIC_OVERFLOW");
        FrameCount = nextFrames; FiniteCount = nextFinite; NanCount = nextNan;
        PositiveInfinityCount = nextPositive; NegativeInfinityCount = nextNegative;
        ExcursionCount = nextExcursions; sum = nextSum; sumSquares = nextSquares;
        if (packet.HasFinite) {
            if (!hasFinite) {
                minimum = packet.Minimum; maximum = packet.Maximum;
                maximumAbsolute = packet.MaximumAbsolute; hasFinite = true;
            } else {
                minimum = Math.Min(minimum, packet.Minimum);
                maximum = Math.Max(maximum, packet.Maximum);
                maximumAbsolute = Math.Max(maximumAbsolute, packet.MaximumAbsolute);
            }
        }
    }

    internal BaiReadinessChannelStatistics Freeze(int channelIndex)
    {
        var state = BaiReadinessDerivedState.NoInput;
        double? mean = null, rms = null, peak = null, rmsDb = null, peakDb = null;
        if (FrameCount > 0 && NanCount + PositiveInfinityCount + NegativeInfinityCount > 0) {
            state = BaiReadinessDerivedState.NotComputableNonfinite;
        } else if (FrameCount > 0 && maximumAbsolute == 0.0) {
            state = BaiReadinessDerivedState.MeasuredZero;
            mean = rms = peak = 0.0;
        } else if (FrameCount > 0) {
            state = BaiReadinessDerivedState.ComputedFinite;
            mean = sum / FiniteCount;
            rms = Math.Sqrt(sumSquares / FiniteCount);
            peak = maximumAbsolute;
            if (rms > 0.0) rmsDb = 20.0 * Math.Log10(rms.Value);
            if (peak > 0.0) peakDb = 20.0 * Math.Log10(peak.Value);
        }
        return new BaiReadinessChannelStatistics(
            channelIndex, FrameCount, FiniteCount, NanCount, PositiveInfinityCount,
            NegativeInfinityCount, sum, sumSquares, SignedMinimum, SignedMaximum,
            MaximumAbsolute, ExcursionCount, state, mean, rms, peak, rmsDb, peakDb);
    }
}

internal sealed class BaiReadinessPacketChannelAggregate
{
    internal long FrameCount { get; private set; }
    internal long FiniteCount { get; private set; }
    internal long NanCount { get; private set; }
    internal long PositiveInfinityCount { get; private set; }
    internal long NegativeInfinityCount { get; private set; }
    internal long ExcursionCount { get; private set; }
    internal double SumFinite { get; private set; }
    internal double SumSquaresFinite { get; private set; }
    internal bool HasFinite { get; private set; }
    internal double Minimum { get; private set; }
    internal double Maximum { get; private set; }
    internal double MaximumAbsolute { get; private set; }

    internal void Add(float value)
    {
        checked { FrameCount++; }
        if (Single.IsNaN(value)) { checked { NanCount++; } return; }
        if (Single.IsPositiveInfinity(value)) { checked { PositiveInfinityCount++; } return; }
        if (Single.IsNegativeInfinity(value)) { checked { NegativeInfinityCount++; } return; }
        double finite = value;
        double nextSum = SumFinite + finite;
        double nextSquares = SumSquaresFinite + finite * finite;
        if (Double.IsNaN(nextSum) || Double.IsInfinity(nextSum) ||
            Double.IsNaN(nextSquares) || Double.IsInfinity(nextSquares))
            throw new ArithmeticException("ARITHMETIC_OVERFLOW");
        SumFinite = nextSum; SumSquaresFinite = nextSquares;
        checked { FiniteCount++; }
        if (Math.Abs(finite) >= BaiReadinessLimits.ExcursionThreshold) checked { ExcursionCount++; }
        if (!HasFinite) {
            Minimum = Maximum = finite; MaximumAbsolute = Math.Abs(finite); HasFinite = true;
        } else {
            Minimum = Math.Min(Minimum, finite); Maximum = Math.Max(Maximum, finite);
            MaximumAbsolute = Math.Max(MaximumAbsolute, Math.Abs(finite));
        }
    }
}

internal sealed class BaiReadinessPacketScan
{
    private BaiReadinessPacketScan(int frames, int planes, long token,
        IList<BaiReadinessPacketChannelAggregate> channels)
    {
        Frames = frames; Planes = planes; MeasurementToken = token; Channels = channels;
    }

    internal int Frames { get; private set; }
    internal int Planes { get; private set; }
    internal long MeasurementToken { get; private set; }
    internal IList<BaiReadinessPacketChannelAggregate> Channels { get; private set; }
    internal bool HasNonfinite {
        get {
            foreach (var channel in Channels) if (channel.NanCount +
                channel.PositiveInfinityCount + channel.NegativeInfinityCount > 0) return true;
            return false;
        }
    }

    internal static BaiReadinessPacketScan Create(
        byte[] payload, int frames, int planes, int expectedPlanes, long token)
    {
        if (frames <= 0 || frames > 8192 || planes != expectedPlanes)
            throw new InvalidOperationException("FORMAT_DRIFT");
        if (payload == null || payload.Length != checked(frames * planes * 4))
            throw new InvalidOperationException("INVALID_HEADER");
        var channels = new List<BaiReadinessPacketChannelAggregate>(planes);
        for (int plane = 0; plane < planes; plane++) {
            var aggregate = new BaiReadinessPacketChannelAggregate();
            int planeOffset = plane * frames * 4;
            for (int frame = 0; frame < frames; frame++)
                aggregate.Add(BitConverter.ToSingle(payload, planeOffset + frame * 4));
            channels.Add(aggregate);
        }
        return new BaiReadinessPacketScan(frames, planes, token, channels.AsReadOnly());
    }
}

internal sealed class BaiReadinessChannelStatistics
{
    internal BaiReadinessChannelStatistics(
        int index, long frames, long finite, long nan, long positiveInfinity,
        long negativeInfinity, double sum, double sumSquares, double? minimum,
        double? maximum, double? maximumAbsolute, long excursions,
        BaiReadinessDerivedState state, double? mean, double? rms, double? peak,
        double? rmsDb, double? peakDb)
    {
        ChannelIndex = index; FrameCount = frames; FiniteCount = finite; NanCount = nan;
        PositiveInfinityCount = positiveInfinity; NegativeInfinityCount = negativeInfinity;
        SumFinite = sum; SumSquaresFinite = sumSquares; SignedMinimum = minimum;
        SignedMaximum = maximum; MaximumAbsolute = maximumAbsolute; ExcursionCount = excursions;
        DerivedState = state; MeanDc = mean; RmsLinear = rms; PeakLinear = peak;
        RmsDbfs = rmsDb; PeakDbfs = peakDb;
    }

    internal int ChannelIndex { get; private set; }
    internal long FrameCount { get; private set; }
    internal long FiniteCount { get; private set; }
    internal long NanCount { get; private set; }
    internal long PositiveInfinityCount { get; private set; }
    internal long NegativeInfinityCount { get; private set; }
    internal double SumFinite { get; private set; }
    internal double SumSquaresFinite { get; private set; }
    internal double? SignedMinimum { get; private set; }
    internal double? SignedMaximum { get; private set; }
    internal double? MaximumAbsolute { get; private set; }
    internal long ExcursionCount { get; private set; }
    internal BaiReadinessDerivedState DerivedState { get; private set; }
    internal double? MeanDc { get; private set; }
    internal double? RmsLinear { get; private set; }
    internal double? PeakLinear { get; private set; }
    internal double? RmsDbfs { get; private set; }
    internal double? PeakDbfs { get; private set; }

    internal IDictionary<string, object> ToObject()
    {
        return new Dictionary<string, object>(StringComparer.Ordinal) {
            { "channel_index", ChannelIndex }, { "frame_count", FrameCount },
            { "finite_count", FiniteCount }, { "nan_count", NanCount },
            { "positive_inf_count", PositiveInfinityCount },
            { "negative_inf_count", NegativeInfinityCount },
            { "sum_finite", SumFinite }, { "sum_squares_finite", SumSquaresFinite },
            { "signed_min_finite", SignedMinimum }, { "signed_max_finite", SignedMaximum },
            { "max_abs_finite", MaximumAbsolute },
            { "excursion_threshold_abs", 0.9999 }, { "excursion_count", ExcursionCount },
            { "derived_state", DerivedStateName(DerivedState) }, { "mean_dc", MeanDc },
            { "rms_linear", RmsLinear }, { "peak_linear", PeakLinear },
            { "rms_dbfs", RmsDbfs }, { "peak_dbfs", PeakDbfs }
        };
    }

    private static string DerivedStateName(BaiReadinessDerivedState value)
    {
        switch (value) {
            case BaiReadinessDerivedState.ComputedFinite: return "COMPUTED_FINITE";
            case BaiReadinessDerivedState.MeasuredZero: return "MEASURED_ZERO";
            case BaiReadinessDerivedState.NoInput: return "NO_INPUT";
            case BaiReadinessDerivedState.NotComputableNonfinite:
                return "NOT_COMPUTABLE_NONFINITE";
            default: throw new InvalidOperationException("DERIVED_STATE");
        }
    }
}

internal sealed class BaiReadinessWindow
{
    private readonly List<BaiReadinessChannelAggregate> channels = new List<BaiReadinessChannelAggregate>();
    private readonly List<string> invalidationEventIds = new List<string>();
    private readonly SortedSet<string> observationFlags = new SortedSet<string>(StringComparer.Ordinal);

    internal BaiReadinessWindow(string id, string epochId, BaiReadinessWindowPurpose purpose,
        long startFrame, long startTick, string commandId, string startEventId, int channelCount)
    {
        WindowId = BaiReadinessAdmission.RequireId(id);
        EpochId = BaiReadinessAdmission.RequireId(epochId);
        StartCommandId = BaiReadinessAdmission.RequireId(commandId);
        StartEventId = BaiReadinessAdmission.RequireId(startEventId);
        Purpose = purpose; StartFrame = startFrame; EndFrame = startFrame;
        StartTick = startTick; EndTick = startTick;
        CurrentnessState = "SAME_EPOCH_AT_CLOSE";
        observationFlags.Add("UPSTREAM_LOSS_UNKNOWN");
        for (int i = 0; i < channelCount; i++) channels.Add(new BaiReadinessChannelAggregate());
    }

    internal string WindowId { get; private set; }
    internal string EpochId { get; private set; }
    internal string StartCommandId { get; private set; }
    internal string EndCommandId { get; private set; }
    internal string StartEventId { get; private set; }
    internal string ClosureEventId { get; private set; }
    internal string CurrentnessState { get; private set; }
    internal BaiReadinessWindowPurpose Purpose { get; private set; }
    internal BaiReadinessClosureState ClosureState { get; private set; }
    internal long StartFrame { get; private set; }
    internal long EndFrame { get; private set; }
    internal long StartTick { get; private set; }
    internal long EndTick { get; private set; }
    internal ulong? FirstSequence { get; private set; }
    internal ulong? LastSequence { get; private set; }
    internal bool IsOpen { get; private set; } = true;

    internal void AddPacket(BaiReadinessPacketScan packet, ulong sequence)
    {
        if (packet == null || !IsOpen || packet.Planes != channels.Count)
            throw new InvalidOperationException("WINDOW_PACKET_INVALID");
        if (!FirstSequence.HasValue) FirstSequence = sequence;
        LastSequence = sequence;
        for (int plane = 0; plane < packet.Planes; plane++)
            channels[plane].Merge(packet.Channels[plane]);
        foreach (var channel in packet.Channels) {
            if (channel.ExcursionCount > 0) observationFlags.Add("RECEIVED_EXCURSION_PRESENT");
            if (channel.NanCount + channel.PositiveInfinityCount +
                channel.NegativeInfinityCount > 0) observationFlags.Add("SIGNAL_NOT_FINITE");
        }
    }

    internal void Close(string commandId, long endFrame, long endTick, bool interrupted,
        string closureEventId)
    {
        if (!IsOpen) throw new InvalidOperationException("WINDOW_ALREADY_CLOSED");
        if (endFrame < StartFrame || endTick < StartTick)
            throw new InvalidOperationException("WINDOW_COORDINATE_REGRESSION");
        EndCommandId = interrupted ? null : BaiReadinessAdmission.RequireId(commandId);
        ClosureEventId = BaiReadinessAdmission.RequireId(closureEventId);
        EndFrame = endFrame; EndTick = endTick;
        ClosureState = interrupted ? BaiReadinessClosureState.Interrupted : BaiReadinessClosureState.Closed;
        IsOpen = false;
    }

    internal void Invalidate(string eventId, bool whileOpen, bool withdrawn)
    {
        invalidationEventIds.Add(BaiReadinessAdmission.RequireId(eventId));
        if (withdrawn) CurrentnessState = "WITHDRAWN";
        else if (whileOpen) CurrentnessState = "INVALIDATED_WHILE_OPEN";
        else if (CurrentnessState == "SAME_EPOCH_AT_CLOSE")
            CurrentnessState = "INVALIDATED_AFTER_CLOSE";
    }

    internal void Report(bool redIndicator)
    {
        observationFlags.Add(redIndicator ? "OWNER_RED_INDICATOR_REPORTED" :
            "OWNER_DISTORTION_REPORTED");
    }

    internal IList<BaiReadinessChannelStatistics> FreezeStatistics()
    {
        var result = new List<BaiReadinessChannelStatistics>();
        for (int i = 0; i < channels.Count; i++) result.Add(channels[i].Freeze(i));
        return result.AsReadOnly();
    }

    internal IDictionary<string, object> ToObject()
    {
        var statistics = new List<object>();
        foreach (var value in FreezeStatistics()) statistics.Add(value.ToObject());
        return new Dictionary<string, object>(StringComparer.Ordinal) {
            { "window_id", WindowId }, { "epoch_id", EpochId },
            { "purpose", Purpose == BaiReadinessWindowPurpose.RoomTone ? "ROOM_TONE" : "NORMAL_SPEECH" },
            { "coordinate_domain", "ACCEPTED_AUTHENTICATED_FRAME_V1" },
            { "start_frame", StartFrame }, { "end_frame", EndFrame },
            { "start_command_id", StartCommandId }, { "end_command_id", EndCommandId },
            { "start_event_id", StartEventId }, { "closure_event_id", ClosureEventId },
            { "start_tick", StartTick }, { "end_tick", EndTick },
            { "first_sequence", FirstSequence.HasValue ? FirstSequence.Value.ToString() : null },
            { "last_sequence", LastSequence.HasValue ? LastSequence.Value.ToString() : null },
            { "frame_count", EndFrame - StartFrame },
            { "closure_state", ClosureState == BaiReadinessClosureState.Closed ? "CLOSED" : "INTERRUPTED" },
            { "currentness_state", CurrentnessState },
            { "observation_flags", new List<string>(observationFlags).ToArray() },
            { "invalidation_event_ids", invalidationEventIds.ToArray() },
            { "channel_statistics", statistics.ToArray() }
        };
    }
}

internal sealed class BaiReadinessTerminalProjection
{
    private readonly object[] events;
    private readonly object[] epochs;
    private readonly object[] windows;
    private readonly IList<string> secondaryReasons;
    private int consumed;

    internal BaiReadinessTerminalProjection(string operationId, string sessionId,
        long frequency, long start, long stop, long revoke, long settled,
        string primaryReason, IList<string> secondary, bool interruptedAtRevoke,
        long authenticatedPackets, long committedPackets, long committedFrames,
        long invalidHeaders, long sequenceOrderErrors, long timestampRegressions,
        long connectionAttempts, long incompletePackets, long hmacFailures, long nonceMismatches,
        long sequenceGapEvents, long missingPackets, long discardedAfterRevocation,
        long discardedOnTokenChange, ulong? firstSequence, ulong? lastSequence,
        ulong? firstTimestamp, ulong? lastTimestamp,
        IList<BaiReadinessEventRecord> eventRecords,
        IList<BaiReadinessSettingsEpoch> epochRecords,
        IList<BaiReadinessWindow> windowRecords)
    {
        OperationId = operationId;
        SessionId = sessionId;
        MonotonicFrequency = frequency;
        StartTick = start;
        StopRequestTick = stop;
        RevokeTick = revoke;
        SettledTick = settled;
        PrimaryReason = primaryReason;
        InterruptedAtRevoke = interruptedAtRevoke;
        AuthenticatedPackets = authenticatedPackets;
        CommittedPackets = committedPackets;
        CommittedFrames = committedFrames;
        InvalidHeaders = invalidHeaders;
        ConnectionAttempts = connectionAttempts;
        IncompletePackets = incompletePackets;
        HmacFailures = hmacFailures;
        NonceMismatches = nonceMismatches;
        SequenceOrderErrors = sequenceOrderErrors;
        TimestampRegressions = timestampRegressions;
        SequenceGapEvents = sequenceGapEvents;
        MissingPackets = missingPackets;
        DiscardedAfterRevocation = discardedAfterRevocation;
        DiscardedOnTokenChange = discardedOnTokenChange;
        FirstSequence = firstSequence;
        LastSequence = lastSequence;
        FirstTimestamp = firstTimestamp;
        LastTimestamp = lastTimestamp;
        secondaryReasons = new List<string>(secondary).AsReadOnly();
        var eventObjects = new List<object>();
        foreach (var item in eventRecords) eventObjects.Add(item.ToObject());
        events = (object[])BaiReadinessReceipt.CopyJson(eventObjects);
        var epochObjects = new List<object>();
        foreach (var item in epochRecords) epochObjects.Add(item.ToObject(null));
        epochs = (object[])BaiReadinessReceipt.CopyJson(epochObjects);
        var windowObjects = new List<object>();
        foreach (var item in windowRecords) windowObjects.Add(item.ToObject());
        windows = (object[])BaiReadinessReceipt.CopyJson(windowObjects);
    }

    internal string OperationId { get; private set; }
    internal string SessionId { get; private set; }
    internal long MonotonicFrequency { get; private set; }
    internal long StartTick { get; private set; }
    internal long StopRequestTick { get; private set; }
    internal long RevokeTick { get; private set; }
    internal long SettledTick { get; private set; }
    internal string PrimaryReason { get; private set; }
    internal bool InterruptedAtRevoke { get; private set; }
    internal long AuthenticatedPackets { get; private set; }
    internal long CommittedPackets { get; private set; }
    internal long CommittedFrames { get; private set; }
    internal long InvalidHeaders { get; private set; }
    internal long ConnectionAttempts { get; private set; }
    internal long IncompletePackets { get; private set; }
    internal long HmacFailures { get; private set; }
    internal long NonceMismatches { get; private set; }
    internal long SequenceOrderErrors { get; private set; }
    internal long TimestampRegressions { get; private set; }
    internal long SequenceGapEvents { get; private set; }
    internal long MissingPackets { get; private set; }
    internal long DiscardedAfterRevocation { get; private set; }
    internal long DiscardedOnTokenChange { get; private set; }
    internal ulong? FirstSequence { get; private set; }
    internal ulong? LastSequence { get; private set; }
    internal ulong? FirstTimestamp { get; private set; }
    internal ulong? LastTimestamp { get; private set; }

    internal void ApplyTo(IDictionary<string, object> root, string captureBindingSha256)
    {
        Consume().ApplyTo(root, captureBindingSha256);
    }

    internal sealed class Consumption
    {
        private readonly BaiReadinessTerminalProjection owner;
        private int applied;
        private Consumption(BaiReadinessTerminalProjection value) { owner = value; }
        internal BaiReadinessTerminalProjection Owner { get { return owner; } }
        internal static Consumption Take(BaiReadinessTerminalProjection value)
        {
            if (Interlocked.Exchange(ref value.consumed, 1) != 0)
                throw new InvalidOperationException("TERMINAL_PROJECTION_ALREADY_CONSUMED");
            return new Consumption(value);
        }
        internal void ApplyTo(IDictionary<string, object> root, string captureBindingSha256)
        {
            if (Interlocked.Exchange(ref applied, 1) != 0)
                throw new InvalidOperationException("PROJECTION_CONSUMPTION_ALREADY_APPLIED");
            owner.ApplyOwnedTo(root, captureBindingSha256);
        }
    }

    internal Consumption Consume() { return Consumption.Take(this); }

    private void ApplyOwnedTo(IDictionary<string, object> root, string captureBindingSha256)
    {
        root["operation_id"] = OperationId;
        root["session_id"] = SessionId;
        var priorClocks = (System.Collections.IDictionary)root["clocks"];
        root["clocks"] = new Dictionary<string, object>(StringComparer.Ordinal) {
            { "started_at_utc", priorClocks["started_at_utc"] },
            { "stop_requested_at_utc", priorClocks["stop_requested_at_utc"] },
            { "settled_at_utc", priorClocks["settled_at_utc"] },
            { "monotonic_frequency", MonotonicFrequency }, { "start_tick", StartTick },
            { "stop_request_tick", StopRequestTick }, { "revoke_tick", RevokeTick },
            { "settled_tick", SettledTick }
        };
        root["events"] = BaiReadinessReceipt.CopyJson(events);
        var epochObjects = (object[])BaiReadinessReceipt.CopyJson(epochs);
        foreach (var item in epochObjects)
            ((IDictionary<string, object>)item)["capture_binding_sha256"] = captureBindingSha256;
        root["settings_epochs"] = epochObjects;
        root["windows"] = BaiReadinessReceipt.CopyJson(windows);
        root["terminal"] = new Dictionary<string, object>(StringComparer.Ordinal) {
            { "primary_reason", PrimaryReason },
            { "secondary_reasons", new List<string>(secondaryReasons).ToArray() },
            { "receiver_settled", true }, { "in_flight_count", 0 },
            { "local_admission_revoked", true },
            { "open_window_disposition", InterruptedAtRevoke ?
                "INTERRUPTED_AT_REVOKE" : "NONE_OPEN_AT_REVOKE" },
            { "producer_stop_ack_state", "UNAVAILABLE_LEGACY_WIRE" }
        };
        root["transport"] = new Dictionary<string, object>(StringComparer.Ordinal) {
            { "connection_attempts", ConnectionAttempts }, { "authenticated_packets", AuthenticatedPackets },
            { "committed_packets", CommittedPackets }, { "committed_frames", CommittedFrames },
            { "incomplete_packets", IncompletePackets }, { "invalid_headers", InvalidHeaders },
            { "hmac_failures", HmacFailures }, { "nonce_mismatches", NonceMismatches },
            { "sequence_order_errors", SequenceOrderErrors },
            { "source_timestamp_regressions", TimestampRegressions },
            { "sequence_gap_events", SequenceGapEvents },
            { "missing_packets_lower_bound", MissingPackets },
            { "discarded_after_revocation", DiscardedAfterRevocation },
            { "discarded_on_token_change", DiscardedOnTokenChange },
            { "first_sequence", FirstSequence.HasValue ? FirstSequence.Value.ToString() : null },
            { "last_sequence", LastSequence.HasValue ? LastSequence.Value.ToString() : null },
            { "first_source_timestamp", FirstTimestamp.HasValue ? FirstTimestamp.Value.ToString() : null },
            { "last_source_timestamp", LastTimestamp.HasValue ? LastTimestamp.Value.ToString() : null },
            { "upstream_callback_drop_state", "UNKNOWN_WIRE_V1" },
            { "acoustic_dropout_state", "NOT_MEASURED" }
        };
    }
}

internal sealed class BaiReadinessMonitor
{
    internal const string LiveUnavailableReason = "READINESS_DURABLE_EXCLUSION_NOT_BOUND";
    private readonly object gate = new object();
    private readonly BaiReadinessAdmission admission;
    private readonly int channelCount;
    private readonly long monotonicFrequency;
    private readonly List<BaiReadinessWindow> windows = new List<BaiReadinessWindow>();
    private readonly List<BaiReadinessSettingsEpoch> settingsEpochs =
        new List<BaiReadinessSettingsEpoch>();
    private readonly List<BaiReadinessEventRecord> events = new List<BaiReadinessEventRecord>();
    private readonly HashSet<string> epochIds = new HashSet<string>(StringComparer.Ordinal);
    private readonly HashSet<string> windowIds = new HashSet<string>(StringComparer.Ordinal);
    private readonly HashSet<string> commandIds = new HashSet<string>(StringComparer.Ordinal);
    private readonly HashSet<string> queuedCommandIds = new HashSet<string>(StringComparer.Ordinal);
    private readonly Queue<BaiReadinessCommand> commandQueue = new Queue<BaiReadinessCommand>();
    private readonly SortedSet<string> secondaryStopReasons = new SortedSet<string>(StringComparer.Ordinal);
    private BaiReadinessWindow openWindow;
    private BaiReadinessSettingsEpoch currentEpoch;
    private string epochId;
    private ulong expectedSequence;
    private ulong previousTimestamp;
    private bool sequenceAnchored;
    private bool sequenceExhausted;
    private bool timestampAnchored;
    private bool admissionOpen;
    private long cursor;
    private long lastEffectiveTick;
    private long measurementToken = 1;
    private int settingsEpochCount;
    private string stopReason;
    private long startTick;
    private long armedTick;
    private long stopRequestTick;
    private long revokeTick;
    private long settledTick;
    private long lastWatchdogTick;
    private bool inputSeen;
    private ulong? firstSequence;
    private ulong? lastSequence;
    private ulong? firstSourceTimestamp;
    private ulong? lastSourceTimestamp;
    private bool interruptedAtRevoke;
    private string revocationEventId;
    private bool globalRevocationApplied;
    private BaiReadinessTerminalProjection terminalProjection;
    private Task<BaiReadinessMetadataSinkCapability.PublicationResult> publicationTask;
    private Task publicationCompletion;
    private Task latePublicationObservation;
    private BaiReadinessMetadataSinkCapability.PublicationResult publicationProof;
    internal BaiReadinessPublicationOutcome PublicationOutcome { get; private set; }
    internal string PublicationReason { get; private set; } = "NONE";
    internal Task RetainedPublicationTask { get { lock (gate) return publicationTask; } }
    internal Task RetainedLatePublicationObservation { get { lock (gate) return latePublicationObservation; } }
    internal BaiReadinessMetadataSinkCapability.PublicationResult PublicationProof {
        get { lock (gate) return publicationProof; }
    }

    private BaiReadinessMonitor(BaiReadinessAdmission value, int channels, long frequency)
    {
        if (channels < 1 || channels > 8) throw new ArgumentOutOfRangeException("channels");
        if (frequency <= 0 || frequency > 1000000000L)
            throw new ArgumentOutOfRangeException("frequency");
        admission = value ?? throw new ArgumentNullException("value");
        channelCount = channels;
        monotonicFrequency = frequency;
        Lifecycle = BaiReadinessLifecycle.Created;
        Phase = BaiReadinessPhase.AdjustmentOnly;
    }

    internal BaiReadinessLifecycle Lifecycle { get; private set; }
    internal BaiReadinessPhase Phase { get; private set; }
    internal string OperationId { get { return admission.OperationId; } }
    internal string SessionId { get { return admission.SessionId; } }
    internal long CommittedFrames { get { lock (gate) return cursor; } }
    internal long AuthenticatedPackets { get; private set; }
    internal long CommittedPackets { get; private set; }
    internal long SequenceOrderErrors { get; private set; }
    internal long SourceTimestampRegressions { get; private set; }
    internal long SequenceGapEvents { get; private set; }
    internal long MissingPacketsLowerBound { get; private set; }
    internal long InvalidHeaders { get; private set; }
    internal long DiscardedAfterRevocation { get; private set; }
    internal long DiscardedOnTokenChange { get; private set; }
    internal long NonfinitePackets { get; private set; }
    internal long ConnectionAttempts { get; private set; }
    internal long IncompletePackets { get; private set; }
    internal long HmacFailures { get; private set; }
    internal long NonceMismatches { get; private set; }
    internal string StopReason { get { lock (gate) return stopReason; } }
    internal IList<string> SecondaryStopReasons {
        get { lock (gate) return new List<string>(secondaryStopReasons).AsReadOnly(); }
    }
    internal int SettingsEpochCount { get { lock (gate) return settingsEpochCount; } }
    internal int PendingCommandCount { get { lock (gate) return commandQueue.Count; } }
    internal IList<BaiReadinessEventRecord> Events {
        get { lock (gate) return new List<BaiReadinessEventRecord>(events).AsReadOnly(); }
    }
    internal IList<BaiReadinessWindow> Windows {
        get { lock (gate) return new List<BaiReadinessWindow>(windows).AsReadOnly(); }
    }

    internal static bool TryCreateLive(int channels, out BaiReadinessMonitor monitor,
        out string reason)
    {
        if (channels < 1 || channels > 8) throw new ArgumentOutOfRangeException("channels");
        // No TASK-046 / H1 / durable-exclusion producer ABI is bound in F01-F10.
        // There is deliberately no caller-supplied Boolean or data object that can
        // turn this fail-closed production seam into a live monitor.
        monitor = null;
        reason = LiveUnavailableReason;
        return false;
    }

    internal static BaiReadinessMonitor CreatePureTest(string operationId, string sessionId, int channels,
        string subjectBindingSha256 = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    {
        return new BaiReadinessMonitor(
            BaiReadinessAdmission.CreatePureTest(operationId, sessionId,
                "owner-start-" + operationId, subjectBindingSha256), channels, 1000);
    }

    internal void Activate()
    {
        BeginArming(0);
        ObserveConnectionAttempt(0);
        MarkArmed(0);
    }

    internal void BeginArming(long tick)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Created, "LIFECYCLE");
            Require(tick == 0, "REJECT_INVALID_COMMAND");
            Lifecycle = BaiReadinessLifecycle.Arming;
            admissionOpen = true;
            startTick = lastWatchdogTick = lastEffectiveTick = tick;
            commandIds.Add(admission.OwnerStartCommandId);
            AppendEvent(admission.OwnerStartCommandId, tick, 0, null, null,
                "OWNER_START", null);
        }
    }

    internal void MarkArmed(long tick)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Arming && admissionOpen, "LIFECYCLE");
            Require(ConnectionAttempts == 1, "CONNECTION_NOT_OBSERVED");
            RequireTick(tick);
            armedTick = tick;
            lastEffectiveTick = tick;
            Lifecycle = BaiReadinessLifecycle.Active;
        }
    }

    internal bool TryEnqueueCommand(BaiReadinessCommand command, out string rejection)
    {
        lock (gate) {
            if (command == null) { rejection = "REJECT_INVALID_COMMAND"; return false; }
            if (!String.Equals(command.OperationId, OperationId, StringComparison.Ordinal)) {
                rejection = "REJECT_WRONG_OPERATION";
                RecordCommandRejected(command, rejection);
                return false;
            }
            if (!admissionOpen || Lifecycle == BaiReadinessLifecycle.Revoking ||
                Lifecycle == BaiReadinessLifecycle.Settling ||
                Lifecycle == BaiReadinessLifecycle.StopPending) {
                rejection = "REJECT_ALREADY_STOPPING";
                RecordCommandRejected(command, rejection);
                return false;
            }
            if (commandQueue.Count >= BaiReadinessLimits.MaxPendingCommands) {
                rejection = "REJECT_QUEUE_FULL";
                RecordCommandRejected(command, rejection);
                return false;
            }
            if (commandIds.Contains(command.CommandId) ||
                !queuedCommandIds.Add(command.CommandId)) {
                rejection = "REJECT_INVALID_COMMAND";
                return false;
            }
            commandQueue.Enqueue(command);
            rejection = null;
            return true;
        }
    }

    internal bool ProcessNextCommand(out string rejection)
    {
        BaiReadinessCommand command;
        lock (gate) {
            if (commandQueue.Count == 0) { rejection = null; return false; }
            command = commandQueue.Dequeue();
            queuedCommandIds.Remove(command.CommandId);
        }
        try {
            switch (command.Kind) {
                case BaiReadinessCommandKind.FreezeSettings:
                    FreezeSettings(command.EpochId, command.CommandId,
                        command.Tick, command.FreezeEvidence); break;
                case BaiReadinessCommandKind.StartRoomTone:
                    StartWindow(BaiReadinessWindowPurpose.RoomTone, command.WindowId,
                        command.CommandId, command.Tick); break;
                case BaiReadinessCommandKind.StartNormalSpeech:
                    StartWindow(BaiReadinessWindowPurpose.NormalSpeech, command.WindowId,
                        command.CommandId, command.Tick); break;
                case BaiReadinessCommandKind.EndWindow:
                    EndWindow(command.CommandId, command.Tick); break;
                case BaiReadinessCommandKind.SettingsChanged:
                    ObserveSettingsChanged(command.CommandId, command.Tick); break;
                case BaiReadinessCommandKind.WithdrawWindow:
                    WithdrawWindow(command.WindowId, command.CommandId, command.Tick); break;
                case BaiReadinessCommandKind.OwnerDistortionReport:
                case BaiReadinessCommandKind.OwnerRedReport:
                    ReportObservation(command.WindowId, command.CommandId, command.Tick,
                        command.Kind == BaiReadinessCommandKind.OwnerRedReport); break;
                case BaiReadinessCommandKind.OwnerStop:
                    RequestStop("OWNER_STOP", command.CommandId, command.Tick); break;
                default: throw new InvalidOperationException("REJECT_INVALID_COMMAND");
            }
            rejection = null;
            return true;
        } catch (InvalidOperationException ex) {
            rejection = NormalizeCommandRejection(ex.Message);
            lock (gate) RecordCommandRejected(command, rejection);
            return false;
        }
    }

    internal void FreezeSettings(
        string newEpochId, string commandId, long tick, BaiReadinessFreezeEvidence evidence)
    {
        lock (gate) {
            RequireActive();
            Require(Phase == BaiReadinessPhase.AdjustmentOnly, "REJECT_WRONG_PHASE");
            Require(evidence != null && evidence.FixedSettings.State == "ATTESTED_FIXED" &&
                evidence.FixedSettings.CurrentnessState == "CURRENT",
                "REJECT_ATTESTATION_MISSING");
            RequireTick(tick);
            Require(settingsEpochCount < BaiReadinessLimits.MaxSettingsEpochs,
                "REJECT_LIMIT_REACHED");
            var admittedEpoch = BaiReadinessAdmission.RequireId(newEpochId);
            var admittedCommand = BaiReadinessAdmission.RequireId(commandId);
            Require(!epochIds.Contains(admittedEpoch), "REJECT_WRONG_EPOCH");
            Require(!commandIds.Contains(admittedCommand), "REJECT_INVALID_COMMAND");
            var preparedEpoch = new BaiReadinessSettingsEpoch(admittedEpoch, admittedCommand,
                cursor, tick, evidence);
            preparedEpoch.Evidence.ValidateForFreeze(admission.SubjectBindingSha256, admittedCommand, tick);
            RequireOptionalSlot(tick);
            epochIds.Add(admittedEpoch);
            commandIds.Add(admittedCommand);
            epochId = admittedEpoch;
            AppendEvent(admittedCommand, tick, cursor, admittedEpoch, null,
                "SETTINGS_FROZEN", null);
            currentEpoch = preparedEpoch;
            settingsEpochs.Add(currentEpoch);
            settingsEpochCount++;
            lastEffectiveTick = tick;
            checked { measurementToken++; }
            Phase = BaiReadinessPhase.Frozen;
        }
    }

    internal void StartWindow(BaiReadinessWindowPurpose purpose, string windowId,
        string commandId, long tick)
    {
        lock (gate) {
            RequireActive();
            Require(windows.Count < BaiReadinessLimits.MaxWindows, "REJECT_LIMIT_REACHED");
            RequireTick(tick);
            if (purpose == BaiReadinessWindowPurpose.RoomTone)
                Require(Phase == BaiReadinessPhase.Frozen, "REJECT_WRONG_PHASE");
            else
                Require(Phase == BaiReadinessPhase.RoomToneClosed, "REJECT_WRONG_PHASE");
            var admittedWindow = BaiReadinessAdmission.RequireId(windowId);
            var admittedCommand = BaiReadinessAdmission.RequireId(commandId);
            Require(!windowIds.Contains(admittedWindow), "REJECT_INVALID_COMMAND");
            Require(!commandIds.Contains(admittedCommand), "REJECT_INVALID_COMMAND");
            RequireOptionalSlot(tick);
            windowIds.Add(admittedWindow);
            commandIds.Add(admittedCommand);
            var startEvent = AppendEvent(admittedCommand, tick, cursor, epochId,
                admittedWindow, purpose == BaiReadinessWindowPurpose.RoomTone ?
                    "ROOM_TONE_STARTED" : "NORMAL_SPEECH_STARTED", null);
            openWindow = new BaiReadinessWindow(
                admittedWindow, epochId, purpose, cursor, tick, admittedCommand,
                startEvent.EventId, channelCount);
            windows.Add(openWindow);
            lastEffectiveTick = tick;
            checked { measurementToken++; }
            Phase = purpose == BaiReadinessWindowPurpose.RoomTone
                ? BaiReadinessPhase.RoomToneOpen : BaiReadinessPhase.NormalSpeechOpen;
        }
    }

    internal void EndWindow(string commandId, long tick)
    {
        lock (gate) {
            RequireActive();
            Require(openWindow != null && openWindow.IsOpen, "REJECT_WRONG_PHASE");
            RequireTick(tick);
            var admittedCommand = BaiReadinessAdmission.RequireId(commandId);
            Require(!commandIds.Contains(admittedCommand), "REJECT_INVALID_COMMAND");
            RequireOptionalSlot(tick);
            commandIds.Add(admittedCommand);
            var purpose = openWindow.Purpose;
            var closeEvent = AppendEvent(admittedCommand, tick, cursor, epochId,
                openWindow.WindowId, purpose == BaiReadinessWindowPurpose.RoomTone ?
                    "ROOM_TONE_ENDED" : "NORMAL_SPEECH_ENDED", null);
            openWindow.Close(admittedCommand, cursor, tick, false, closeEvent.EventId);
            openWindow = null;
            lastEffectiveTick = tick;
            checked { measurementToken++; }
            Phase = purpose == BaiReadinessWindowPurpose.RoomTone
                ? BaiReadinessPhase.RoomToneClosed : BaiReadinessPhase.PairClosed;
        }
    }

    internal BaiReadinessPacketScan ScanPacket(byte[] payload, int frames, int planes)
    {
        long token;
        lock (gate) token = measurementToken;
        return BaiReadinessPacketScan.Create(payload, frames, planes, channelCount, token);
    }

    internal bool CommitPacket(
        ulong sequence, ulong timestamp, int frames, int planes, byte[] payload, long commitTick)
    {
        BaiReadinessPacketScan scan;
        try { scan = ScanPacket(payload, frames, planes); }
        catch (InvalidOperationException ex) when (ex.Message == "FORMAT_DRIFT" ||
            ex.Message == "INVALID_HEADER") {
            lock (gate) {
                if (!admissionOpen || Lifecycle != BaiReadinessLifecycle.Active) {
                    checked { DiscardedAfterRevocation++; }
                    return false;
                }
                RequireTick(commitTick);
                checked { InvalidHeaders++; }
                RequestStopUnderGate(ex.Message, null, commitTick, true);
                return false;
            }
        }
        return CommitScannedPacket(sequence, timestamp, scan, commitTick);
    }

    internal bool CommitScannedPacket(
        ulong sequence, ulong timestamp, BaiReadinessPacketScan scan, long commitTick)
    {
        lock (gate) {
            checked { AuthenticatedPackets++; }
            if (!admissionOpen || Lifecycle != BaiReadinessLifecycle.Active) {
                checked { DiscardedAfterRevocation++; }
                return false;
            }
            RequireTick(commitTick);
            if (scan == null) {
                checked { InvalidHeaders++; }
                RequestStopUnderGate("INVALID_HEADER", null, commitTick, true);
                return false;
            }
            if (scan.MeasurementToken != measurementToken) {
                checked { DiscardedOnTokenChange++; }
                return false;
            }
            if (sequenceAnchored) {
                if (sequenceExhausted || sequence < expectedSequence) {
                    checked { SequenceOrderErrors++; }
                    RequestStopUnderGate("SEQUENCE_ORDER_ERROR", null, commitTick, true);
                    return false;
                }
                if (sequence > expectedSequence) {
                    checked { SequenceGapEvents++; }
                    ulong gap = sequence - expectedSequence;
                    long room = BaiReadinessLimits.MaxExactJsonInteger - MissingPacketsLowerBound;
                    MissingPacketsLowerBound += gap > (ulong)room ? room : (long)gap;
                    RequestStopUnderGate("SEQUENCE_GAP", null, commitTick, true);
                    return false;
                }
            }
            if (timestampAnchored && timestamp < previousTimestamp) {
                checked { SourceTimestampRegressions++; }
                RequestStopUnderGate("SOURCE_TIMESTAMP_REGRESSION", null, commitTick, true);
                return false;
            }
            if (cursor > BaiReadinessLimits.MaxExactJsonInteger - scan.Frames) {
                RequestStopUnderGate("RESOURCE_LIMIT", null, commitTick, true);
                return false;
            }
            if (openWindow != null) openWindow.AddPacket(scan, sequence);
            checked { cursor += scan.Frames; CommittedPackets++; }
            if (!firstSequence.HasValue) firstSequence = sequence;
            lastSequence = sequence;
            if (!firstSourceTimestamp.HasValue) firstSourceTimestamp = timestamp;
            lastSourceTimestamp = timestamp;
            inputSeen = true;
            if (sequence == UInt64.MaxValue) sequenceExhausted = true;
            else expectedSequence = sequence + 1;
            previousTimestamp = timestamp;
            sequenceAnchored = timestampAnchored = true;
            lastEffectiveTick = commitTick;
            if (scan.HasNonfinite) {
                checked { NonfinitePackets++; }
                RequestStopUnderGate("NONFINITE_INPUT", null, commitTick, true);
            }
            return true;
        }
    }

    internal void ObserveSettingsChanged(string commandId, long tick)
    {
        lock (gate) {
            RequireActive();
            Require(Phase != BaiReadinessPhase.AdjustmentOnly, "REJECT_WRONG_PHASE");
            RequireTick(tick);
            var admittedCommand = BaiReadinessAdmission.RequireId(commandId);
            Require(!commandIds.Contains(admittedCommand), "REJECT_INVALID_COMMAND");
            RequireOptionalSlot(tick);
            commandIds.Add(admittedCommand);
            string affectedEpoch = epochId;
            string affectedWindow = openWindow != null && openWindow.IsOpen
                ? openWindow.WindowId : null;
            var changed = AppendEvent(admittedCommand, tick, cursor, affectedEpoch,
                affectedWindow, "SETTINGS_CHANGED", null);
            if (currentEpoch != null) currentEpoch.Invalidate(changed.EventId);
            foreach (var window in windows) if (window.EpochId == affectedEpoch)
                window.Invalidate(changed.EventId, window.IsOpen, false);
            if (openWindow != null && openWindow.IsOpen)
                openWindow.Close(null, cursor, tick, true, changed.EventId);
            openWindow = null;
            epochId = null;
            currentEpoch = null;
            lastEffectiveTick = tick;
            checked { measurementToken++; }
            Phase = BaiReadinessPhase.AdjustmentOnly;
        }
    }

    internal void ReportObservation(string windowId, string commandId, long tick, bool redIndicator)
    {
        lock (gate) {
            RequireActive(); RequireTick(tick);
            var window = FindWindow(windowId);
            Require(window != null || openWindow == null, "REJECT_INVALID_COMMAND");
            string command = BaiReadinessAdmission.RequireId(commandId);
            Require(!commandIds.Contains(command), "REJECT_INVALID_COMMAND");
            RequireOptionalSlot(tick);
            AppendEvent(command, tick, cursor, window == null ? epochId : window.EpochId,
                window == null ? null : window.WindowId,
                redIndicator ? "OWNER_RED_REPORT" : "OWNER_DISTORTION_REPORT", null);
            commandIds.Add(command);
            if (window != null) window.Report(redIndicator);
            lastEffectiveTick = tick;
        }
    }

    internal void WithdrawWindow(string windowId, string commandId, long tick)
    {
        lock (gate) {
            RequireActive(); RequireTick(tick);
            var window = FindWindow(windowId);
            Require(window != null && window.CurrentnessState != "WITHDRAWN", "REJECT_WRONG_PHASE");
            string command = BaiReadinessAdmission.RequireId(commandId);
            Require(!commandIds.Contains(command), "REJECT_INVALID_COMMAND");
            RequireOptionalSlot(tick);
            var withdrawn = AppendEvent(command, tick, cursor, window.EpochId,
                window.WindowId, "WINDOW_WITHDRAWN", null);
            commandIds.Add(command);
            window.Invalidate(withdrawn.EventId, window.IsOpen, true);
            if (window.IsOpen) {
                window.Close(null, cursor, tick, true, withdrawn.EventId);
                openWindow = null;
                Phase = BaiReadinessPhase.PairClosed;
                checked { measurementToken++; }
            }
            lastEffectiveTick = tick;
        }
    }

    private BaiReadinessWindow FindWindow(string windowId)
    {
        if (windowId == null) return null;
        foreach (var window in windows) if (window.WindowId == windowId) return window;
        throw new InvalidOperationException("REJECT_WRONG_EPOCH");
    }

    internal void ObserveConnectionAttempt(long tick)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Arming && admissionOpen, "LIFECYCLE");
            RequireTick(tick);
            Require(ConnectionAttempts == 0, "RECONNECT_PROHIBITED");
            ConnectionAttempts++;
            lastEffectiveTick = tick;
        }
    }

    internal void ObserveTransportFault(string reason, long tick)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Arming ||
                Lifecycle == BaiReadinessLifecycle.Active, "LIFECYCLE");
            RequireTick(tick);
            switch (reason) {
                case "INCOMPLETE_PACKET": IncompletePackets++; break;
                case "HMAC_FAILURE": HmacFailures++; break;
                case "NONCE_DRIFT": NonceMismatches++; break;
                case "INVALID_HEADER": InvalidHeaders++; break;
                case "PIPE_CLOSED": case "PIPE_FAILURE": break;
                default: throw new InvalidOperationException("REJECT_INVALID_COMMAND");
            }
            RequestStopUnderGate(reason, null, tick, true);
        }
    }

    internal void ObserveWatchdog(long tick)
    {
        lock (gate) {
            if (!admissionOpen) return;
            RequireTick(tick);
            Require(tick >= lastWatchdogTick, "REJECT_INVALID_COMMAND");
            long watchdogLimit = MillisecondsToTicks(
                BaiReadinessLimits.WatchdogMaxIntervalMilliseconds);
            if (tick - lastWatchdogTick > watchdogLimit) {
                RequestStopUnderGate("WATCHDOG_OVERRUN", null, tick, true);
                return;
            }
            lastWatchdogTick = tick;
            lastEffectiveTick = tick;
            if (tick - startTick >= MillisecondsToTicks(BaiReadinessLimits.HardCapMilliseconds)) {
                RequestStopUnderGate("HARD_CAP_REACHED", null, tick, true);
                return;
            }
            if (Lifecycle == BaiReadinessLifecycle.Arming &&
                tick - startTick >= MillisecondsToTicks(BaiReadinessLimits.ArmBudgetMilliseconds)) {
                RequestStopUnderGate("ARM_TIMEOUT", null, tick, true);
                return;
            }
            if (Lifecycle == BaiReadinessLifecycle.Active && !inputSeen &&
                tick - armedTick >= MillisecondsToTicks(BaiReadinessLimits.NoInputBudgetMilliseconds))
                RequestStopUnderGate("NO_INPUT_TIMEOUT", null, tick, true);
        }
    }

    internal void RequestStop(string reason, long tick)
    {
        RequestStop(reason, reason == "OWNER_STOP" ? "stop-" + OperationId : null, tick);
    }

    internal void RequestStop(string reason, string ownerCommandId, long tick)
    {
        lock (gate) {
            RequireStopReason(reason);
            if (!admissionOpen && stopReason != null) {
                ObserveSecondaryStop(reason, tick);
                return;
            }
            RequireTick(tick);
            if (reason == "OWNER_STOP") {
                ownerCommandId = BaiReadinessAdmission.RequireId(ownerCommandId);
                Require(commandIds.Add(ownerCommandId), "REJECT_INVALID_COMMAND");
            } else Require(ownerCommandId == null, "REJECT_INVALID_COMMAND");
            RequestStopUnderGate(reason, ownerCommandId, tick, true);
        }
    }

    internal void InvalidateCurrentness(string reason, long tick)
    {
        lock (gate) {
            Require(IsCurrentnessStopReason(reason), "REJECT_INVALID_COMMAND");
            if (stopReason != null) { ObserveSecondaryStop(reason, tick); return; }
            RequireActive();
            RequireTick(tick);
            // Fence before optional bookkeeping. A full ledger must never defeat
            // an authority revocation; its mandatory revoke event remains sufficient.
            FenceAdmission();
            if (events.Count >= BaiReadinessLimits.MaxEvents - 3) {
                RequestStopUnderGate(reason, null, tick, true);
                return;
            }
            string affectedEpoch = epochId;
            string affectedWindow = openWindow != null && openWindow.IsOpen
                ? openWindow.WindowId : null;
            var invalidated = AppendEvent(null, tick, cursor, affectedEpoch,
                affectedWindow, "CURRENTNESS_INVALIDATED", reason);
            ApplyEpochInvalidation(invalidated.EventId, affectedEpoch);
            if (openWindow != null && openWindow.IsOpen) {
                openWindow.Close(null, cursor, tick, true, invalidated.EventId);
                openWindow = null;
            }
            RequestStopUnderGate(reason, null, tick, true);
        }
    }

    internal void MarkSettling()
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Revoking, "LIFECYCLE");
            Lifecycle = BaiReadinessLifecycle.Settling;
        }
    }

    internal void MarkStopPending()
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Revoking ||
                Lifecycle == BaiReadinessLifecycle.Settling, "LIFECYCLE");
            Lifecycle = BaiReadinessLifecycle.StopPending;
        }
    }

    internal void MarkSettled(long tick)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Revoking ||
                Lifecycle == BaiReadinessLifecycle.Settling ||
                Lifecycle == BaiReadinessLifecycle.StopPending, "LIFECYCLE");
            Require(tick >= revokeTick && tick <= BaiReadinessLimits.MaxExactJsonInteger,
                "REJECT_INVALID_COMMAND");
            settledTick = tick;
            AppendEvent(null, tick, cursor, null, null, "RECEIVER_SETTLED", null, true);
            lastEffectiveTick = tick;
            Lifecycle = BaiReadinessLifecycle.Settled;
        }
    }

    private void RequestStopUnderGate(string reason, string ownerCommandId, long tick,
        bool interruptOpenWindow)
    {
        RequireStopReason(reason);
        if (stopReason != null) {
            ObserveSecondaryStop(reason, tick);
            return;
        }
        stopReason = reason;
        stopRequestTick = tick;
        FenceAdmission();
        RejectPendingCommandsBeforeStop(tick);
        AppendEvent(ownerCommandId, tick, cursor, null, null, "STOP_REQUESTED", reason, true);
        Lifecycle = BaiReadinessLifecycle.Revoking;
        revokeTick = tick;
        var revoked = AppendEvent(null, tick, cursor, null, null,
            "REVOCATION_LINEARIZED", null, true);
        revocationEventId = revoked.EventId;
        ApplyGlobalRevocationIfRequired();
        if (interruptOpenWindow && openWindow != null && openWindow.IsOpen) {
            interruptedAtRevoke = true;
            openWindow.Close(null, cursor, tick, true, revoked.EventId);
            openWindow = null;
        }
        lastEffectiveTick = Math.Max(lastEffectiveTick, tick);
    }

    private void ObserveSecondaryStop(string reason, long tick)
    {
        Require(terminalProjection == null, "TERMINAL_ALREADY_FROZEN");
        RequireTick(tick);
        if (!String.Equals(stopReason, reason, StringComparison.Ordinal))
            secondaryStopReasons.Add(reason);
        ApplyGlobalRevocationIfRequired();
    }

    private void ApplyGlobalRevocationIfRequired()
    {
        if (globalRevocationApplied || revocationEventId == null) return;
        bool required = IsCurrentnessStopReason(stopReason);
        foreach (var reason in secondaryStopReasons) required |= IsCurrentnessStopReason(reason);
        if (!required) return;
        ApplyAllEpochInvalidation(revocationEventId);
        globalRevocationApplied = true;
    }

    internal BaiReadinessTerminalProjection FreezeTerminalProjection()
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Settled && stopReason != null &&
                terminalProjection == null,
                "TERMINAL_BEFORE_SETTLEMENT");
            terminalProjection = new BaiReadinessTerminalProjection(OperationId, SessionId,
                monotonicFrequency, startTick, stopRequestTick, revokeTick, settledTick,
                stopReason, new List<string>(secondaryStopReasons).AsReadOnly(),
                interruptedAtRevoke, AuthenticatedPackets, CommittedPackets, cursor,
                InvalidHeaders, SequenceOrderErrors, SourceTimestampRegressions,
                ConnectionAttempts, IncompletePackets, HmacFailures, NonceMismatches,
                SequenceGapEvents, MissingPacketsLowerBound, DiscardedAfterRevocation,
                DiscardedOnTokenChange, firstSequence, lastSequence,
                firstSourceTimestamp, lastSourceTimestamp,
                new List<BaiReadinessEventRecord>(events).AsReadOnly(),
                new List<BaiReadinessSettingsEpoch>(settingsEpochs).AsReadOnly(),
                new List<BaiReadinessWindow>(windows).AsReadOnly());
            return terminalProjection;
        }
    }

    internal Task BeginPublicationAsync(BaiReadinessReceipt receipt,
        BaiReadinessMetadataSinkCapability sink)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Settled && publicationTask == null &&
                receipt != null && receipt.IsFrom(terminalProjection) && sink != null,
                "PUBLICATION_OWNERSHIP");
            Lifecycle = BaiReadinessLifecycle.Publishing;
            PublicationOutcome = BaiReadinessPublicationOutcome.InProgress;
            var deadline = Task.Delay(BaiReadinessLimits.MetadataPublicationBudgetMilliseconds);
            publicationTask = Task.Run(() => sink.Publish(receipt));
            publicationCompletion = ObservePublicationAsync(publicationTask, deadline, receipt, sink);
            return publicationCompletion;
        }
    }

    internal Task BeginPreparedPublicationAsync(IDictionary<string, object> staticContext,
        BaiReadinessMetadataSinkCapability sink)
    {
        lock (gate) {
            Require(Lifecycle == BaiReadinessLifecycle.Settled && publicationTask == null,
                "PUBLICATION_OWNERSHIP");
            var projection = FreezeTerminalProjection();
            Lifecycle = BaiReadinessLifecycle.Publishing;
            PublicationOutcome = BaiReadinessPublicationOutcome.InProgress;
            var deadline = Task.Delay(BaiReadinessLimits.MetadataPublicationBudgetMilliseconds);
            try {
                // Preparation/validation and no-artifact proof precede every sink task.
                publicationTask = BaiReadinessMetadataSinkCapability.PublicationResult.StartPrepared(
                    sink, projection, staticContext);
            } catch {
                SetMetadataUnconfirmed("IO_OUTCOME_UNKNOWN");
                publicationCompletion = Task.FromResult(false);
                return publicationCompletion;
            }
            publicationCompletion = ObservePublicationAsync(publicationTask, deadline, null, sink);
            return publicationCompletion;
        }
    }

    private async Task ObservePublicationAsync(
        Task<BaiReadinessMetadataSinkCapability.PublicationResult> ownedTask, Task deadline,
        BaiReadinessReceipt receipt, BaiReadinessMetadataSinkCapability sink)
    {
        var completed = await Task.WhenAny(ownedTask, deadline).ConfigureAwait(false);
        if (!Object.ReferenceEquals(completed, ownedTask)) {
            lock (gate) SetMetadataUnconfirmed("PUBLICATION_TIMEOUT");
            // Keep the exact task and lease. Observe late faults, without upgrading
            // UNKNOWN or scheduling a retry; reconciliation is not bound in this unit.
            lock (gate) latePublicationObservation = ObserveLatePublicationAsync(ownedTask);
            return;
        }
        BaiReadinessMetadataSinkCapability.PublicationResult proof;
        try { proof = await ownedTask.ConfigureAwait(false); }
        catch { lock (gate) SetMetadataUnconfirmed("IO_OUTCOME_UNKNOWN"); return; }
        lock (gate) {
            if (Lifecycle != BaiReadinessLifecycle.Publishing) return;
            Require(Object.ReferenceEquals(ownedTask, publicationTask), "PUBLICATION_TASK_SUBSTITUTION");
            if (proof == null || (receipt != null ? !proof.BelongsTo(receipt, sink) :
                !proof.BelongsTo(terminalProjection, sink))) {
                SetMetadataUnconfirmed("IDENTITY_MISMATCH");
                return;
            }
            publicationProof = proof;
            PublicationOutcome = proof.Outcome;
            PublicationReason = proof.Reason;
            Lifecycle = proof.Outcome == BaiReadinessPublicationOutcome.Unknown ?
                BaiReadinessLifecycle.MetadataUnconfirmed : BaiReadinessLifecycle.Terminal;
        }
    }

    private void SetMetadataUnconfirmed(string reason)
    {
        PublicationOutcome = BaiReadinessPublicationOutcome.Unknown;
        PublicationReason = reason;
        Lifecycle = BaiReadinessLifecycle.MetadataUnconfirmed;
    }

    private static async Task ObserveLatePublicationAsync(Task ownedTask)
    {
        try { await ownedTask.ConfigureAwait(false); } catch { }
    }

    private void ApplyEpochInvalidation(string eventId, string affectedEpoch)
    {
        if (affectedEpoch == null) return;
        if (currentEpoch != null && currentEpoch.EpochId == affectedEpoch)
            currentEpoch.Invalidate(eventId);
        foreach (var window in windows) if (window.EpochId == affectedEpoch)
            window.Invalidate(eventId, window.IsOpen, false);
    }

    private void ApplyAllEpochInvalidation(string eventId)
    {
        foreach (var epoch in settingsEpochs) epoch.Invalidate(eventId);
        foreach (var window in windows) window.Invalidate(eventId,
            window.IsOpen || window.ClosureEventId == eventId, false);
    }

    private void FenceAdmission()
    {
        if (!admissionOpen) return;
        admissionOpen = false;
        checked { measurementToken++; }
    }

    private void RequireOptionalSlot(long tick)
    {
        if (events.Count < BaiReadinessLimits.MaxEvents - 3) return;
        RequestStopUnderGate("RESOURCE_LIMIT", null, tick, true);
        throw new InvalidOperationException("REJECT_LIMIT_REACHED");
    }

    private BaiReadinessEventRecord AppendEvent(string commandId, long tick, long frame,
        string eventEpochId, string eventWindowId, string code, string reason,
        bool terminal = false)
    {
        int limit = terminal ? BaiReadinessLimits.MaxEvents :
            BaiReadinessLimits.MaxEvents - 3;
        Require(events.Count < limit, "REJECT_LIMIT_REACHED");
        var item = new BaiReadinessEventRecord(
            "event-" + (events.Count + 1).ToString("D2"), commandId, tick, frame,
            eventEpochId, eventWindowId, code, reason);
        events.Add(item);
        return item;
    }

    private void RecordCommandRejected(BaiReadinessCommand command, string rejection,
        long? observedTick = null)
    {
        if (commandIds.Contains(command.CommandId) ||
            (!admissionOpen && !observedTick.HasValue)) return;
        long tick = observedTick.HasValue ? observedTick.Value :
            Math.Max(lastEffectiveTick, command.Tick);
        if (events.Count >= BaiReadinessLimits.MaxEvents - 3) {
            if (stopReason == null) RequestStopUnderGate("RESOURCE_LIMIT", null, tick, true);
            return;
        }
        commandIds.Add(command.CommandId);
        AppendEvent(command.CommandId, tick, cursor,
            null, null, "COMMAND_REJECTED", rejection);
        lastEffectiveTick = tick;
    }

    private void RejectPendingCommandsBeforeStop(long tick)
    {
        while (commandQueue.Count > 0) {
            var pending = commandQueue.Dequeue();
            queuedCommandIds.Remove(pending.CommandId);
            if (events.Count < BaiReadinessLimits.MaxEvents - 3)
                RecordCommandRejected(pending, "REJECT_ALREADY_STOPPING", tick);
        }
        lastEffectiveTick = Math.Max(lastEffectiveTick, tick);
    }

    private static string NormalizeCommandRejection(string value)
    {
        switch (value) {
            case "REJECT_WRONG_OPERATION": case "REJECT_WRONG_PHASE":
            case "REJECT_WRONG_EPOCH": case "REJECT_ALREADY_STOPPING":
            case "REJECT_QUEUE_FULL": case "REJECT_LIMIT_REACHED":
            case "REJECT_ATTESTATION_MISSING": case "REJECT_AUTHORITY_NOT_CURRENT":
            case "REJECT_INVALID_COMMAND": return value;
            default: return "REJECT_INVALID_COMMAND";
        }
    }

    private long MillisecondsToTicks(long milliseconds)
    {
        return checked(milliseconds * monotonicFrequency / 1000L);
    }

    private static bool IsCurrentnessStopReason(string reason)
    {
        switch (reason) {
            case "OBS_IDENTITY_DRIFT": case "SOURCE_BINDING_DRIFT": case "FORMAT_DRIFT":
            case "OWNER_REVOCATION": case "AUTHORIZATION_EXPIRED":
            case "AUTHORIZATION_CURRENTNESS_UNKNOWN":
            case "ENVIRONMENT_ATTESTATION_REVOKED": case "PIPE_CLOSED":
            case "PIPE_FAILURE": case "INVALID_HEADER": case "INCOMPLETE_PACKET":
            case "HMAC_FAILURE": case "NONCE_DRIFT": case "SEQUENCE_GAP":
            case "SEQUENCE_ORDER_ERROR": case "SOURCE_TIMESTAMP_REGRESSION": return true;
            default: return false;
        }
    }

    private void RequireActive()
    {
        Require(Lifecycle == BaiReadinessLifecycle.Active && admissionOpen, "REJECT_ALREADY_STOPPING");
    }

    private void RequireTick(long tick)
    {
        Require(tick >= lastEffectiveTick && tick <= BaiReadinessLimits.MaxExactJsonInteger,
            "REJECT_INVALID_COMMAND");
    }

    private static void RequireStopReason(string reason)
    {
        switch (reason) {
            case "OWNER_STOP": case "HARD_CAP_REACHED": case "OWNER_REVOCATION":
            case "AUTHORIZATION_EXPIRED": case "AUTHORIZATION_CURRENTNESS_UNKNOWN":
            case "FORM_CLOSE": case "OBS_IDENTITY_DRIFT": case "SOURCE_BINDING_DRIFT":
            case "FORMAT_DRIFT": case "ENVIRONMENT_ATTESTATION_REVOKED":
            case "ARM_TIMEOUT": case "NO_INPUT_TIMEOUT": case "WATCHDOG_OVERRUN":
            case "PIPE_CLOSED": case "PIPE_FAILURE": case "INVALID_HEADER":
            case "INCOMPLETE_PACKET": case "HMAC_FAILURE": case "NONCE_DRIFT":
            case "SEQUENCE_GAP": case "SEQUENCE_ORDER_ERROR":
            case "SOURCE_TIMESTAMP_REGRESSION": case "NONFINITE_INPUT":
            case "ARITHMETIC_OVERFLOW": case "RESOURCE_LIMIT":
            case "INTERNAL_INVARIANT_FAILURE": return;
            default: throw new InvalidOperationException("REJECT_INVALID_COMMAND");
        }
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
