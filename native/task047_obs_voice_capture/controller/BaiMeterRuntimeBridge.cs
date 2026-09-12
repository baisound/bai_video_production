// TASK-048 C1A source contract. Not compiled/native-verified until gated B/C.
// Metadata only: no PCM transport, Project writer, capture control or classifier.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

internal sealed class BaiMeterProtocolException : Exception
{
    internal BaiMeterProtocolException() : base("ERR_TASK048_C1_PROTOCOL_FAILURE") { }
}

internal sealed class BaiMeterFrame
{
    internal readonly ushort Type;
    internal readonly ulong Sequence;
    internal readonly byte[] Nonce, Body, Wire;
    internal BaiMeterFrame(ushort type, ulong sequence, byte[] nonce, byte[] body, byte[] wire)
    { Type = type; Sequence = sequence; Nonce = nonce; Body = body; Wire = wire; }
    public override string ToString() { return "BaiMeterFrame(metadata)"; }
}

internal static class BaiMeterProtocol
{
    internal const int MaxFrameBytes = 65536, MaxProofBytes = 49152;
    internal const ulong MaxInteger = 9007199254740991UL;
    internal const byte LegacyLossUnknown = 2;
    private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);

    internal static void Require(bool value) { if (!value) throw new BaiMeterProtocolException(); }
    internal static byte[] Slice(byte[] data, int offset, int count)
    {
        Require(data != null && offset >= 0 && count >= 0 && offset <= data.Length - count);
        byte[] result = new byte[count]; Buffer.BlockCopy(data, offset, result, 0, count); return result;
    }
    internal static ushort U16(byte[] data, int offset) { return BitConverter.ToUInt16(Slice(data, offset, 2), 0); }
    internal static uint U32(byte[] data, int offset) { return BitConverter.ToUInt32(Slice(data, offset, 4), 0); }
    internal static ulong U64(byte[] data, int offset) { return BitConverter.ToUInt64(Slice(data, offset, 8), 0); }
    internal static byte[] Hash(byte[] data) { using (SHA256 hash = SHA256.Create()) return hash.ComputeHash(data); }
    internal static bool Equal(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        int diff = 0; for (int i = 0; i < left.Length; i++) diff |= left[i] ^ right[i]; return diff == 0;
    }
    internal static byte[] Hex(string text)
    {
        Require(text != null && text.Length % 2 == 0);
        byte[] result = new byte[text.Length / 2];
        for (int i = 0; i < result.Length; i++) result[i] = Convert.ToByte(text.Substring(i * 2, 2), 16);
        return result;
    }
    internal static string HexText(byte[] data) { return BitConverter.ToString(data).Replace("-", "").ToLowerInvariant(); }
    internal static byte[] UuidBytes(Guid value)
    {
        byte[] result = Hex(value.ToString("N"));
        ValidateUuid(result, 0); return result; // RFC bytes, never Guid.ToByteArray().
    }
    internal static Guid GuidAt(byte[] data, int offset)
    {
        ValidateUuid(data, offset); return Guid.ParseExact(HexText(Slice(data, offset, 16)), "N");
    }
    private static void ValidateUuid(byte[] data, int offset)
    {
        byte[] id = Slice(data, offset, 16);
        Require((id[6] & 240) == 64 && (id[8] & 192) == 128);
    }
    private static void Count(ulong value, bool positive)
    { Require(value <= MaxInteger && (!positive || value > 0)); }
    private static void Zero(byte[] data, int start, int count)
    { Require(Slice(data, start, count).All(x => x == 0)); }
    private static string Text(byte[] data, int offset, int count)
    {
        byte[] bytes = Slice(data, offset, count);
        Require(!(bytes.Length >= 3 && bytes[0] == 239 && bytes[1] == 187 && bytes[2] == 191));
        string text = Utf8.GetString(bytes); Require(text.IndexOf('\0') < 0); return text;
    }
    private static void Metric(byte[] data, int stateOffset)
    {
        byte state = data[stateOffset]; Require(state <= 4);
        if (state != 0) { Zero(data, stateOffset + 1, 8); return; }
        double value = BitConverter.ToDouble(data, stateOffset + 1);
        Require(!Double.IsNaN(value) && !Double.IsInfinity(value)); // No dBFS clamp.
    }
    private static void Counts(byte[] data, int stateOffset, int slots)
    {
        byte state = data[stateOffset]; Require(state <= 2);
        if (state != 0) { Zero(data, stateOffset + 1, slots * 8); return; }
        for (int i = 0; i < slots; i++) Count(U64(data, stateOffset + 1 + i * 8), false);
        Require(U64(data, stateOffset + 1 + (slots - 1) * 8) <= U64(data, stateOffset + 1));
    }
    private static void ValidateBody(ushort type, byte[] b)
    {
        switch (type)
        {
            case 1:
                Require(b.Length >= 84); ValidateUuid(b, 0); Count(U64(b, 40), true);
                int i = U16(b, 80), p = U16(b, 82);
                Require(i >= 3 && i <= 64 && p >= 1 && p <= 8192 && b.Length == 84 + i + p);
                string project = Text(b, 84, i), root = Text(b, 84 + i, p);
                Require(System.Text.RegularExpressions.Regex.IsMatch(project, @"\A[a-z][a-z0-9-]{2,63}\z"));
                Require(System.Text.RegularExpressions.Regex.IsMatch(root, @"^[A-Z]:\\[^\\]+\\.+$"));
                Require(!root.EndsWith("\\", StringComparison.Ordinal) && root.IndexOf(':', 2) < 0);
                foreach (string part in root.Substring(3).Split('\\'))
                    Require(part.Length > 0 && part != "." && part != ".." && !part.EndsWith(" ", StringComparison.Ordinal)
                        && !part.EndsWith(".", StringComparison.Ordinal)
                        && !part.Any(c => c < 32 || "<>\"|?*".IndexOf(c) >= 0));
                break;
            case 2:
                Require(b.Length == 145);
                foreach (int offset in new int[] { 0, 16, 32, 48 }) ValidateUuid(b, offset);
                Count(U64(b, 64), true);
                Require(b[72] <= 1 && b[73] <= 1 && b[74] <= 2 && b[75] == 0);
                Counts(b, 76, 3); Counts(b, 101, 2);
                Metric(b, 118); Metric(b, 127); Metric(b, 136); break;
            case 3:
                Require(b.Length >= 60);
                ushort source = U16(b, 2); Require(source == 1 || source == 2 || source == 4);
                Count(U64(b, 4), true); ValidateUuid(b, 44);
                if (b[0] == 0)
                {
                    Require(b[1] == 0 && source == 1 && b.Length == 156);
                    Count(U64(b, 60), true); ValidateUuid(b, 124); ValidateUuid(b, 140);
                }
                else if (b[0] == 2) Require(b[1] >= 1 && b[1] <= 8 && b.Length == 60);
                else
                {
                    Require(b[0] == 1 && b[1] == 0 && source == 2 && b.Length >= 308);
                    foreach (int offset in new int[] { 60, 76, 92, 124, 140, 156 }) ValidateUuid(b, offset);
                    Count(U64(b, 108), true); Require(U64(b, 116) >= 1 && U64(b, 116) <= 65536);
                    Require(b[268] <= 5 && b[269] >= 1 && b[269] <= 17); Zero(b, 270, 2);
                    uint length = U32(b, 272);
                    Require(length >= 1 && length <= MaxProofBytes && b.Length == 308 + length);
                    byte[] proof = Slice(b, 308, (int)length);
                    Require(Equal(Hash(proof), Slice(b, 276, 32)));
                    Text(proof, 0, proof.Length); // Public P2 worker validates JSON/canonical self-digests.
                }
                break;
            case 4:
                Require(b.Length == 68);
                foreach (int offset in new int[] { 0, 16, 32, 48 }) ValidateUuid(b, offset);
                Require(b[64] >= 1 && b[64] <= 8 && b[65] <= 1); Zero(b, 66, 2); break;
            case 5:
                Require(b.Length == 20); ValidateUuid(b, 0);
                Require(b[16] >= 1 && b[16] <= 4); Zero(b, 17, 3); break;
            default: throw new BaiMeterProtocolException();
        }
    }
    internal static BaiMeterFrame Parse(byte[] data)
    {
        try
        {
            Require(BitConverter.IsLittleEndian && data != null && data.Length >= 52 && data.Length <= MaxFrameBytes);
            Require(U32(data, 0) == data.Length - 4 && U32(data, 0) >= 48);
            Require(Equal(Slice(data, 4, 4), new byte[] { 66, 86, 77, 49 }) && U16(data, 8) == 1);
            ushort type = U16(data, 10); ulong sequence = U64(data, 12); Count(sequence, true);
            byte[] nonce = Slice(data, 20, 32), body = Slice(data, 52, data.Length - 52);
            Require(nonce.Any(x => x != 0)); ValidateBody(type, body);
            return new BaiMeterFrame(type, sequence, nonce, body, (byte[])data.Clone());
        }
        catch (Exception) { throw new BaiMeterProtocolException(); }
    }
    internal static byte[] Encode(ushort type, ulong sequence, byte[] nonce, byte[] body)
    {
        try
        {
            Require(nonce != null && nonce.Length == 32 && body != null);
            using (MemoryStream stream = new MemoryStream())
            using (BinaryWriter writer = new BinaryWriter(stream))
            {
                writer.Write((uint)(48 + body.Length)); writer.Write(new byte[] { 66, 86, 77, 49 });
                writer.Write((ushort)1); writer.Write(type); writer.Write(sequence); writer.Write(nonce); writer.Write(body);
                byte[] data = stream.ToArray(); Parse(data); return data;
            }
        }
        catch (Exception) { throw new BaiMeterProtocolException(); }
    }
    internal static byte[] Read(Stream reader, Action<bool> partial)
    {
        byte[] prefix = new byte[4]; int read = reader.Read(prefix, 0, 4);
        if (read == 0) return null;
        partial(true);
        while (read < 4) { int n = reader.Read(prefix, read, 4 - read); Require(n > 0); read += n; }
        uint nbytes = U32(prefix, 0); Require(nbytes >= 48 && nbytes <= MaxFrameBytes - 4);
        byte[] frame = new byte[nbytes + 4]; Buffer.BlockCopy(prefix, 0, frame, 0, 4); read = 4;
        while (read < frame.Length)
        { int n = reader.Read(frame, read, frame.Length - read); Require(n > 0); read += n; }
        Parse(frame); partial(false); return frame;
    }
    internal static byte[] Invalidation(Guid selected, Guid session, Guid consumer, Guid view, byte reason, bool paused)
    {
        using (MemoryStream s = new MemoryStream())
        using (BinaryWriter w = new BinaryWriter(s))
        {
            w.Write(UuidBytes(selected)); w.Write(UuidBytes(session)); w.Write(UuidBytes(consumer)); w.Write(UuidBytes(view));
            w.Write(reason); w.Write((byte)(paused ? 1 : 0)); w.Write((ushort)0);
            byte[] body = s.ToArray(); ValidateBody(4, body); return body;
        }
    }
    internal static byte[] LegacyWindow(byte[] scalarBody)
    {
        Require(scalarBody != null && scalarBody.Length == 145);
        byte[] body = (byte[])scalarBody.Clone(); body[72] = 1; body[74] = LegacyLossUnknown;
        ValidateBody(2, body); return body;
    }
}

