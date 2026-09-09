using System;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Any(x => x == "--meter-self-test")) return MeterObservationSelfTest.Run();
        if (args.Any(x => x == "--self-test")) return ControllerSelfTest.Run();
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new CaptureForm(args.Any(x => x == "--acceptance")));
        return 0;
    }
}

internal sealed class CaptureForm : Form
{
    private const string PipeName = "bai-voice-capture-v1";
    private readonly bool acceptanceMode;
    private readonly Label status = new Label();
    private readonly TextBox destination = new TextBox();
    private readonly TextBox obsExecutable = new TextBox();
    private readonly NumericUpDown maximumMinutes = new NumericUpDown();
    private readonly NumericUpDown diskFloorGb = new NumericUpDown();
    private readonly Label elapsed = new Label();
    private readonly Label written = new Label();
    private readonly Label freeSpace = new Label();
    private readonly Label packets = new Label();
    private readonly AudioLevelMeter levelMeter = new AudioLevelMeter();
    private readonly Label levelValues = new Label();
    private readonly Label detail = new Label();
    private readonly Button browse = new Button();
    private readonly Button browseObs = new Button();
    private readonly Button gainCheck = new Button();
    private readonly Button start = new Button();
    private readonly Button pause = new Button();
    private readonly Button resume = new Button();
    private readonly Button stop = new Button();
    private readonly System.Windows.Forms.Timer uiTimer = new System.Windows.Forms.Timer();
    private readonly object stateLock = new object();
    private readonly object metricLock = new object();
    private readonly ManualResetEventSlim resumeGate = new ManualResetEventSlim(true);

    private CancellationTokenSource cancellation;
    private NamedPipeServerStream pipe;
    private Process obs;
    private WaveFloatWriter wave;
    private byte[] sessionKey;
    private DateTime startedUtc;
    private long packetCount;
    private long payloadBytes;
    private long sequenceGaps;
    private long hmacFailures;
    private long reconnectCount;
    private long pauseCount;
    private long pauseBoundarySkippedSequences;
    private long receivedBytes;
    private long metricSampleCount;
    private long clipSampleCount;
    private long nonFiniteSampleCount;
    private double metricSumSquares;
    private readonly AudioMeterWindow meterWindow = new AudioMeterWindow();
    private string partialPath;
    private string finalPath;
    private string terminalReason;
    private volatile bool connected;
    private volatile bool recording;
    private volatile bool paused;
    private volatile bool sequenceReanchorPending;
    private volatile bool gainMeasurement;
    private volatile bool terminalStopRequested;
    private int stopStarted;
    private TimeSpan maximumDurationValue;
    private long diskFloorBytes;
    private DateTime pauseStartedUtc;
    private TimeSpan completedPauseDuration;
    private DateTime measurementStartedUtc;
    private string gainReceiptPath;
    private int obsProcessId;
    private bool obsReused;

