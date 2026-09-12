using System;
using System.IO.Pipes;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;

internal enum BaiCaptureMode
{
    WavRecording,
    LegacyGainCheck,
    ReadinessMonitor
}

internal sealed class BaiCapturePacketLease : IDisposable
{
    private BaiCaptureOperation owner;

    internal BaiCapturePacketLease(BaiCaptureOperation operation)
    {
        owner = operation;
    }

    public void Dispose()
    {
        var operation = Interlocked.Exchange(ref owner, null);
        if (operation != null) operation.ReleasePacketLease();
    }
}

internal abstract class BaiCaptureOperation : IDisposable
{
    private readonly object commitGate = new object();
    private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
    private readonly byte[] sessionKey = new byte[32];
    private Task receiverTask;
    private Task teardownTask;
    private Task<bool> settlementTask;
    private NamedPipeServerStream pipe;
    private bool admitted = true;
    private bool settled;
    private int inFlight;
    private int stopRequested;
    private long generation = 1;

    protected BaiCaptureOperation(BaiCaptureMode mode, string operationId, string sessionId)
    {
        if (String.IsNullOrWhiteSpace(operationId)) throw new ArgumentException("operationId");
        if (String.IsNullOrWhiteSpace(sessionId)) throw new ArgumentException("sessionId");
        Mode = mode;
        OperationId = operationId;
        SessionId = sessionId;
        using (var random = RandomNumberGenerator.Create()) random.GetBytes(sessionKey);
    }

    internal BaiCaptureMode Mode { get; private set; }
    internal string OperationId { get; private set; }
    internal string SessionId { get; private set; }
    internal CancellationToken Token { get { return cancellation.Token; } }
    internal byte[] SessionKey { get { return sessionKey; } }
    internal long Generation { get { lock (commitGate) return generation; } }
    internal bool StopRequested { get { return Volatile.Read(ref stopRequested) != 0; } }
    internal bool IsSettled { get { lock (commitGate) return settled; } }
    internal int InFlightCount { get { lock (commitGate) return inFlight; } }
    internal bool IsRecording { get { return Mode == BaiCaptureMode.WavRecording; } }
    internal bool IsLegacyGain { get { return Mode == BaiCaptureMode.LegacyGainCheck; } }
    internal bool IsReadiness { get { return Mode == BaiCaptureMode.ReadinessMonitor; } }
    internal virtual bool HasRecordingSink { get { return false; } }
    internal virtual string MetadataPath { get { return null; } }
    internal virtual string PartialAudioPath { get { return null; } }
    internal virtual string FinalAudioPath { get { return null; } }

    internal static BaiCaptureOperation CreateRecording(
        string operationId, string sessionId, string partialPath, string finalPath)
    {
        return new BaiWavCaptureOperation(operationId, sessionId,
            new BaiRecordingSinkCapability(partialPath, finalPath));
    }

    internal static BaiCaptureOperation CreateLegacyGain(
        string operationId, string sessionId, string metadataPath)
    {
        return new BaiMetadataOnlyCaptureOperation(
            BaiCaptureMode.LegacyGainCheck, operationId, sessionId, metadataPath);
    }

    internal static BaiCaptureOperation CreateReadinessUnavailable(
        string operationId, string sessionId, string metadataPath)
    {
        return new BaiMetadataOnlyCaptureOperation(
            BaiCaptureMode.ReadinessMonitor, operationId, sessionId, metadataPath);
    }

    internal void AttachReceiver(Task receiver)
    {
        if (receiver == null) throw new ArgumentNullException("receiver");
        lock (commitGate) {
            if (receiverTask != null) throw new InvalidOperationException("Receiver already attached");
            if (!admitted) throw new InvalidOperationException("Operation already revoked");
            receiverTask = receiver;
        }
    }

    internal void RegisterPipe(NamedPipeServerStream ownedPipe)
    {
        lock (commitGate) {
            if (!admitted) throw new OperationCanceledException();
            pipe = ownedPipe;
        }
    }

    internal void ReleasePipe(NamedPipeServerStream ownedPipe)
    {
        lock (commitGate) {
            if (Object.ReferenceEquals(pipe, ownedPipe)) pipe = null;
        }
    }

    internal bool TryAcquirePacketLease(long observedGeneration, out BaiCapturePacketLease lease)
    {
        lock (commitGate) {
            if (!admitted || stopRequested != 0 || observedGeneration != generation) {
                lease = null;
                return false;
            }
            checked { inFlight++; }
            lease = new BaiCapturePacketLease(this);
            return true;
        }
    }

    internal void ReleasePacketLease()
    {
        lock (commitGate) {
            if (inFlight <= 0) throw new InvalidOperationException("Packet lease underflow");
            inFlight--;
            Monitor.PulseAll(commitGate);
        }
    }

    internal bool RequestStop()
    {
        bool first = Interlocked.Exchange(ref stopRequested, 1) == 0;
        if (first) {
            lock (commitGate) {
                admitted = false;
                checked { generation++; }
                Monitor.PulseAll(commitGate);
            }
        }
        return first;
    }

    internal Task<bool> BeginSettlementAsync(TimeSpan sharedBudget)
    {
        if (sharedBudget < TimeSpan.Zero) throw new ArgumentOutOfRangeException("sharedBudget");
        lock (commitGate) {
            if (stopRequested == 0 || admitted)
                throw new InvalidOperationException("Stop must linearize before settlement");
            if (settlementTask != null) return settlementTask;

            var receiver = receiverTask ?? Task.FromResult(0);
            // Create the single shared deadline before scheduling cancellation or handle disposal.
            var deadline = Task.Delay(sharedBudget);
            teardownTask = Task.Run((Action)SignalCancellationAndClosePipeCore);
            settlementTask = AwaitOwnedLeavesWithinDeadlineAsync(receiver, teardownTask, deadline);
            return settlementTask;
        }
    }