internal interface IBaiMeterClock { long Now { get; } long Frequency { get; } }
internal sealed class BaiMeterMonotonicClock : IBaiMeterClock
{
    public long Now { get { return Stopwatch.GetTimestamp(); } }
    public long Frequency { get { return Stopwatch.Frequency; } }
}
internal interface IBaiMeterOwnedWorker
{
    Stream Reader { get; } Stream Writer { get; }
    Stream StderrReader { get; }
    byte[] BootstrapSha256 { get; }
    // Implemented by the exact suspended-launch receipt. Never terminate OBS/Controller.
    void ClosePureWorker();
}
internal sealed class BaiMeterDisplay
{
    internal readonly bool Connected;
    internal readonly byte Band;
    internal readonly string Reason;
    internal BaiMeterDisplay(bool connected, byte band, string reason)
    { Connected = connected; Band = band; Reason = reason; }
    internal string Label
    {
        get { return new string[] { "適正判定 未確定", "目標未満", "目標範囲", "目標超過", "警告", "クリップ" }[Band]; }
    }
    internal const string ScopeLabel = "今回の観測窓に対する方針照合";
}
internal sealed class BaiMeterPending
{
    internal readonly byte[] Body;
    internal readonly long Observed;
    internal ulong Tx;
    internal BaiMeterPending(byte[] body, long observed) { Body = body; Observed = observed; }
}