    public CaptureForm(bool acceptance)
    {
        acceptanceMode = acceptance;
        Text = "BAI 学習データ録音コントローラ";
        TopMost = true;
        MinimumSize = new Size(720, 570);
        Size = new Size(820, 650);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;

        status.Text = "停止中";
        status.Font = new Font("Yu Gothic UI", 22F, FontStyle.Bold);
        status.TextAlign = ContentAlignment.MiddleCenter;
        status.BackColor = Color.FromArgb(70, 70, 70);
        status.ForeColor = Color.White;
        status.Dock = DockStyle.Top;
        status.Height = 70;

        var table = new TableLayoutPanel {
            Dock = DockStyle.Fill, ColumnCount = 3, RowCount = 12,
            Padding = new Padding(16), AutoSize = false
        };
        table.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 150));
        table.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        table.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 100));

        destination.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "BAI Voice Captures");
        destination.Dock = DockStyle.Fill;
        browse.Text = "参照...";
        browse.Dock = DockStyle.Fill;
        browse.Click += BrowseClicked;
        AddRow(table, 0, "保存先", destination, browse);

        var configuredObs = Environment.GetEnvironmentVariable("BAI_OBS_EXECUTABLE");
        var programFilesObs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "obs-studio", "bin", "64bit", "obs64.exe");
        obsExecutable.Text = !String.IsNullOrWhiteSpace(configuredObs) ? configuredObs : programFilesObs;
        obsExecutable.Dock = DockStyle.Fill;
        browseObs.Text = "参照...";
        browseObs.Dock = DockStyle.Fill;
        browseObs.Click += BrowseObsClicked;
        AddRow(table, 1, "OBS実行ファイル", obsExecutable, browseObs);

        maximumMinutes.Minimum = 1;
        maximumMinutes.Maximum = 120;
        maximumMinutes.Value = 90;
        maximumMinutes.Width = 120;
        AddRow(table, 2, "最大録音時間（分）", maximumMinutes, null);

        diskFloorGb.Minimum = 1;
        diskFloorGb.Maximum = 1024;
        diskFloorGb.Value = 20;
        diskFloorGb.Width = 120;
        AddRow(table, 3, "停止する空き容量（GB）", diskFloorGb, null);

        levelMeter.Height = 34;
        levelMeter.Dock = DockStyle.Fill;
        AddRow(table, 4, "入力レベル", levelMeter, null);
        levelValues.Text = "Peak -- / RMS -- / 最大 -- dBFS\n0 dBFS = デジタル上限 / 警告・適正判定 未確定";
        levelValues.AutoSize = true;
        levelValues.MaximumSize = new Size(520, 0);
        AddRow(table, 5, "測定値", levelValues, null);
        table.SetColumnSpan(levelValues, 2);
        AddRow(table, 6, "経過時間", elapsed, null);
        AddRow(table, 7, "保存済み", written, null);
        AddRow(table, 8, "保存先の空き容量", freeSpace, null);
        AddRow(table, 9, "受信状態", packets, null);

        detail.AutoSize = true;
        detail.MaximumSize = new Size(520, 0);
        detail.Text = acceptanceMode
            ? "合成音声Acceptanceモード。Owner音声は使用しません。"
            : "OBSを起動したままGAIN確認・録音・一時停止・再開・停止できます。停止時にWAVを確定します。";
        table.Controls.Add(new Label { Text = "説明", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 10);
        table.Controls.Add(detail, 1, 10);
        table.SetColumnSpan(detail, 2);

        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.LeftToRight };
        gainCheck.Text = "録音前GAINチェック（5秒・保存なし）";
        gainCheck.AutoSize = true;
        gainCheck.Padding = new Padding(12, 6, 12, 6);
        gainCheck.Click += GainCheckClicked;
        start.Text = "録音開始（OBS起動中でも可）";
        start.AutoSize = true;
        start.Padding = new Padding(12, 6, 12, 6);
        start.Click += StartClicked;
        pause.Text = "一時停止";
        pause.AutoSize = true;
        pause.Padding = new Padding(12, 6, 12, 6);
        pause.Enabled = false;
        pause.Click += delegate { PauseCapture(); };
        resume.Text = "再開";
        resume.AutoSize = true;
        resume.Padding = new Padding(12, 6, 12, 6);
        resume.Enabled = false;
        resume.Click += delegate { ResumeCapture(); };
        stop.Text = "録音停止";
        stop.AutoSize = true;
        stop.Padding = new Padding(12, 6, 12, 6);
        stop.Enabled = false;
        stop.Click += delegate { StopCapture(); };
        buttons.Controls.Add(gainCheck);
        buttons.Controls.Add(start);
        buttons.Controls.Add(pause);
        buttons.Controls.Add(resume);
        buttons.Controls.Add(stop);
        table.Controls.Add(buttons, 1, 11);
        table.SetColumnSpan(buttons, 2);

        Controls.Add(table);
        Controls.Add(status);

        uiTimer.Interval = 250;
        uiTimer.Tick += delegate { RefreshUi(); };
        uiTimer.Start();
        FormClosing += OnClosing;
        RefreshUi();
    }

    private static void AddRow(TableLayoutPanel table, int row, string label, Control value, Control extra)
    {
        var name = new Label { Text = label, AutoSize = true, Anchor = AnchorStyles.Left };
        value.Anchor = AnchorStyles.Left | AnchorStyles.Right;
        table.Controls.Add(name, 0, row);
        table.Controls.Add(value, 1, row);
        if (extra != null) table.Controls.Add(extra, 2, row);
    }

    private void BrowseClicked(object sender, EventArgs e)
    {
        using (var dialog = new FolderBrowserDialog()) {
            dialog.Description = "学習データ録音の保存先を選択";
            dialog.SelectedPath = destination.Text;
            if (dialog.ShowDialog(this) == DialogResult.OK) destination.Text = dialog.SelectedPath;
        }
    }

    private void BrowseObsClicked(object sender, EventArgs e)
    {
        using (var dialog = new OpenFileDialog()) {
            dialog.Title = "OBS 32.2.1のobs64.exeを選択";
            dialog.Filter = "OBS executable (obs64.exe)|obs64.exe";
            dialog.FileName = obsExecutable.Text;
            if (dialog.ShowDialog(this) == DialogResult.OK) obsExecutable.Text = dialog.FileName;
        }
    }

    private void StartClicked(object sender, EventArgs e)
    {
        StartOperation(false);
    }

    private void GainCheckClicked(object sender, EventArgs e)
    {
        StartOperation(true);
    }

    private async void StartOperation(bool measureGain)
    {
        if (recording) return;
        var selectedObsPath = obsExecutable.Text.Trim();
        if (!File.Exists(selectedObsPath)) {
            MessageBox.Show(this, "OBS 32.2.1が見つかりません。\n" + selectedObsPath, "OBS未検出",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        string root;
        Process existingObs = null;
        try {
            var runningObs = Process.GetProcessesByName("obs64");
            if (runningObs.Length > 1) throw new InvalidOperationException("OBS_MULTI_PROCESS_AMBIGUOUS");
            if (runningObs.Length == 1) {
                var runningPath = Path.GetFullPath(runningObs[0].MainModule.FileName);
                if (!String.Equals(runningPath, Path.GetFullPath(selectedObsPath),
                        StringComparison.OrdinalIgnoreCase)) {
                    throw new InvalidOperationException("OBS_EXECUTABLE_MISMATCH");
                }
                existingObs = runningObs[0];
            }
            root = Path.GetFullPath(destination.Text.Trim());
            Directory.CreateDirectory(root);
            var drive = new DriveInfo(Path.GetPathRoot(root));
            if (drive.AvailableFreeSpace < (long)diskFloorGb.Value * 1024L * 1024L * 1024L) {
                throw new IOException("保存先の空き容量が設定下限未満です。");
            }
        } catch (Exception ex) {
            MessageBox.Show(this, ex.Message, "保存先エラー", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        var stamp = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ", CultureInfo.InvariantCulture);
        partialPath = Path.Combine(root, "bai-learning-voice-" + stamp + ".partial.wav");
        finalPath = Path.Combine(root, "bai-learning-voice-" + stamp + ".wav");
        gainReceiptPath = Path.Combine(root, "bai-gain-check-" + stamp + ".receipt.json");
        terminalReason = null;
        packetCount = payloadBytes = sequenceGaps = hmacFailures = reconnectCount = pauseCount =
            pauseBoundarySkippedSequences = receivedBytes = 0;
        lock (metricLock) {
            metricSampleCount = clipSampleCount = nonFiniteSampleCount = 0;
            metricSumSquares = 0.0;
            meterWindow.ResetSession();
        }
        levelMeter.ResetLevels();
        connected = false;
        recording = true;
        paused = false;
        sequenceReanchorPending = false;
        gainMeasurement = measureGain;
        terminalStopRequested = false;
        obsProcessId = 0;
        obsReused = existingObs != null;
        stopStarted = 0;
        startedUtc = DateTime.UtcNow;
        measurementStartedUtc = DateTime.MinValue;
        completedPauseDuration = TimeSpan.Zero;
        resumeGate.Set();
        maximumDurationValue = TimeSpan.FromMinutes((double)maximumMinutes.Value);
        diskFloorBytes = (long)diskFloorGb.Value * 1024L * 1024L * 1024L;
        cancellation = new CancellationTokenSource();
        sessionKey = new byte[32];
        using (var rng = RandomNumberGenerator.Create()) rng.GetBytes(sessionKey);
        start.Enabled = false;
        gainCheck.Enabled = false;
        pause.Enabled = !gainMeasurement;
        resume.Enabled = false;
        stop.Enabled = true;
        destination.Enabled = browse.Enabled = obsExecutable.Enabled = browseObs.Enabled =
            maximumMinutes.Enabled = diskFloorGb.Enabled = false;
        string obsMode = existingObs == null ? " OBSを起動して接続します。" :
            " 起動中のOBSへ安全に再接続します。";
        detail.Text = gainMeasurement
            ? "5秒間の録音前GAIN測定中。音声bodyは保存せず、ハードウェア設定も変更しません。" + obsMode
            : (acceptanceMode ? "合成音声Acceptanceモード。Owner音声は使用しません。" :
                "録音中。停止時にWAVとbody-free receiptを確定します。") + obsMode;

        var receiveTask = Task.Run(() => ReceiveLoop(root, selectedObsPath, cancellation.Token));
        await Task.Delay(300);
        if (!recording) return;

        if (existingObs != null) {
            obs = existingObs;
            obsProcessId = existingObs.Id;
            return;
        }

        try {
            var startInfo = new ProcessStartInfo {
                FileName = selectedObsPath,
                WorkingDirectory = Path.GetDirectoryName(selectedObsPath),
                UseShellExecute = false
            };
            startInfo.Arguments = acceptanceMode
                ? "--multi --collection BVP_TASK047_ACCEPTANCE --profile YouTube_VBR_10000_20000_1080p_60fps --disable-updater --verbose"
                : "--disable-updater";
            obs = Process.Start(startInfo);
            if (obs == null) throw new InvalidOperationException("OBS_PROCESS_START_RETURNED_NULL");
            obsProcessId = obs.Id;
        } catch (Exception ex) {
            BeginStop("OBS_LAUNCH_FAILED: " + ex.GetType().Name);
        }
    }

    private bool ValidateSameObsProcess(string operation)
    {
        try {
            if (obs == null || obsProcessId <= 0 || obs.HasExited || obs.Id != obsProcessId) {
                BeginStop("OBS_PROCESS_NOT_RUNNING_DURING_" + operation);
                return false;
            }
            var actualPath = Path.GetFullPath(obs.MainModule.FileName);
            var selectedPath = Path.GetFullPath(obsExecutable.Text.Trim());
            if (!String.Equals(actualPath, selectedPath, StringComparison.OrdinalIgnoreCase)) {
                BeginStop("OBS_PROCESS_IDENTITY_CHANGED_DURING_" + operation);
                return false;
            }
            return true;
        } catch (Exception ex) {
            BeginStop("OBS_PROCESS_VALIDATION_FAILED_DURING_" + operation + ": " + ex.GetType().Name);
            return false;
        }
    }

    private NamedPipeServerStream CreateSameUserPipe()
    {
        var identity = WindowsIdentity.GetCurrent();
        if (identity.User == null) throw new InvalidOperationException("CURRENT_USER_SID_UNAVAILABLE");
        var security = new PipeSecurity();
        security.SetAccessRuleProtection(true, false);
        security.AddAccessRule(new PipeAccessRule(identity.User,
            PipeAccessRights.ReadWrite | PipeAccessRights.CreateNewInstance,
            AccessControlType.Allow));
        return new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1,
            PipeTransmissionMode.Message, PipeOptions.Asynchronous, 1048576, 4096, security);
    }

    private static void ValidateObsPipeClient(NamedPipeServerStream connectedPipe, string selectedObsPath)
    {
        uint processId;
        if (!NativeMethods.GetNamedPipeClientProcessId(
                connectedPipe.SafePipeHandle.DangerousGetHandle(), out processId) || processId == 0) {
            throw new InvalidDataException("PIPE_CLIENT_PID_UNAVAILABLE");
        }
        using (var process = Process.GetProcessById(checked((int)processId))) {
            if (!String.Equals(process.ProcessName, "obs64", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("PIPE_CLIENT_NOT_OBS");
            var actualPath = Path.GetFullPath(process.MainModule.FileName);
            if (!String.Equals(actualPath, Path.GetFullPath(selectedObsPath),
                    StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("PIPE_CLIENT_OBS_PATH_MISMATCH");
        }
    }

    private void ReceiveLoop(string outputRoot, string selectedObsPath, CancellationToken token)
    {
        ulong expectedSequence = 0;
        bool sequenceInitialized = false;
        byte[] expectedNonce = null;
        while (!token.IsCancellationRequested) {
            NamedPipeServerStream currentPipe = null;
            bool wasConnected = false;
            try {
                resumeGate.Wait(token);
                token.ThrowIfCancellationRequested();
                if (paused) continue;
                currentPipe = CreateSameUserPipe();
                pipe = currentPipe;
                var connection = currentPipe.WaitForConnectionAsync();
                while (!connection.IsCompleted) {
                    token.ThrowIfCancellationRequested();
                    if (paused) throw new ObjectDisposedException("paused");
                    Thread.Sleep(50);
                }
                connection.GetAwaiter().GetResult();
                ValidateObsPipeClient(currentPipe, selectedObsPath);
                var hello = ControllerProtocol.BuildSessionHello(sessionKey);
                currentPipe.Write(hello, 0, hello.Length);
                currentPipe.Flush();
                Array.Clear(hello, 0, hello.Length);
                connected = true;
                wasConnected = true;
                if (gainMeasurement && measurementStartedUtc == DateTime.MinValue) {
                    measurementStartedUtc = DateTime.UtcNow;
                }

                while (!token.IsCancellationRequested && currentPipe.IsConnected && !paused) {
                var header = ReadExact(currentPipe, 88, token);
                if (header == null) break;
                uint magic = BitConverter.ToUInt32(header, 0);
                ushort version = BitConverter.ToUInt16(header, 4);
                ushort headerBytes = BitConverter.ToUInt16(header, 6);
                ulong sequence = BitConverter.ToUInt64(header, 8);
                uint frames = BitConverter.ToUInt32(header, 24);
                uint planes = BitConverter.ToUInt32(header, 28);
                uint samples = BitConverter.ToUInt32(header, 32);
                uint bytes = BitConverter.ToUInt32(header, 36);
                if (magic != 0x31495642U || version != 1 || headerBytes != 88 ||
                    frames == 0 || frames > 8192 || planes == 0 || planes > 8 ||
                    samples != frames * planes || bytes != samples * 4U || bytes > 262144U) {
                    throw new InvalidDataException("WIRE_HEADER_INVALID");
                }
                var payload = ReadExact(currentPipe, checked((int)bytes), token);
                if (payload == null) break;
                var nonce = new byte[16];
                Buffer.BlockCopy(header, 40, nonce, 0, nonce.Length);
                if (expectedNonce == null) expectedNonce = nonce;
                else if (!FixedEquals(expectedNonce, nonce)) throw new InvalidDataException("SESSION_NONCE_CHANGED");

                var observedMac = new byte[32];
                Buffer.BlockCopy(header, 56, observedMac, 0, observedMac.Length);
                byte[] computedMac;
                using (var hmac = new HMACSHA256(sessionKey)) {
                    hmac.TransformBlock(header, 0, 56, null, 0);
                    hmac.TransformFinalBlock(payload, 0, payload.Length);
                    computedMac = hmac.Hash;
                }
                if (!FixedEquals(computedMac, observedMac)) {
                    Interlocked.Increment(ref hmacFailures);
                    throw new InvalidDataException("HMAC_INVALID");
                }
                UpdateMetrics(payload);
                if (!sequenceInitialized) {
                    expectedSequence = sequence;
                    sequenceInitialized = true;
                } else if (sequenceReanchorPending) {
                    if (sequence > expectedSequence) {
                        Interlocked.Add(ref pauseBoundarySkippedSequences,
                            unchecked((long)(sequence - expectedSequence)));
                    }
                    expectedSequence = sequence;
                    sequenceReanchorPending = false;
                }
                if (sequence != expectedSequence) {
                    Interlocked.Add(ref sequenceGaps, Math.Abs(unchecked((long)(sequence - expectedSequence))));
                    expectedSequence = sequence;
                }
                expectedSequence++;

                lock (stateLock) {
                    if (!gainMeasurement) {
                        if (wave == null) wave = new WaveFloatWriter(partialPath, checked((ushort)planes), 48000);
                        wave.WritePlanar(payload, checked((int)frames), checked((int)planes));
                    }
                }
                var count = Interlocked.Increment(ref packetCount);
                Interlocked.Add(ref receivedBytes, payload.Length);
                if (!gainMeasurement) {
                    Interlocked.Add(ref payloadBytes, payload.Length);
                    if ((count % 50) == 0) lock (stateLock) { if (wave != null) wave.Checkpoint(); }
                }

                var drive = new DriveInfo(Path.GetPathRoot(outputRoot));
                if (drive.AvailableFreeSpace < diskFloorBytes) {
                    terminalStopRequested = true;
                    BeginInvoke(new Action(() => BeginStop("DISK_FLOOR_REACHED")));
                    break;
                }
                if (gainMeasurement && measurementStartedUtc != DateTime.MinValue &&
                    DateTime.UtcNow - measurementStartedUtc >= TimeSpan.FromSeconds(5)) {
                    terminalStopRequested = true;
                    BeginInvoke(new Action(() => BeginStop("GAIN_CHECK_COMPLETED")));
                    break;
                }
                if (!gainMeasurement && GetActiveElapsed() >= maximumDurationValue) {
                    terminalStopRequested = true;
                    BeginInvoke(new Action(() => BeginStop("MAX_DURATION_REACHED")));
                    break;
                }
            }
            } catch (OperationCanceledException) {
                break;
            } catch (ObjectDisposedException) {
                if (!paused && !token.IsCancellationRequested) {
                    terminalReason = "FAILED: RECEIVER_DISPOSED_UNEXPECTEDLY";
                    terminalStopRequested = true;
                    BeginInvoke(new Action(() => BeginStop(terminalReason)));
                    break;
                }
            } catch (IOException) {
                if (!paused && !token.IsCancellationRequested) {
                    Thread.Sleep(100);
                }
            } catch (Exception ex) {
                terminalReason = "FAILED: " + ex.GetType().Name + ": " + ex.Message;
                terminalStopRequested = true;
                BeginInvoke(new Action(() => BeginStop(terminalReason)));
                break;
            } finally {
                connected = false;
                try { if (currentPipe != null) currentPipe.Dispose(); } catch { }
                if (Object.ReferenceEquals(pipe, currentPipe)) pipe = null;
                if (wasConnected && !paused && !token.IsCancellationRequested && !terminalStopRequested) {
                    Interlocked.Increment(ref reconnectCount);
                }
            }
        }
    }

    private void UpdateMetrics(byte[] payload)
    {
        AudioMeterPacket packet = AudioMeterPacket.Measure(payload);
        lock (metricLock) {
            metricSampleCount += packet.SampleCount;
            clipSampleCount += packet.ClipSampleCount;
            nonFiniteSampleCount += packet.NonFiniteSampleCount;
            metricSumSquares += packet.SumSquares;
            meterWindow.Accumulate(packet);
        }
    }

    private void PauseCapture()
    {
        if (!recording || paused) return;
        if (!ValidateSameObsProcess("PAUSE")) return;
        paused = true;
        sequenceReanchorPending = true;
        pauseStartedUtc = DateTime.UtcNow;
        Interlocked.Increment(ref pauseCount);
        resumeGate.Reset();
        connected = false;
        try { if (pipe != null) pipe.Dispose(); } catch { }
        lock (stateLock) { if (wave != null) wave.Checkpoint(); }
        pause.Enabled = false;
        resume.Enabled = true;
        RefreshUi();
    }

    private void ResumeCapture()
    {
        if (!recording || !paused) return;
        if (!ValidateSameObsProcess("RESUME")) return;
        completedPauseDuration += DateTime.UtcNow - pauseStartedUtc;
        paused = false;
        resumeGate.Set();
        pause.Enabled = true;
        resume.Enabled = false;
        RefreshUi();
    }

    private void StopCapture()
    {
        if (!recording) return;
        if (!ValidateSameObsProcess("STOP")) return;
        BeginStop("USER_STOP");
    }

    private TimeSpan GetActiveElapsed()
    {
        var pausedDuration = completedPauseDuration;
        if (paused) pausedDuration += DateTime.UtcNow - pauseStartedUtc;
        var elapsed = DateTime.UtcNow - startedUtc - pausedDuration;
        return elapsed < TimeSpan.Zero ? TimeSpan.Zero : elapsed;
    }

    private static byte[] ReadExact(Stream stream, int count, CancellationToken token)
    {
        var buffer = new byte[count];
        int offset = 0;
        while (offset < count) {
            token.ThrowIfCancellationRequested();
            int read = stream.Read(buffer, offset, count - offset);
            if (read == 0) return null;
            offset += read;
        }
        return buffer;
    }

    private void BeginStop(string reason)
    {
        if (Interlocked.Exchange(ref stopStarted, 1) != 0) return;
        bool completedGainMeasurement = gainMeasurement;
        terminalReason = reason;
        if (paused) completedPauseDuration += DateTime.UtcNow - pauseStartedUtc;
        paused = false;
        resumeGate.Set();
        recording = false;
        connected = false;
        stop.Enabled = false;
        pause.Enabled = false;
        resume.Enabled = false;
        try { cancellation.Cancel(); } catch { }
        try { if (pipe != null) pipe.Dispose(); } catch { }
        try {
            lock (stateLock) {
                if (wave != null) {
                    wave.Dispose();
                    wave = null;
                }
            }
            if (completedGainMeasurement) {
                WriteGainReceipt(reason);
            } else if (File.Exists(partialPath)) {
                if (File.Exists(finalPath)) throw new IOException("Final output already exists.");
                File.Move(partialPath, finalPath);
                WriteReceipt(finalPath, reason);
            }
        } catch (Exception ex) {
            terminalReason = "FINALIZE_FAILED: " + ex.Message;
        }
        if (sessionKey != null) Array.Clear(sessionKey, 0, sessionKey.Length);
        sessionKey = null;
        destination.Enabled = browse.Enabled = obsExecutable.Enabled = browseObs.Enabled =
            maximumMinutes.Enabled = diskFloorGb.Enabled = true;
        gainMeasurement = false;
        gainCheck.Enabled = true;
        start.Enabled = true;
        RefreshUi();
        if (completedGainMeasurement) detail.Text = FormatGainSummary();
    }

    private void WriteGainReceipt(string reason)
    {
        long samples;
        long clips;
        long nonFinite;
        double sumSquares;
        double peak;
        lock (metricLock) {
            samples = metricSampleCount;
            clips = clipSampleCount;
            nonFinite = nonFiniteSampleCount;
            sumSquares = metricSumSquares;
            peak = meterWindow.SessionMaximum;
        }
        double rms = samples > 0 ? Math.Sqrt(sumSquares / samples) : 0.0;
        string factState = samples > 0 && nonFinite == 0 ? "MEASURED" :
            (samples > 0 ? "ERROR_NON_FINITE_SAMPLE" : "INSUFFICIENT_INPUT");
        string signalIntegrity = samples == 0 ? "UNKNOWN" :
            (clips > 0 ? "FAIL_CLIPPING" : "MEASURED_NO_CLIPPING");
        string recommendation = clips > 0 ? "LOWER_HARDWARE_GAIN_PROPOSAL" :
            "NO_AUTOMATIC_RECOMMENDATION";
        string peakDb = samples > 0 && peak > 0.0 ?
            (20.0 * Math.Log10(peak)).ToString("0.000", CultureInfo.InvariantCulture) : "null";
        string rmsDb = samples > 0 && rms > 0.0 ?
            (20.0 * Math.Log10(rms)).ToString("0.000", CultureInfo.InvariantCulture) : "null";
        var json = "{\n" +
            "  \"schema\": \"bvp.task047.local-gain-check-receipt.v1\",\n" +
            "  \"terminal_reason\": \"" + JsonEscape(reason) + "\",\n" +
            "  \"started_at_utc\": \"" + startedUtc.ToString("o") + "\",\n" +
            "  \"finished_at_utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n" +
            "  \"measurement_fact_state\": \"" + factState + "\",\n" +
            "  \"signal_integrity_state\": \"" + signalIntegrity + "\",\n" +
            "  \"gain_admission_state\": \"UNKNOWN_POLICY_NOT_BOUND\",\n" +
            "  \"recommendation\": \"" + recommendation + "\",\n" +
            "  \"sample_peak_dbfs\": " + peakDb + ",\n" +
            "  \"rms_dbfs\": " + rmsDb + ",\n" +
            "  \"clip_threshold_abs\": 0.9999,\n" +
            "  \"clip_sample_count\": " + clips.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"non_finite_sample_count\": " + nonFinite.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"measured_sample_values\": " + samples.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"received_bytes\": " + receivedBytes.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"audio_body_persisted\": false,\n" +
            "  \"hardware_setting_changed\": false,\n" +
            "  \"session_key_persisted\": false\n" +
            "}\n";
        File.WriteAllText(gainReceiptPath, json, new UTF8Encoding(false));
    }

    private string FormatGainSummary()
    {
        long samples;
        long clips;
        double sumSquares;
        double peak;
        lock (metricLock) {
            samples = metricSampleCount;
            clips = clipSampleCount;
            sumSquares = metricSumSquares;
            peak = meterWindow.SessionMaximum;
        }
        if (samples == 0) return "GAINチェック: 入力不足。音声は保存していません。";
        double rms = Math.Sqrt(sumSquares / samples);
        string peakDb = AudioMeterSnapshot.FormatDbfs(peak, samples);
        string rmsDb = AudioMeterSnapshot.FormatDbfs(rms, samples);
        return String.Format(CultureInfo.InvariantCulture,
            "GAIN測定: Peak {0} dBFS / RMS {1} dBFS / clip {2}。{3}音声保存なし。適正判定はQuality Policy未設定のため未確定です。",
            peakDb, rmsDb, clips, peak > 1.0 ? "入力範囲外の検出あり。" : "");
    }

    private void WriteReceipt(string audioPath, string reason)
    {
        string hash;
        using (var sha = SHA256.Create())
        using (var input = File.OpenRead(audioPath)) hash = ToHex(sha.ComputeHash(input));
        var receiptPath = audioPath + ".receipt.json";
        var json = "{\n" +
            "  \"schema\": \"bvp.task047.local-voice-capture-receipt.v1\",\n" +
            "  \"terminal_reason\": \"" + JsonEscape(reason) + "\",\n" +
            "  \"started_at_utc\": \"" + startedUtc.ToString("o") + "\",\n" +
            "  \"finished_at_utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n" +
            "  \"audio_filename\": \"" + JsonEscape(Path.GetFileName(audioPath)) + "\",\n" +
            "  \"audio_bytes\": " + new FileInfo(audioPath).Length.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"audio_sha256\": \"" + hash + "\",\n" +
            "  \"packet_count\": " + packetCount.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"payload_bytes\": " + payloadBytes.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"sequence_gaps\": " + sequenceGaps.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"hmac_failures\": " + hmacFailures.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"transport_reconnects\": " + reconnectCount.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"pause_count\": " + pauseCount.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"pause_boundary_skipped_sequences\": " + pauseBoundarySkippedSequences.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"paused_duration_seconds\": " + completedPauseDuration.TotalSeconds.ToString("0.000", CultureInfo.InvariantCulture) + ",\n" +
            "  \"obs_process_id\": " + obsProcessId.ToString(CultureInfo.InvariantCulture) + ",\n" +
            "  \"obs_process_reused\": " + (obsReused ? "true" : "false") + ",\n" +
            "  \"obs_pause_resume_pid_stability_state\": \"" +
                (pauseCount > 0 ? "VERIFIED_SAME_PROCESS" : "NOT_EXERCISED") + "\",\n" +
            "  \"session_key_persisted\": false\n" +
            "}\n";
        File.WriteAllText(receiptPath, json, new UTF8Encoding(false));
    }

    private static string JsonEscape(string value)
    {
        if (value == null) return String.Empty;
        return value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
    }

    private static bool FixedEquals(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        int difference = 0;
        for (int i = 0; i < left.Length; i++) difference |= left[i] ^ right[i];
        return difference == 0;
    }

    private static string ToHex(byte[] bytes)
    {
        var result = new StringBuilder(bytes.Length * 2);
        foreach (byte value in bytes) result.Append(value.ToString("x2", CultureInfo.InvariantCulture));
        return result.ToString();
    }

    private void RefreshUi()
    {
        pause.Enabled = recording && !gainMeasurement && connected && !paused;
        resume.Enabled = recording && !gainMeasurement && paused;
        if (recording && gainMeasurement && connected) {
            status.Text = "● 録音前GAINチェック中（音声保存なし）";
            status.BackColor = Color.FromArgb(30, 100, 180);
        } else if (recording && paused) {
            status.Text = "⏸ 学習データ録音 一時停止中";
            status.BackColor = Color.FromArgb(200, 120, 0);
        } else if (recording && connected) {
            status.Text = "● 学習データ録音中";
            status.BackColor = Color.FromArgb(190, 20, 35);
        } else if (recording) {
            status.Text = "録音準備中（OBS接続待ち）";
            status.BackColor = Color.FromArgb(200, 120, 0);
        } else {
            status.Text = "停止中";
            status.BackColor = Color.FromArgb(70, 70, 70);
        }
        var age = recording ? GetActiveElapsed() : TimeSpan.Zero;
        elapsed.Text = age.ToString(@"hh\:mm\:ss");
        written.Text = gainMeasurement
            ? "音声保存なし / 受信 " + FormatBytes(Interlocked.Read(ref receivedBytes))
            : FormatBytes(Interlocked.Read(ref payloadBytes));
        packets.Text = String.Format(CultureInfo.InvariantCulture,
            "{0} packets / gap {1} / HMAC {2} / reconnect {3}",
            Interlocked.Read(ref packetCount), Interlocked.Read(ref sequenceGaps),
            Interlocked.Read(ref hmacFailures), Interlocked.Read(ref reconnectCount));
        AudioMeterSnapshot window;
        long clips;
        long samples;
        lock (metricLock) {
            window = meterWindow.SnapshotAndReset();
            clips = clipSampleCount;
            samples = metricSampleCount;
        }
        double livePeak = window.Packet.Peak;
        double liveRms = window.Packet.Rms;
        double livePeakDb = livePeak > 0.0 ? 20.0 * Math.Log10(livePeak) : -60.0;
        double liveRmsDb = liveRms > 0.0 ? 20.0 * Math.Log10(liveRms) : -60.0;
        levelMeter.UpdateLevels(livePeakDb, liveRmsDb, window.Packet.ClipSampleCount > 0, clips > 0);
        levelValues.Text = String.Format(CultureInfo.InvariantCulture,
            "Peak {0} / RMS {1} / 最大 {2} dBFS\n" +
            "clip 今回 {4}（赤バー）/ 累計 {3}（赤枠）\n" +
            "非有限(今回) {5} / {6} / {7}\n" +
            "0 dBFS = デジタル上限 / 警告・適正判定 未確定",
            AudioMeterSnapshot.FormatDbfs(livePeak, window.Packet.SampleCount),
            AudioMeterSnapshot.FormatDbfs(liveRms, window.Packet.SampleCount),
            AudioMeterSnapshot.FormatDbfs(window.SessionMaximum, samples),
            clips, window.Packet.ClipSampleCount, window.Packet.NonFiniteSampleCount,
            paused ? "一時停止" : window.ObservationState, window.RangeState);
        try {
            var root = Path.GetPathRoot(Path.GetFullPath(destination.Text));
            freeSpace.Text = FormatBytes(new DriveInfo(root).AvailableFreeSpace);
        } catch { freeSpace.Text = "未確認"; }
        if (!recording && !String.IsNullOrEmpty(terminalReason)) detail.Text = "停止理由: " + terminalReason;
    }

    private static string FormatBytes(long bytes)
    {
        string[] units = { "B", "KiB", "MiB", "GiB", "TiB" };
        double value = bytes;
        int unit = 0;
        while (value >= 1024 && unit < units.Length - 1) { value /= 1024; unit++; }
        return value.ToString("0.00", CultureInfo.InvariantCulture) + " " + units[unit];
    }

    private void OnClosing(object sender, FormClosingEventArgs e)
    {
        if (recording) BeginStop("CONTROLLER_WINDOW_CLOSED");
    }
}

// Packet analysis is memory-only. The caller owns metricLock for aggregation
// and snapshot/reset; the OBS real-time callback and capture transport are unchanged.
internal struct AudioMeterPacket
{
    public readonly long SampleCount;
    public readonly long ClipSampleCount;
    public readonly long NonFiniteSampleCount;
    public readonly double SumSquares;
    public readonly double Peak;

    public AudioMeterPacket(long samples, long clips, long nonFinite, double sumSquares, double peak)
    {
        SampleCount = samples;
        ClipSampleCount = clips;
        NonFiniteSampleCount = nonFinite;
        SumSquares = sumSquares;
        Peak = peak;
    }

    public double Rms { get { return SampleCount > 0 ? Math.Sqrt(SumSquares / SampleCount) : 0.0; } }

    public static AudioMeterPacket Measure(byte[] payload)
    {
        long samples = 0, clips = 0, nonFinite = 0;
        double sumSquares = 0.0, peak = 0.0;
        for (int offset = 0; offset + 4 <= payload.Length; offset += 4) {
            double value = BitConverter.ToSingle(payload, offset);
            if (Double.IsNaN(value) || Double.IsInfinity(value)) {
                nonFinite++;
                continue;
            }
            double absolute = Math.Abs(value);
            peak = Math.Max(peak, absolute);
            // Preserve the existing observed clip boundary; this is not a
            // quality-policy target/warning threshold or a hardware setting.
            if (absolute >= 0.9999) clips++;
            sumSquares += value * value;
            samples++;
        }
        return new AudioMeterPacket(samples, clips, nonFinite, sumSquares, peak);
    }
}

internal struct AudioMeterSnapshot
{
    public readonly AudioMeterPacket Packet;
    public readonly double SessionMaximum;

    public AudioMeterSnapshot(AudioMeterPacket packet, double sessionMaximum)
    {
        Packet = packet;
        SessionMaximum = sessionMaximum;
    }

    public string ObservationState {
        get {
            if (Packet.NonFiniteSampleCount > 0) return "入力異常";
            if (Packet.SampleCount == 0) return "今回の受信なし";
            return Packet.Peak == 0.0 ? "無音入力" : "観測中";
        }
    }

    public string RangeState {
        get {
            if (Packet.Peak > 1.0) return "入力範囲外(今回)";
            if (SessionMaximum > 1.0) return "入力範囲外(履歴)";
            return Packet.SampleCount > 0 ? "範囲外の検出なし" : "入力範囲 未観測";
        }
    }

    public static string FormatDbfs(double amplitude, long sampleCount)
    {
        if (sampleCount == 0) return "--";
        return amplitude > 0.0
            ? (20.0 * Math.Log10(Math.Min(1.0, amplitude))).ToString("0.0", CultureInfo.InvariantCulture)
            : "-∞";
    }
}

internal sealed class AudioMeterWindow
{
    private AudioMeterPacket pending;
    public double SessionMaximum { get; private set; }

    public void Accumulate(AudioMeterPacket packet)
    {
        // Sample-weighted RMS, not the mean of packet RMS values.
        pending = new AudioMeterPacket(
            checked(pending.SampleCount + packet.SampleCount),
            checked(pending.ClipSampleCount + packet.ClipSampleCount),
            checked(pending.NonFiniteSampleCount + packet.NonFiniteSampleCount),
            pending.SumSquares + packet.SumSquares,
            Math.Max(pending.Peak, packet.Peak));
        SessionMaximum = Math.Max(SessionMaximum, packet.Peak);
    }

    public AudioMeterSnapshot SnapshotAndReset()
    {
        var result = new AudioMeterSnapshot(pending, SessionMaximum);
        pending = default(AudioMeterPacket);
        return result;
    }

    public void ResetSession()
    {
        pending = default(AudioMeterPacket);
        SessionMaximum = 0.0;
    }
}

internal sealed class AudioMeterPeakHold
{
    private const long HoldTicks = 1500L * TimeSpan.TicksPerMillisecond;
    private long heldAt;
    private long lastObservedAt;
    public double PeakDb { get; private set; }

    public AudioMeterPeakHold() { Reset(); }

    public void Reset()
    {
        PeakDb = -60.0;
        heldAt = lastObservedAt = 0;
    }

    public void Observe(double peakDb, long monotonicTicks)
    {
        if (Double.IsNaN(peakDb) || Double.IsInfinity(peakDb) || peakDb < -60.0 || peakDb > 0.0)
            throw new ArgumentOutOfRangeException("peakDb");
        if (monotonicTicks < lastObservedAt) throw new ArgumentOutOfRangeException("monotonicTicks");
        lastObservedAt = monotonicTicks;
        if (peakDb >= PeakDb || monotonicTicks - heldAt >= HoldTicks) {
            PeakDb = peakDb;
            heldAt = monotonicTicks;
        }
    }
}

internal struct AudioMeterClipDisplay
{
    public readonly bool WindowClipped;
    public readonly bool SessionClipped;

    public AudioMeterClipDisplay(bool windowClipped, bool sessionClipped)
    {
        WindowClipped = windowClipped;
        SessionClipped = sessionClipped;
    }
}

internal sealed class AudioLevelMeter : Control
{
    private double peakDb = -60.0;
    private double rmsDb = -60.0;
    private readonly AudioMeterPeakHold peakHold = new AudioMeterPeakHold();
    private readonly Stopwatch meterClock = Stopwatch.StartNew();
    private AudioMeterClipDisplay clipDisplay;

    public AudioLevelMeter()
    {
        DoubleBuffered = true;
        MinimumSize = new Size(240, 32);
        BackColor = Color.FromArgb(28, 28, 28);
    }

    public void ResetLevels()
    {
        peakDb = rmsDb = -60.0;
        peakHold.Reset();
        clipDisplay = default(AudioMeterClipDisplay);
        Invalidate();
    }

    public void UpdateLevels(double peak, double rms, bool windowClipped, bool sessionClipped)
    {
        peakDb = ClampDb(peak);
        rmsDb = ClampDb(rms);
        clipDisplay = new AudioMeterClipDisplay(windowClipped, sessionClipped);
        peakHold.Observe(peakDb, meterClock.Elapsed.Ticks);
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var bounds = new Rectangle(1, 1, Math.Max(1, Width - 3), Math.Max(1, Height - 3));
        using (var background = new SolidBrush(BackColor)) e.Graphics.FillRectangle(background, bounds);
        int rmsX = DbToX(rmsDb, bounds);
        int peakX = DbToX(peakDb, bounds);
        using (var rmsBrush = new SolidBrush(clipDisplay.WindowClipped ? Color.FromArgb(220, 45, 45) : Color.FromArgb(65, 120, 180)))
            e.Graphics.FillRectangle(rmsBrush, bounds.Left, bounds.Top, Math.Max(0, rmsX - bounds.Left), bounds.Height);
        using (var peakBrush = new SolidBrush(clipDisplay.WindowClipped ? Color.FromArgb(220, 45, 45) : Color.FromArgb(45, 155, 230)))
            e.Graphics.FillRectangle(peakBrush, rmsX, bounds.Top, Math.Max(0, peakX - rmsX), bounds.Height);
        int holdX = DbToX(peakHold.PeakDb, bounds);
        using (var holdPen = new Pen(Color.White, 2F))
            e.Graphics.DrawLine(holdPen, holdX, bounds.Top, holdX, bounds.Bottom);
        using (var border = new Pen(clipDisplay.SessionClipped ? Color.Red : Color.DimGray)) e.Graphics.DrawRectangle(border, bounds);
        using (var labelBrush = new SolidBrush(Color.WhiteSmoke)) {
            foreach (int tick in new[] { -60, -48, -36, -24, -12, 0 }) {
                int x = DbToX(tick, bounds);
                e.Graphics.DrawString(tick.ToString(CultureInfo.InvariantCulture), Font, labelBrush,
                    Math.Max(bounds.Left, x - 10), bounds.Top + 2);
            }
        }
    }

    private static double ClampDb(double value)
    {
        if (Double.IsNaN(value) || Double.IsInfinity(value)) return -60.0;
        return Math.Max(-60.0, Math.Min(0.0, value));
    }

    private static int DbToX(double value, Rectangle bounds)
    {
        return bounds.Left + checked((int)Math.Round((ClampDb(value) + 60.0) / 60.0 * bounds.Width));
    }
}

internal static class ControllerProtocol
{
    internal const uint SessionHelloMagic = 0x32484342U;
    internal const ushort SessionHelloVersion = 2;
    internal const int SessionHelloBytes = 40;

    internal static byte[] BuildSessionHello(byte[] sessionKey)
    {
        if (sessionKey == null || sessionKey.Length != 32 || sessionKey.All(value => value == 0))
            throw new ArgumentException("SESSION_KEY_INVALID", "sessionKey");
        var hello = new byte[SessionHelloBytes];
        Buffer.BlockCopy(BitConverter.GetBytes(SessionHelloMagic), 0, hello, 0, 4);
        Buffer.BlockCopy(BitConverter.GetBytes(SessionHelloVersion), 0, hello, 4, 2);
        Buffer.BlockCopy(BitConverter.GetBytes((ushort)SessionHelloBytes), 0, hello, 6, 2);
        Buffer.BlockCopy(sessionKey, 0, hello, 8, sessionKey.Length);
        return hello;
    }
}

internal static class NativeMethods
{
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool GetNamedPipeClientProcessId(IntPtr pipe, out uint clientProcessId);
}

internal sealed class WaveFloatWriter : IDisposable
{
    private readonly FileStream stream;
    private readonly BinaryWriter writer;
    private readonly ushort channels;
    private readonly uint sampleRate;
    private long dataBytes;
    private bool disposed;

    public WaveFloatWriter(string path, ushort channels, uint sampleRate)
    {
        this.channels = channels;
        this.sampleRate = sampleRate;
        stream = new FileStream(path, FileMode.CreateNew, FileAccess.ReadWrite, FileShare.Read);
        writer = new BinaryWriter(stream, Encoding.ASCII, true);
        WriteHeader();
    }

    private void WriteHeader()
    {
        writer.Write(Encoding.ASCII.GetBytes("RIFF"));
        writer.Write((uint)0);
        writer.Write(Encoding.ASCII.GetBytes("WAVEfmt "));
        writer.Write((uint)16);
        writer.Write((ushort)3);
        writer.Write(channels);
        writer.Write(sampleRate);
        uint byteRate = sampleRate * channels * 4U;
        writer.Write(byteRate);
        writer.Write((ushort)(channels * 4));
        writer.Write((ushort)32);
        writer.Write(Encoding.ASCII.GetBytes("data"));
        writer.Write((uint)0);
    }

    public void WritePlanar(byte[] planarBytes, int frames, int planeCount)
    {
        if (disposed) throw new ObjectDisposedException("WaveFloatWriter");
        if (planeCount != channels) throw new InvalidDataException("CHANNEL_COUNT_CHANGED");
        var planar = new float[frames * planeCount];
        var interleaved = new float[planar.Length];
        Buffer.BlockCopy(planarBytes, 0, planar, 0, planarBytes.Length);
        for (int frame = 0; frame < frames; frame++)
            for (int channel = 0; channel < planeCount; channel++)
                interleaved[frame * planeCount + channel] = planar[channel * frames + frame];
        var bytes = new byte[planarBytes.Length];
        Buffer.BlockCopy(interleaved, 0, bytes, 0, bytes.Length);
        writer.Write(bytes);
        dataBytes += bytes.Length;
        if (dataBytes > UInt32.MaxValue - 44L) throw new IOException("WAV_4GIB_LIMIT_REACHED");
    }

    public void Checkpoint()
    {
        PatchHeader();
        stream.Flush(true);
    }

    private void PatchHeader()
    {
        long position = stream.Position;
        stream.Position = 4;
        writer.Write((uint)(36L + dataBytes));
        stream.Position = 40;
        writer.Write((uint)dataBytes);
        stream.Position = position;
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        PatchHeader();
        stream.Flush(true);
        writer.Dispose();
        stream.Dispose();
    }
}

// Explicit headless test entry: synthetic in-memory packets only. Unlike the
// existing writer self-test, this does not open a Form, OBS, a pipe or a file.
internal static class MeterObservationSelfTest
{
    private static AudioMeterPacket Packet(params float[] samples)
    {
        var bytes = new byte[samples.Length * 4];
        Buffer.BlockCopy(samples, 0, bytes, 0, bytes.Length);
        return AudioMeterPacket.Measure(bytes);
    }

    private static void Require(bool condition, string name)
    {
        if (!condition) throw new InvalidOperationException(name);
    }

    public static int Run()
    {
        try {
            var window = new AudioMeterWindow();
            window.Accumulate(Packet(0.875F));
            window.Accumulate(Packet(0.125F, 0.125F, 0.125F));
            var first = window.SnapshotAndReset();
            Require(first.Packet.Peak == 0.875, "high_then_low_preserves_peak");
            Require(first.Packet.SampleCount == 4, "window_sample_count");
            Require(Math.Abs(first.Packet.Rms - Math.Sqrt(0.8125 / 4.0)) < 1e-12,
                "sample_weighted_window_rms");
            var empty = window.SnapshotAndReset();
            Require(empty.Packet.SampleCount == 0 && empty.Packet.Peak == 0.0 &&
                empty.Packet.Rms == 0.0 && empty.Packet.ClipSampleCount == 0,
                "snapshot_resets_only_window");
            Require(empty.SessionMaximum == 0.875 && empty.ObservationState == "今回の受信なし",
                "no_packet_is_not_silence_or_session_reset");
            Require(first.Packet.Peak == 0.875 && first.Packet.SampleCount == 4,
                "snapshot_is_immutable_value");
            window.Accumulate(Packet(0.25F));
            Require(window.SnapshotAndReset().SessionMaximum == 0.875, "session_maximum_monotonic");
            window.Accumulate(Packet(0.0F, 0.0F));
            var silent = window.SnapshotAndReset();
            Require(silent.ObservationState == "無音入力" && silent.SessionMaximum == 0.875,
                "silence_preserves_session_maximum");
            Require(AudioMeterSnapshot.FormatDbfs(0.0, 2) == "-∞" &&
                AudioMeterSnapshot.FormatDbfs(0.0, 0) == "--", "silence_vs_missing_reading");
            window.ResetSession();
            Require(window.SnapshotAndReset().SessionMaximum == 0.0, "explicit_session_reset");

            window.Accumulate(Packet(0.5F, -0.5F));
            Require(window.SnapshotAndReset().Packet.ClipSampleCount == 0,
                "below_clip_does_not_invent_warning");
            window.Accumulate(Packet(1.0F, -1.0F, 1.25F));
            var clipped = window.SnapshotAndReset();
            Require(clipped.Packet.ClipSampleCount == 3 && clipped.Packet.Peak == 1.25 &&
                clipped.SessionMaximum == 1.25, "full_scale_and_overrange_observed_before_drawing_clamp");
            Require(AudioMeterSnapshot.FormatDbfs(1.25, 3) == "0.0" &&
                clipped.RangeState == "入力範囲外(今回)", "overrange_display_clamped_and_explicit");
            long sessionClips = clipped.Packet.ClipSampleCount;
            var clipDisplay = new AudioMeterClipDisplay(clipped.Packet.ClipSampleCount > 0, sessionClips > 0);
            Require(clipDisplay.WindowClipped && clipDisplay.SessionClipped, "clip_window_marks_bar_and_history");
            window.Accumulate(Packet(0.125F));
            var quiet = window.SnapshotAndReset();
            sessionClips += quiet.Packet.ClipSampleCount;
            clipDisplay = new AudioMeterClipDisplay(quiet.Packet.ClipSampleCount > 0, sessionClips > 0);
            Require(!clipDisplay.WindowClipped && clipDisplay.SessionClipped,
                "quiet_window_clears_red_bar_but_preserves_history");
            Require(quiet.RangeState == "入力範囲外(履歴)" && quiet.SessionMaximum == 1.25 &&
                AudioMeterSnapshot.FormatDbfs(quiet.SessionMaximum, 3) == "0.0",
                "overrange_history_preserves_raw_session_maximum");
            Require(window.SnapshotAndReset().Packet.ClipSampleCount == 0,
                "window_clip_delta_not_replayed");
            foreach (double db in new[] { -60.0, -24.0, -12.0, -1.0, 0.0 }) {
                var measured = Packet((float)Math.Pow(10.0, db / 20.0));
                Require(Math.Abs(20.0 * Math.Log10(measured.Peak) - db) < 0.001,
                    "known_dbfs_vector");
                Require(measured.ClipSampleCount == (db == 0.0 ? 1 : 0),
                    "zero_dbfs_clip_is_not_warning_band");
            }
            window.ResetSession();
            window.Accumulate(Packet(float.NaN, float.PositiveInfinity, float.NegativeInfinity, 0.25F));
            var invalid = window.SnapshotAndReset();
            Require(invalid.Packet.NonFiniteSampleCount == 3 && invalid.Packet.SampleCount == 1 &&
                invalid.Packet.Rms == 0.25 && invalid.ObservationState == "入力異常",
                "nonfinite_samples_excluded_and_reported");
            window.Accumulate(Packet(float.NaN));
            Require(window.SnapshotAndReset().ObservationState == "入力異常",
                "all_nonfinite_is_not_silence_or_missing");
            window.Accumulate(Packet(1.0F));
            window.ResetSession();
            var reset = window.SnapshotAndReset();
            Require(reset.Packet.SampleCount == 0 && reset.Packet.ClipSampleCount == 0 &&
                reset.SessionMaximum == 0.0, "reset_discards_pending_previous_session");

            var hold = new AudioMeterPeakHold();
            hold.Observe(-1.0, 0);
            hold.Observe(-20.0, TimeSpan.FromMilliseconds(1499).Ticks);
            Require(hold.PeakDb == -1.0, "hold_before_exact_expiry");
            hold.Observe(-20.0, TimeSpan.FromMilliseconds(1500).Ticks);
            Require(hold.PeakDb == -20.0, "hold_expires_at_exact_boundary");
            hold.Observe(-2.0, TimeSpan.FromMilliseconds(1600).Ticks);
            Require(hold.PeakDb == -2.0, "higher_peak_immediately_replaces_hold");
            hold.Observe(-2.0, TimeSpan.FromMilliseconds(2000).Ticks);
            hold.Observe(-30.0, TimeSpan.FromMilliseconds(3499).Ticks);
            Require(hold.PeakDb == -2.0, "equal_peak_refreshes_hold");
            hold.Observe(-60.0, TimeSpan.FromMilliseconds(3500).Ticks);
            Require(hold.PeakDb == -60.0, "pause_or_no_input_expires_hold");
            hold.Reset();
            Require(hold.PeakDb == -60.0, "hold_reset");
            hold.Observe(-12.0, 10);
            bool rejected = false;
            try { hold.Observe(-20.0, 9); }
            catch (ArgumentOutOfRangeException) { rejected = true; }
            Require(rejected, "nonmonotonic_hold_clock_rejected");
            rejected = false;
            try { hold.Observe(double.NaN, 11); }
            catch (ArgumentOutOfRangeException) { rejected = true; }
            Require(rejected, "nonfinite_hold_reading_rejected");
            return 0;
        } catch (Exception error) {
            Console.Error.WriteLine("METER_SELF_TEST_FAIL " + error.Message);
            return 98;
        }
    }
}

internal static class ControllerSelfTest
{
    public static int Run()
    {
        string path = Path.Combine(Path.GetTempPath(), "bai-controller-self-test-" + Guid.NewGuid().ToString("N") + ".wav");
        try {
            var planar = new float[] { 1.0F, 2.0F, 3.0F, 4.0F };
            var bytes = new byte[planar.Length * 4];
            Buffer.BlockCopy(planar, 0, bytes, 0, bytes.Length);
            using (var writer = new WaveFloatWriter(path, 2, 48000)) {
                writer.WritePlanar(bytes, 2, 2);
                writer.Checkpoint();
            }
            var output = File.ReadAllBytes(path);
            if (output.Length != 60) return 11;
            if (Encoding.ASCII.GetString(output, 0, 4) != "RIFF") return 12;
            if (Encoding.ASCII.GetString(output, 8, 4) != "WAVE") return 13;
            if (BitConverter.ToUInt16(output, 20) != 3 || BitConverter.ToUInt16(output, 22) != 2) return 14;
            if (BitConverter.ToUInt32(output, 24) != 48000 || BitConverter.ToUInt32(output, 40) != 16) return 15;
            var actual = new float[4];
            Buffer.BlockCopy(output, 44, actual, 0, 16);
            var expected = new float[] { 1.0F, 3.0F, 2.0F, 4.0F };
            for (int i = 0; i < expected.Length; i++) if (actual[i] != expected[i]) return 16;
            var key = Enumerable.Range(1, 32).Select(value => checked((byte)value)).ToArray();
            var hello = ControllerProtocol.BuildSessionHello(key);
            if (hello.Length != 40 || BitConverter.ToUInt32(hello, 0) != ControllerProtocol.SessionHelloMagic ||
                BitConverter.ToUInt16(hello, 4) != ControllerProtocol.SessionHelloVersion ||
                BitConverter.ToUInt16(hello, 6) != 40) return 17;
            for (int i = 0; i < key.Length; i++) if (hello[i + 8] != key[i]) return 18;
            Array.Clear(key, 0, key.Length);
            Array.Clear(hello, 0, hello.Length);
            return 0;
        } catch {
            return 99;
        } finally {
            try { if (File.Exists(path)) File.Delete(path); } catch { }
        }
    }
}