    private void SignalCancellationAndClosePipeCore()
    {
        try { cancellation.Cancel(); } catch (ObjectDisposedException) { }
        NamedPipeServerStream owned;
        lock (commitGate) owned = pipe;
        try { if (owned != null) owned.Dispose(); } catch { }
    }

    private async Task<bool> AwaitOwnedLeavesWithinDeadlineAsync(
        Task receiver, Task teardown, Task deadline)
    {
        var leaves = Task.WhenAll(ObserveLeafAsync(receiver), ObserveLeafAsync(teardown));
        var completed = await Task.WhenAny(leaves, deadline).ConfigureAwait(false);
        if (!Object.ReferenceEquals(completed, leaves)) return false;
        await leaves.ConfigureAwait(false);
        while (!MarkSettledIfNoInFlight()) {
            completed = await Task.WhenAny(Task.Delay(10), deadline).ConfigureAwait(false);
            if (Object.ReferenceEquals(completed, deadline)) return false;
        }
        return true;
    }

    internal async Task AwaitSettlementWithoutDeadlineAsync()
    {
        Task receiver, teardown;
        lock (commitGate) {
            if (settlementTask == null)
                throw new InvalidOperationException("Settlement was not started");
            receiver = receiverTask ?? Task.FromResult(0);
            teardown = teardownTask ?? Task.FromResult(0);
        }
        await ObserveLeafAsync(receiver).ConfigureAwait(false);
        await ObserveLeafAsync(teardown).ConfigureAwait(false);
        while (!MarkSettledIfNoInFlight()) await Task.Delay(10).ConfigureAwait(false);
    }

    private static async Task ObserveLeafAsync(Task leaf)
    {
        try { await leaf.ConfigureAwait(false); } catch { }
    }

    private bool MarkSettledIfNoInFlight()
    {
        lock (commitGate) {
            if (inFlight != 0) return false;
            settled = true;
            return true;
        }
    }

    internal virtual void WriteAudio(byte[] payload, int frames, int planes)
    {
        throw new InvalidOperationException("Recording sink capability absent");
    }

    internal virtual void CheckpointAudio() { }

    internal virtual void FinalizeAudioPrefix() { }

    internal virtual void AbandonAudioWriter() { }

    public virtual void Dispose()
    {
        SignalCancellationAndClosePipeCore();
        Array.Clear(sessionKey, 0, sessionKey.Length);
        cancellation.Dispose();
    }
}

internal sealed class BaiMetadataOnlyCaptureOperation : BaiCaptureOperation
{
    private readonly string metadataPath;

    internal BaiMetadataOnlyCaptureOperation(
        BaiCaptureMode mode, string operationId, string sessionId, string path)
        : base(mode, operationId, sessionId)
    {
        if (mode == BaiCaptureMode.WavRecording) throw new ArgumentException("Metadata-only mode required");
        metadataPath = path;
    }

    internal override string MetadataPath { get { return metadataPath; } }
}

internal sealed class BaiRecordingSinkCapability
{
    private readonly object gate = new object();
    private readonly string partialPath;
    private readonly string finalPath;
    private WaveFloatWriter writer;

    internal BaiRecordingSinkCapability(string partial, string final)
    {
        if (String.IsNullOrWhiteSpace(partial) || String.IsNullOrWhiteSpace(final))
            throw new ArgumentException("Recording paths required");
        partialPath = partial;
        finalPath = final;
    }

    internal string PartialPath { get { return partialPath; } }
    internal string FinalPath { get { return finalPath; } }

    internal void Write(byte[] payload, int frames, int planes)
    {
        lock (gate) {
            if (writer == null) writer = new WaveFloatWriter(partialPath, checked((ushort)planes), 48000);
            writer.WritePlanar(payload, frames, planes);
        }
    }

    internal void Checkpoint()
    {
        lock (gate) { if (writer != null) writer.Checkpoint(); }
    }

    internal void FinalizePrefix()
    {
        lock (gate) {
            if (writer != null) {
                writer.Dispose();
                writer = null;
            }
        }
    }

    internal void Abandon()
    {
        lock (gate) {
            if (writer != null) {
                writer.Dispose();
                writer = null;
            }
        }
    }
}

internal sealed class BaiWavCaptureOperation : BaiCaptureOperation
{
    private readonly BaiRecordingSinkCapability sink;

    internal BaiWavCaptureOperation(
        string operationId, string sessionId, BaiRecordingSinkCapability capability)
        : base(BaiCaptureMode.WavRecording, operationId, sessionId)
    {
        sink = capability ?? throw new ArgumentNullException("capability");
    }

    internal override bool HasRecordingSink { get { return true; } }
    internal override string PartialAudioPath { get { return sink.PartialPath; } }
    internal override string FinalAudioPath { get { return sink.FinalPath; } }
    internal override void WriteAudio(byte[] payload, int frames, int planes)
    {
        sink.Write(payload, frames, planes);
    }
    internal override void CheckpointAudio() { sink.Checkpoint(); }
    internal override void FinalizeAudioPrefix() { sink.FinalizePrefix(); }
    internal override void AbandonAudioWriter() { sink.Abandon(); }

    public override void Dispose()
    {
        sink.Abandon();
        base.Dispose();
    }
}