internal sealed class BaiMeterRuntimeBridge : IDisposable
{
    private readonly object gate = new object();
    private readonly IBaiMeterOwnedWorker worker;
    private readonly IBaiMeterClock clock;
    private readonly BaiMeterFrame bootstrap;
    private readonly AutoResetEvent sendSignal = new AutoResetEvent(false);
    private readonly Dictionary<ulong, BaiMeterFrame> requests = new Dictionary<ulong, BaiMeterFrame>();
    private readonly HashSet<Guid> requestIds = new HashSet<Guid>();
    private BaiMeterPending current, pending, active;
    private byte[] queuedControl, runtimeEpoch, producerEpoch;
    private ulong controlTx, tx = 1, rx, lastP2Sequence;
    private Guid p2Consumer;
    private bool ready, closed, started;
    private long partialSince = -1, startTime;
    private byte band;
    private string reason = "NOT_CONNECTED";
    private Timer timer;

    internal BaiMeterRuntimeBridge(IBaiMeterOwnedWorker ownedWorker, byte[] sentBootstrap, IBaiMeterClock monotonicClock)
    {
        worker = ownedWorker; clock = monotonicClock; bootstrap = BaiMeterProtocol.Parse(sentBootstrap);
        BaiMeterProtocol.Require(bootstrap.Type == 1 && bootstrap.Sequence == 1 && clock.Frequency >= 4);
        BaiMeterProtocol.Require(BaiMeterProtocol.Equal(worker.BootstrapSha256, BaiMeterProtocol.Hash(sentBootstrap)));
        requests.Add(1, bootstrap);
    }
    internal void Start()
    {
        lock (gate)
        {
            BaiMeterProtocol.Require(!started && !closed); started = true; startTime = clock.Now;
        }
        Thread read = new Thread(ReadLoop); read.IsBackground = true; read.Name = "bvp-c1-read"; read.Start();
        Thread write = new Thread(WriteLoop); write.IsBackground = true; write.Name = "bvp-c1-write"; write.Start();
        Thread error = new Thread(StderrLoop); error.IsBackground = true; error.Name = "bvp-c1-stderr"; error.Start();
        timer = new Timer(Watchdog, null, 25, 25);
    }
    internal static bool Within(long observed, long now, long frequency)
    { return now >= observed && frequency >= 4 && (ulong)(now - observed) < (ulong)frequency / 4; }

    internal static BaiMeterDisplay ExpireWindow(BaiMeterDisplay display, bool hasCurrent,
        long observed, long now, long frequency)
    {
        if (hasCurrent && !Within(observed, now, frequency))
            return new BaiMeterDisplay(display.Connected, 0, "WINDOW_EXPIRED");
        return display; // Preserve disconnected/initial reasons when no window exists.
    }
    private void RefreshDisplayExpiry(long now)
    {
        // Called only while holding gate: band and reason change together.
        BaiMeterDisplay value = ExpireWindow(new BaiMeterDisplay(ready && !closed, band, reason),
            current != null, current == null ? 0 : current.Observed, now, clock.Frequency);
        band = value.Band; reason = value.Reason;
    }

    internal void OfferNativeV1(byte[] scalarWindowBody)
    {
        byte[] body = BaiMeterProtocol.LegacyWindow(scalarWindowBody); // Cannot accept a loss-promotion flag.
        BaiMeterProtocol.Require(BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(body, 0, 16),
            BaiMeterProtocol.Slice(bootstrap.Body, 0, 16)));
        long now = clock.Now;
        lock (gate)
        {
            if (closed) return;
            if (current != null && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(current.Body, 0, 64),
                    BaiMeterProtocol.Slice(body, 0, 64)))
                BaiMeterProtocol.Require(BaiMeterProtocol.U64(body, 64) > BaiMeterProtocol.U64(current.Body, 64));
            band = 0; reason = "WINDOW_PENDING";
            current = pending = new BaiMeterPending(body, now); // One pending latest; no queue growth.
        }
        Signal();
    }
    internal void Invalidate(Guid session, Guid consumer, Guid view, byte why, bool paused)
    {
        byte[] body = BaiMeterProtocol.Invalidation(BaiMeterProtocol.GuidAt(bootstrap.Body, 0),
            session, consumer, view, why, paused);
        lock (gate)
        {
            if (closed) return;
            band = 0; reason = "INVALIDATED"; pending = current = null;
            queuedControl = body; // Unsent control is latest-only; sequence minted by writer.
        }
        Signal();
    }
    internal BaiMeterDisplay Snapshot()
    {
        lock (gate)
        {
            RefreshDisplayExpiry(clock.Now);
            return new BaiMeterDisplay(ready && !closed, band, reason);
        }
    }
    private void Partial(bool value)
    { lock (gate) partialSince = value ? clock.Now : -1; }
    private void Signal()
    { try { sendSignal.Set(); } catch (ObjectDisposedException) { } }
    private void StderrLoop()
    {
        const int MaxStderrLineBytes = 80, MaxStderrSessionBytes = 4096;
        int line = 0, total = 0;
        try
        {
            while (true)
            {
                int value = worker.StderrReader.ReadByte(); if (value < 0) return;
                total++; BaiMeterProtocol.Require(total <= MaxStderrSessionBytes);
                if (value == 10)
                { BaiMeterProtocol.Require(line > 0); line = 0; FailClosed("WORKER_FAILURE"); return; }
                BaiMeterProtocol.Require(value == 95 || value >= 65 && value <= 90 || value >= 48 && value <= 57);
                line++; BaiMeterProtocol.Require(line <= MaxStderrLineBytes);
            }
        }
        catch (Exception) { FailClosed("WORKER_FAILURE"); }
        // Never retain or display stderr text.
    }
    private void Watchdog(object unused)
    {
        bool expired;
        lock (gate)
        {
            long now = clock.Now;
            RefreshDisplayExpiry(now);
            expired = !closed && ((!ready && (now < startTime || now - startTime >= clock.Frequency * 5))
                || (partialSince >= 0 && (now < partialSince || now - partialSince >= clock.Frequency)));
        }
        if (expired) FailClosed("TRANSPORT_TIMEOUT");
    }
    private void WriteLoop()
    {
        try
        {
            while (true)
            {
                sendSignal.WaitOne(50);
                byte[] outgoing = null;
                lock (gate)
                {
                    if (closed) return;
                    if (!ready) continue;
                    if (queuedControl != null && controlTx == 0)
                    {
                        outgoing = BaiMeterProtocol.Encode(4, ++tx, bootstrap.Nonce, queuedControl);
                        controlTx = tx; queuedControl = null; requests.Add(tx, BaiMeterProtocol.Parse(outgoing));
                    }
                    else if (active == null && controlTx == 0 && pending != null)
                    {
                        BaiMeterPending candidate = pending; pending = null;
                        if (!Within(candidate.Observed, clock.Now, clock.Frequency)) continue;
                        active = candidate; active.Tx = ++tx;
                        outgoing = BaiMeterProtocol.Encode(2, tx, bootstrap.Nonce, active.Body);
                        requests.Add(tx, BaiMeterProtocol.Parse(outgoing));
                    }
                    BaiMeterProtocol.Require(requests.Count <= 2);
                }
                if (outgoing != null)
                { worker.Writer.Write(outgoing, 0, outgoing.Length); worker.Writer.Flush(); }
            }
        }
        catch (Exception) { FailClosed("TRANSPORT_FAILURE"); }
        finally { sendSignal.Dispose(); }
    }
    private void ReadLoop()
    {
        try
        {
            while (true)
            {
                byte[] raw = BaiMeterProtocol.Read(worker.Reader, Partial);
                if (raw == null) { FailClosed("WORKER_EOF"); return; }
                AcceptResult(BaiMeterProtocol.Parse(raw));
            }
        }
        catch (Exception) { FailClosed("PROTOCOL_FAILURE"); }
    }
    private void AcceptResult(BaiMeterFrame frame)
    {
        // Large hash/UTF-8 checks were completed by Parse, outside the UI lock.
        byte[] b = frame.Body;
        BaiMeterProtocol.Require(frame.Type == 3 && BaiMeterProtocol.Equal(frame.Nonce, bootstrap.Nonce));
        lock (gate)
        {
            if (closed) return;
            BaiMeterProtocol.Require(frame.Sequence == rx + 1); rx = frame.Sequence;
            ulong sourceTx = BaiMeterProtocol.U64(b, 4);
            BaiMeterFrame source;
            BaiMeterProtocol.Require(requests.TryGetValue(sourceTx, out source));
            BaiMeterProtocol.Require(BaiMeterProtocol.U16(b, 2) == source.Type
                && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 12, 32), BaiMeterProtocol.Hash(source.Wire))
                && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 44, 16), BaiMeterProtocol.Slice(bootstrap.Body, 0, 16)));
            if (source.Type == 1)
            {
                if (b[0] == 2)
                {
                    BaiMeterProtocol.Require(b[1] == 1); // Exact legitimate bootstrap refusal.
                    requests.Remove(sourceTx);
                    FailClosed("BOOTSTRAP_REJECTED");
                    return;
                }
                BaiMeterProtocol.Require(b[0] == 0
                    && BaiMeterProtocol.U64(b, 60) == BaiMeterProtocol.U64(bootstrap.Body, 40)
                    && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 68, 32), BaiMeterProtocol.Slice(bootstrap.Body, 48, 32))
                    && BaiMeterProtocol.U64(b, 100) == BaiMeterProtocol.U64(bootstrap.Body, 16)
                    && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 108, 16), BaiMeterProtocol.Slice(bootstrap.Body, 24, 16)));
                runtimeEpoch = BaiMeterProtocol.Slice(b, 124, 16);
                producerEpoch = BaiMeterProtocol.Slice(b, 140, 16);
                ready = true; reason = "CONNECTED_NOT_CLASSIFIED"; requests.Remove(sourceTx);
            }
            else if (source.Type == 4)
            {
                BaiMeterProtocol.Require(b[0] == 2 && b[1] == 8 && sourceTx == controlTx);
                requests.Remove(sourceTx); controlTx = 0; band = 0; reason = "INVALIDATED";
                // ACK retires only the cancelled transport request, NOT the P2
                // evaluation/lease. A fresh WINDOW may get BUSY until worker drain.
                if (active != null) { requests.Remove(active.Tx); active = null; }
                if (source.Body[64] == 1 || source.Body[64] == 2 || source.Body[64] == 7)
                    throw new BaiMeterProtocolException();
            }
            else
            {
                BaiMeterProtocol.Require(source.Type == 2 && active != null && sourceTx == active.Tx);
                if (b[0] == 1)
                {
                    BaiMeterProtocol.Require(BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 60, 48),
                        BaiMeterProtocol.Slice(active.Body, 16, 48))
                        && BaiMeterProtocol.U64(b, 108) == BaiMeterProtocol.U64(active.Body, 64)
                        && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 140, 16), runtimeEpoch)
                        && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(b, 156, 16), producerEpoch));
                    Guid consumer = BaiMeterProtocol.GuidAt(b, 76), request = BaiMeterProtocol.GuidAt(b, 124);
                    if (consumer != p2Consumer) { p2Consumer = consumer; lastP2Sequence = 0; requestIds.Clear(); }
                    ulong p2Sequence = BaiMeterProtocol.U64(b, 116);
                    BaiMeterProtocol.Require(p2Sequence > lastP2Sequence && requestIds.Count < 65536 && requestIds.Add(request));
                    lastP2Sequence = p2Sequence;
                    if (Object.ReferenceEquals(current, active) && Within(active.Observed, clock.Now, clock.Frequency))
                    { band = b[268]; reason = "P2_REASON_" + b[269].ToString(System.Globalization.CultureInfo.InvariantCulture); }
                }
                else
                {
                    BaiMeterProtocol.Require(b[0] == 2 && b[1] >= 2 && b[1] <= 7);
                    band = 0; reason = "C1_STATUS_" + b[1].ToString(System.Globalization.CultureInfo.InvariantCulture);
                    if (b[1] == 2 || b[1] == 3 || b[1] == 6 || b[1] == 7) throw new BaiMeterProtocolException();
                }
                requests.Remove(sourceTx); active = null;
            }
        }
        Signal();
    }
    private void FailClosed(string code)
    {
        lock (gate)
        {
            if (closed) return; closed = true; ready = false; band = 0; reason = code;
            pending = current = null; requests.Clear(); queuedControl = null;
        }
        Signal();
        // Never block a capture/UI/emergency thread on pipe/process shutdown.
        ThreadPool.QueueUserWorkItem(delegate { try { worker.ClosePureWorker(); } catch (Exception) { } });
    }
    public void Dispose()
    {
        FailClosed("CLOSED");
        Timer previous = timer; if (previous != null) previous.Dispose();
        // Background pumps may still await owned worker EOF; no Thread.Abort/OBS kill.
    }
}

// Injected Windows operations are concretely bound by the separately gated
// packaged host. Each pin owns non-inheritable CreateFileW handles: image/runtime
// closure FILE_SHARE_READ only; ancestors READ|WRITE with no DELETE sharing.
internal sealed class BaiMeterImageIdentity
{
    internal string CanonicalImage;
    internal byte[] ImageFileId, ImageSha256;
    internal ulong Volume;
    internal IDisposable Pins;
}
internal sealed class BaiMeterProcessIdentity
{
    internal IntPtr Process, Thread;
    internal uint Pid, Session;
    internal long CreationTime;
    internal string ImagePath, Sid;
    internal byte[] ImageFileId;
    internal ulong ImageVolume;
    internal bool Elevated;
}
internal interface IBaiMeterWindowsOps
{
    // Must implement CreateFileW(OPEN_EXISTING, OPEN_REPARSE_POINT), exact
    // closure/ancestor pins and embedded same-build manifest verification.
    BaiMeterImageIdentity PinExactBundle();
    string CreateContainedUniqueRuntimeRoot();
    void CreatePrivatePipes();
    // InitializeProcThreadAttributeList + UpdateProcThreadAttributeList,
    // exactly PROC_THREAD_ATTRIBUTE_HANDLE_LIST with stdin/out/err child handles.
    void PrepareHandleList(uint attribute);
    BaiMeterProcessIdentity CreateProcessW(string application, uint flags, string runtimeRoot);
    BaiMeterProcessIdentity ObserveProcess(BaiMeterProcessIdentity receipt);
    void RevalidatePins(BaiMeterImageIdentity pins);
    void CheckCurrentUserSidSession(BaiMeterProcessIdentity child);
    void AssignOwnedWorkerJob(BaiMeterProcessIdentity child, uint flags, uint activeProcessLimit);
    uint ResumeThread(IntPtr thread);
    void WritePrivateBootstrap(byte[] bytes);
    void CloseParentCopiesOfChildPipeEndsAndAttributes();
    // On pre-resume failure only the returned exact owned process is terminated.
    // After resume only the pure-worker Job may terminate; Controller is untouched.
    void CleanupOwnedFailure(BaiMeterProcessIdentity child, bool resumeAttempted);
    IBaiMeterOwnedWorker CompleteOwnedWorker(BaiMeterProcessIdentity child, BaiMeterImageIdentity pins, string runtimeRoot, byte[] bootstrapHash);
}
internal static class BaiMeterSuspendedLauncher
{
    internal const uint CREATE_SUSPENDED = 0x4, EXTENDED_STARTUPINFO_PRESENT = 0x80000;
    internal const uint CREATE_UNICODE_ENVIRONMENT = 0x400, CREATE_NO_WINDOW = 0x08000000;
    internal const uint PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002;
    internal const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000, JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 8;
    internal static IBaiMeterOwnedWorker Launch(IBaiMeterWindowsOps ops, byte[] bootstrap)
    {
        BaiMeterFrame frame = BaiMeterProtocol.Parse(bootstrap);
        BaiMeterProtocol.Require(frame.Type == 1 && frame.Sequence == 1);
        BaiMeterImageIdentity image = null; BaiMeterProcessIdentity child = null;
        bool attemptedResume = false, success = false, childHandleOwned = false;
        try
        {
            image = ops.PinExactBundle();
            BaiMeterProtocol.Require(image != null && image.Pins != null && image.ImageSha256 != null
                && image.ImageSha256.Length == 32 && image.ImageFileId != null && image.ImageFileId.Length == 16);
            string runtime = ops.CreateContainedUniqueRuntimeRoot();
            ops.CreatePrivatePipes(); ops.PrepareHandleList(PROC_THREAD_ATTRIBUTE_HANDLE_LIST);
            child = ops.CreateProcessW(image.CanonicalImage,
                CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW, runtime);
            childHandleOwned = child != null && child.Process.ToInt64() > 0;
            BaiMeterProtocol.Require(childHandleOwned
                && child.Thread != IntPtr.Zero && child.Thread != new IntPtr(-1) && child.Pid != 0);
            ops.CloseParentCopiesOfChildPipeEndsAndAttributes();
            BaiMeterProcessIdentity observed = ops.ObserveProcess(child);
            ValidateIdentity(child, observed, image); ops.CheckCurrentUserSidSession(observed); ops.RevalidatePins(image);
            ops.AssignOwnedWorkerJob(child, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_ACTIVE_PROCESS, 1);
            BaiMeterProcessIdentity final = ops.ObserveProcess(child);
            ValidateIdentity(child, final, image);
            BaiMeterProtocol.Require(final.CreationTime == observed.CreationTime
                && final.Sid == observed.Sid && final.Session == observed.Session);
            attemptedResume = true;
            BaiMeterProtocol.Require(ops.ResumeThread(child.Thread) == 1);
            ops.WritePrivateBootstrap((byte[])bootstrap.Clone());
            IBaiMeterOwnedWorker result = ops.CompleteOwnedWorker(child, image, runtime, BaiMeterProtocol.Hash(bootstrap));
            BaiMeterProtocol.Require(result != null); success = true; return result;
        }
        catch (Exception) { throw new BaiMeterProtocolException(); }
        finally
        {
            if (!success)
            {
                // Backend retains pins/receipt if owned process exit is unconfirmed.
                try { ops.CleanupOwnedFailure(childHandleOwned ? child : null, attemptedResume); } catch (Exception) { }
            }
        }
    }
    private static void ValidateIdentity(BaiMeterProcessIdentity child, BaiMeterProcessIdentity observed, BaiMeterImageIdentity image)
    {
        BaiMeterProtocol.Require(observed != null && observed.Pid == child.Pid
            && observed.CreationTime > 0 && observed.ImagePath == image.CanonicalImage && !observed.Elevated
            && observed.ImageVolume == image.Volume && BaiMeterProtocol.Equal(observed.ImageFileId, image.ImageFileId));
    }
}

internal sealed class BaiMeterGolden
{
    internal readonly string Name, Digest, Bytes;
    internal readonly int Length;
    internal BaiMeterGolden(string name, int length, string digest, string bytes)
    { Name = name; Length = length; Digest = digest; Bytes = bytes; }
}
internal static class BaiMeterProtocolSelfTest
{
    // Literal independent design vectors. These are never Project/policy admission.
    internal static readonly BaiMeterGolden[] Vectors = new BaiMeterGolden[] {
        new BaiMeterGolden("BOOTSTRAP", 186, "0b7ec9a406d8f037817b15cb09727dce97fa986d0746411a828af2fb7a98c982", "b600000042564d31010001000100000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f000000000000400080000000000000060100000000000000111111111111111111111111111111110400000000000000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa0d0025006d657465722d70726f6a656374433a5c55736572735c6578616d706c655c446f63756d656e74735c63312d70726f6a656374"),
        new BaiMeterGolden("WINDOW", 197, "d0a487a835800ee4e46a5e12151a9fbb7b71f7cb15031035e23782a1882a9a21", "c100000042564d31010002000200000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f000000000000400080000000000000060000000000004000800000000000000100000000000040008000000000000002000000000000400080000000000000070100000000000000010000000001000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000032c00000000000000032c00000000000000032c0"),
        new BaiMeterGolden("INVALIDATE", 120, "54faa59d734159f75f1873922e6c0087d24a0fc93e748a640b92a606a594b165", "7400000042564d31010004000300000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0000000000004000800000000000000600000000000040008000000000000001000000000000400080000000000000080000000000004000800000000000000904010000"),
        new BaiMeterGolden("CLOSE", 72, "5929b9d7c39d7f37c7aa39e3e12d54ab70989fa31681ced0902fa657cf2ddca3", "4400000042564d31010005000400000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0000000000004000800000000000000601000000"),
        new BaiMeterGolden("RESULT_READY", 208, "b19f2a87777de9aa22eda6f40d6384bc3ac1908694fb705fe977e8a385969b85", "cc00000042564d31010003000100000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0000010001000000000000000b7ec9a406d8f037817b15cb09727dce97fa986d0746411a828af2fb7a98c982000000000000400080000000000000060400000000000000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa0100000000000000111111111111111111111111111111110000000000004000800000000000000400000000000040008000000000000005"),
        new BaiMeterGolden("RESULT_STATUS", 112, "8ad4e11ea9d42886198dcb5addf8ecddb27552f8ae38fa1d1998a9f7cd02a05e", "6c00000042564d31010003000300000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f02080400030000000000000054faa59d734159f75f1873922e6c0087d24a0fc93e748a640b92a606a594b16500000000000040008000000000000006"),
        new BaiMeterGolden("RESULT_PROJECTION", 3822, "16295d65b8b56d97ce55f15f39de0d7c0764f4b20661463d8c2a0c8b33672a8a", "ea0e000042564d31010003000200000000000000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f010002000200000000000000d0a487a835800ee4e46a5e12151a9fbb7b71f7cb15031035e23782a1882a9a2100000000000040008000000000000006000000000000400080000000000000010000000000004000800000000000000200000000000040008000000000000007010000000000000001000000000000000000000000004000800000000000000300000000000040008000000000000004000000000000400080000000000000050988969cd5eb0982ce6c21b9cf05d63d5bda92dafb8f161d7774a29bcd533730bfb0abc58ea59ef4821df2113b9a5c9d913765663df7e001deb1c399a72e506e02290e0a58ef1b031955286138c72626c3084c8ffd7df8b59b9a5e9b4548ba6502110000860d0000dcf406d1bd2506683add92eb3df1e93b8c686fe584ccf8dbcb8f338e0d02ad9d7b22617574686f72697479223a7b22617574686f726974795f63726561746564223a66616c73652c22636170747572655f617574686f72697a6564223a66616c73652c22636170747572655f706174685f6e6f6e696e746572666572656e63655f636f6e6669726d6564223a66616c73652c22636f6e73656e745f61737365745f747261696e696e675f6d6f64656c5f617574686f72697a6564223a66616c73652c22656d657267656e63795f73746f705f6e6f6e696e746572666572656e63655f636f6e6669726d6564223a66616c73652c226761696e5f6368616e67655f617574686f72697a6564223a66616c73652c2268617264776172655f6f725f6f62735f73657474696e675f6368616e676564223a66616c73652c2270726f64756374696f6e5f617574686f72697a6564223a66616c73652c2270726f76696465725f696e766f6b6564223a66616c73652c227175616c6974795f706173735f697373756564223a66616c73652c2274656d706f72616c5f66726573686e6573735f636f6e6669726d6564223a66616c73657d2c2263616e6f6e6963616c5f6f776e65725f7461736b223a225441534b2d303438222c22646973706c61795f62616e64223a22544152474554222c22696f5f626f756e64617279223a7b22617564696f5f73656d616e7469635f6465636f64655f6578656375746564223a66616c73652c22617564696f5f757365645f61735f706f6c6963795f696e707574223a66616c73652c22636170747572655f7472616e73706f72745f6170695f696e766f6b6564223a66616c73652c22656d657267656e63795f73746f705f6170695f696e766f6b6564223a66616c73652c22706f6c6963795f6f725f70726f6a6563745f77726974655f6578656375746564223a66616c73652c2270726f6a6563745f696e746567726974795f686173685f72656164735f706f737369626c65223a747275657d2c226c6976655f61646d697373696f6e5f73657269616c697a6564223a66616c73652c226f62736572766174696f6e223a7b2263616e6f6e6963616c5f6f776e65725f7461736b223a225441534b2d303438222c22636170747572655f706f696e74223a225441534b3034375f434f4e54524f4c4c45525f52454345495645445f464c4f415433325f5052455f44524157222c226f62736572766174696f6e5f736861323536223a227368613235363a30393838393639636435656230393832636536633231623963663035643633643562646139326461666238663136316437373734613239626364353333373330222c22706175736564223a66616c73652c2271756572795f636f6e74657874223a7b22636f6e73756d65725f65706f6368223a2230303030303030302d303030302d343030302d383030302d303030303030303030303032222c2270726f6a6563745f6964223a226d657465722d70726f6a656374222c22726571756573745f6964223a2230303030303030302d303030302d343030302d383030302d303030303030303030303033222c2273657373696f6e5f6964223a2230303030303030302d303030302d343030302d383030302d303030303030303030303031222c2277696e646f775f73657175656e6365223a317d2c227265636f72645f74797065223a225461736b3034384d6574657252756e74696d654f62736572766174696f6e5631222c22736368656d615f76657273696f6e223a312c2273657373696f6e5f636f756e7473223a7b22636c69705f73616d706c655f76616c756573223a302c2266696e6974655f73616d706c655f76616c756573223a312c227374617465223a2256414c4944227d2c2273657373696f6e5f7065616b223a7b227374617465223a2246494e495445222c2276616c75655f64626673223a2d31382e307d2c2277696e646f775f636f756e7473223a7b22636c69705f73616d706c655f76616c756573223a302c2266696e6974655f73616d706c655f76616c756573223a312c226e6f6e66696e6974655f73616d706c655f76616c756573223a302c227374617465223a2256414c4944227d2c2277696e646f775f6c6f73735f7374617465223a224e4f5f4c4f53535f5245504f52544544222c2277696e646f775f7065616b223a7b227374617465223a2246494e495445222c2276616c75655f64626673223a2d31382e307d2c2277696e646f775f726d73223a7b227374617465223a2246494e495445222c2276616c75655f64626673223a2d31382e307d7d2c226f62736572766174696f6e5f7374617465223a224d45415355524544222c226f70657261746f725f6c6162656c223a22e79baee6a899e7af84e59bb2222c22706f6c6963795f6f62736572766174696f6e223a7b226566666563746976655f737461747573223a2250524f4a4543545f484541445f4d4154434845445f534e415053484f54222c2266696e616c5f737461747573223a2250524f4a4543545f484541445f4d4154434845445f534e415053484f54222c226964656e74697479223a7b226368696c645f736861323536223a227368613235363a62626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262222c2270726f64756365725f65706f6368223a2230303030303030302d303030302d343030302d383030302d303030303030303030303035222c2270726f6a6563745f6964223a226d657465722d70726f6a656374222c2270726f6a6563745f6d616e69666573745f736861323536223a227368613235363a61616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161222c2270726f6a6563745f7265766973696f6e223a342c2273656c65637465645f706f6c6963795f736861323536223a227368613235363a62623736323565303236623631383836376163663539313435306435363936656338323563646364303962383862393733383039633930343564376433396265222c2273746174655f7265766973696f6e223a337d2c22696e697469616c5f737461747573223a2250524f4a4543545f484541445f4d4154434845445f534e415053484f54222c22706f6c6963795f646f63756d656e74223a7b2263616e6f6e6963616c5f6f776e65725f7461736b223a225441534b2d303438222c22706f6c6963795f726566223a226d657465722d706f6c696379222c22706f6c6963795f7265766973696f6e223a312c22706f6c6963795f7265766973696f6e5f736861323536223a227368613235363a62623736323565303236623631383836376163663539313435306435363936656338323563646364303962383862393733383039633930343564376433396265222c227072656465636573736f725f706f6c6963795f736861323536223a6e756c6c2c227265636f72645f74797065223a225461736b3034384d65746572446973706c6179506f6c6963795265766973696f6e5631222c22736368656d615f76657273696f6e223a312c227461726765745f6365696c696e675f64626673223a2d31322e302c227461726765745f666c6f6f725f64626673223a2d32342e302c22747275655f636c69705f64626673223a302e302c227761726e696e675f64626673223a2d332e307d2c2277696e646f775f706f6c6963795f6d617463686564223a747275657d2c22706f6c6963795f70726f64756365725f65706f6368223a2230303030303030302d303030302d343030302d383030302d303030303030303030303035222c2270726f6a656374696f6e5f736861323536223a227368613235363a30323239306530613538656631623033313935353238363133386337323632366333303834633866666437646638623539623961356539623435343862613635222c2271756572795f636f6e74657874223a7b22636f6e73756d65725f65706f6368223a2230303030303030302d303030302d343030302d383030302d303030303030303030303032222c2270726f6a6563745f6964223a226d657465722d70726f6a656374222c22726571756573745f6964223a2230303030303030302d303030302d343030302d383030302d303030303030303030303033222c2273657373696f6e5f6964223a2230303030303030302d303030302d343030302d383030302d303030303030303030303031222c2277696e646f775f73657175656e6365223a317d2c22726561736f6e5f636f6465223a2257494e444f575f504f4c4943595f434c4153534946494544222c227265636f72645f74797065223a225461736b3034384d6574657252756e74696d654465636973696f6e50726f6a656374696f6e5631222c22726571756573745f736861323536223a227368613235363a62666230616263353865613539656634383231646632313133623961356339643931333736353636336466376530303164656231633339396137326535303665222c2272756e74696d655f65706f6368223a2230303030303030302d303030302d343030302d383030302d303030303030303030303034222c22736368656d615f76657273696f6e223a312c2273636f70655f6c6162656c223a22e4bb8ae59b9ee381aee8a6b3e6b8ace7aa93e381abe5afbee38199e3828be696b9e9879de785a7e59088222c2277696e646f775f6f6e6c79223a747275657d"),
    };
    internal static int Run()
    {
        try
        {
            foreach (BaiMeterGolden vector in Vectors)
            {
                byte[] raw = BaiMeterProtocol.Hex(vector.Bytes);
                BaiMeterProtocol.Require(raw.Length == vector.Length
                    && BaiMeterProtocol.HexText(BaiMeterProtocol.Hash(raw)) == vector.Digest);
                BaiMeterFrame frame = BaiMeterProtocol.Parse(raw);
                BaiMeterProtocol.Require(BaiMeterProtocol.Equal(raw,
                    BaiMeterProtocol.Encode(frame.Type, frame.Sequence, frame.Nonce, frame.Body)));
                byte[] bad = (byte[])raw.Clone(); bad[4] ^= 1;
                bool rejected = false;
                try { BaiMeterProtocol.Parse(bad); } catch (BaiMeterProtocolException) { rejected = true; }
                BaiMeterProtocol.Require(rejected);
            }
            BaiMeterProtocol.Require(BaiMeterRuntimeBridge.Within(0, 249000000, 1000000000));
            BaiMeterProtocol.Require(!BaiMeterRuntimeBridge.Within(0, 250000000, 1000000000));
            BaiMeterProtocol.Require(!BaiMeterRuntimeBridge.Within(0, 251000000, 1000000000));
            long[] expiryBoundaries = new long[] { 249000000, 250000000, 251000000 };
            for (int i = 0; i < expiryBoundaries.Length; i++)
            {
                BaiMeterDisplay classified = new BaiMeterDisplay(true, 2, "P2_REASON_17");
                BaiMeterDisplay display = BaiMeterRuntimeBridge.ExpireWindow(classified,
                    true, 0, expiryBoundaries[i], 1000000000);
                BaiMeterProtocol.Require(display.Connected
                    && display.Band == (i == 0 ? 2 : 0)
                    && display.Reason == (i == 0 ? "P2_REASON_17" : "WINDOW_EXPIRED"));
            }
            foreach (string initialReason in new string[] { "CONNECTED_NOT_CLASSIFIED", "BOOTSTRAP_REJECTED" })
            {
                BaiMeterDisplay initial = new BaiMeterDisplay(initialReason == "CONNECTED_NOT_CLASSIFIED", 0, initialReason);
                BaiMeterProtocol.Require(Object.ReferenceEquals(initial,
                    BaiMeterRuntimeBridge.ExpireWindow(initial, false, 0, 251000000, 1000000000)));
            }
            BaiMeterFrame fixture = BaiMeterProtocol.Parse(BaiMeterProtocol.Hex(Vectors[1].Bytes));
            byte[] native = BaiMeterProtocol.LegacyWindow(fixture.Body);
            BaiMeterProtocol.Require(native[72] == 1 && native[74] == 2);
            return 0;
        }
        catch (Exception) { return 98; } // Fixed failure code, no payload/path/exception dump.
    }
}
