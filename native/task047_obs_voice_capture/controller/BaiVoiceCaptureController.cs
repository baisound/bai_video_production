using System;
using System.Collections.Generic;
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
using Microsoft.Win32.SafeHandles;

// C1B actual Windows binding. The frozen C1A launcher owns admission order.
internal static class BaiMeterWin32
{
    [StructLayout(LayoutKind.Sequential)]
    internal struct FileTime { internal uint Low, High; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct FileInfo
    {
        internal uint Attributes; internal FileTime Creation, Access, Write;
        internal uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [StructLayout(LayoutKind.Sequential)]
    internal struct FileIdInfo
    {
        internal ulong Volume;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)] internal byte[] Id;
    }
    [StructLayout(LayoutKind.Sequential)]
    internal struct SecurityAttributes { internal int Length; internal IntPtr Descriptor; internal int Inherit; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    internal struct StartupInfo
    {
        internal uint Cb; internal string Reserved, Desktop, Title;
        internal uint X, Y, Cx, Cy, CharsX, CharsY, Fill, Flags;
        internal ushort Show, ReservedSize; internal IntPtr Reserved2, Stdin, Stdout, Stderr;
    }
    [StructLayout(LayoutKind.Sequential)]
    internal struct StartupInfoEx { internal StartupInfo Info; internal IntPtr Attributes; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct ProcessInformation { internal IntPtr Process, Thread; internal uint Pid, Tid; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct JobBasic
    {
        internal long ProcessTime, JobTime; internal uint Flags;
        internal UIntPtr MinWorkingSet, MaxWorkingSet; internal uint ActiveLimit;
        internal UIntPtr Affinity; internal uint Priority, Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)]
    internal struct IoCounters { internal ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct JobExtended
    {
        internal JobBasic Basic; internal IoCounters Io;
        internal UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern IntPtr CreateFileW(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool GetFileInformationByHandle(IntPtr file, out FileInfo info);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool GetFileInformationByHandleEx(IntPtr file, int kind, out FileIdInfo info, uint size);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern uint GetFinalPathNameByHandleW(IntPtr file, StringBuilder path, uint size, uint flags);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool SetFilePointerEx(IntPtr file, long offset, IntPtr resulting, uint origin);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool CreatePipe(out IntPtr reader, out IntPtr writer, ref SecurityAttributes security, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref UIntPtr size);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, UIntPtr attribute, IntPtr value, UIntPtr size, IntPtr previous, IntPtr resultSize);
    [DllImport("kernel32.dll")]
    internal static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern bool CreateProcessW(string image, StringBuilder command, IntPtr processSecurity, IntPtr threadSecurity,
        bool inherit, uint flags, IntPtr environment, string cwd, ref StartupInfoEx startup, out ProcessInformation result);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern uint GetProcessId(IntPtr process);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool GetProcessTimes(IntPtr process, out FileTime created, out FileTime exited, out FileTime kernel, out FileTime user);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern bool QueryFullProcessImageNameW(IntPtr process, uint flags, StringBuilder image, ref uint size);
    [DllImport("kernel32.dll")]
    internal static extern IntPtr GetCurrentProcess();
    [DllImport("advapi32.dll", SetLastError = true)]
    internal static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", SetLastError = true)]
    internal static extern bool GetTokenInformation(IntPtr token, int kind, IntPtr data, uint size, out uint needed);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern bool ConvertSidToStringSidW(IntPtr sid, out IntPtr text);
    [DllImport("kernel32.dll")]
    internal static extern IntPtr LocalFree(IntPtr value);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern bool CreateDirectoryW(string path, IntPtr security);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    internal static extern uint GetWindowsDirectoryW(StringBuilder path, uint size);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern IntPtr CreateJobObjectW(IntPtr security, string name);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool SetInformationJobObject(IntPtr job, int kind, ref JobExtended limits, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool TerminateProcess(IntPtr process, uint code);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern uint WaitForSingleObject(IntPtr process, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern IntPtr GetStdHandle(int which);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern uint GetFileType(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool PeekNamedPipe(IntPtr pipe, IntPtr data, uint size, IntPtr read, out uint available, IntPtr left);
    [DllImport("kernel32.dll", SetLastError = true)]
    internal static extern bool ReadFile(IntPtr pipe, byte[] data, uint size, out uint count, IntPtr overlapped);
}

internal sealed class BaiMeterFilePin
{
    internal IntPtr Handle; internal string Path; internal ulong Volume;
    internal byte[] FileId, Digest; internal bool Directory;
}
internal sealed class BaiMeterPinLease : IDisposable
{
    private readonly Func<IntPtr, bool> closeHandle;
    internal BaiMeterPinLease(Func<IntPtr, bool> closeHandle) { this.closeHandle = closeHandle; }
    internal readonly List<BaiMeterFilePin> Items = new List<BaiMeterFilePin>();
    public void Dispose()
    {
        foreach (BaiMeterFilePin item in Items) {
            try { if (item.Handle != IntPtr.Zero && closeHandle(item.Handle)) item.Handle = IntPtr.Zero; }
            catch (Exception) { } // Attempt every retained pin; keep failed identities.
        }
        BaiMeterProtocol.Require(Items.All(x => x.Handle == IntPtr.Zero));
    }
}

#if !BVP_METER_PACKAGED
// Standalone legacy Controller still records. Only managed advisory is unavailable.
internal static class BaiMeterBuildIdentity
{
    internal static readonly string[] Files = new string[0];
    internal static readonly string[] Digests = new string[0];
}
#endif

// Injectable native effects for concrete partial-success/cleanup fault contracts.
// The packaged path uses only these Win32 calls; self-tests provide inert effects.
internal class BaiMeterNativeEffects
{
    internal virtual bool CloseHandle(IntPtr handle) { return BaiMeterWin32.CloseHandle(handle); }
    internal virtual bool Terminate(IntPtr process) { return BaiMeterWin32.TerminateProcess(process, 97); }
    internal virtual uint Wait(IntPtr process, uint milliseconds) { return BaiMeterWin32.WaitForSingleObject(process, milliseconds); }
    internal virtual void DeleteAttributes(IntPtr value) { BaiMeterWin32.DeleteProcThreadAttributeList(value); }
    internal virtual void FreeAllocation(IntPtr value) { Marshal.FreeHGlobal(value); }
    internal virtual string WindowsDirectory()
    {
        var windows = new StringBuilder(32768);
        uint count = BaiMeterWin32.GetWindowsDirectoryW(windows, (uint)windows.Capacity);
        BaiMeterProtocol.Require(count > 0 && count < windows.Capacity); return windows.ToString();
    }
    internal virtual bool Create(string application, uint flags, IntPtr environment, string runtimeRoot,
        ref BaiMeterWin32.StartupInfoEx startup, out BaiMeterWin32.ProcessInformation result)
    {
        return BaiMeterWin32.CreateProcessW(application,
            new StringBuilder("\"" + application + "\" --bvp-meter-worker-v1"),
            IntPtr.Zero, IntPtr.Zero, true, flags, environment, runtimeRoot, ref startup, out result);
    }
    internal virtual void QueueCleanup(Action action)
    {
        var thread = new Thread(delegate() { action(); });
        thread.IsBackground = true; thread.Name = "bvp-c1-owned-cleanup"; thread.Start();
    }
}

internal sealed class BaiMeterNativeWindows : IBaiMeterWindowsOps
{
    private readonly Func<bool> current;
    private readonly BaiMeterNativeEffects effects;
    internal BaiMeterNativeWindows(Func<bool> current) : this(current, new BaiMeterNativeEffects()) { }
    internal BaiMeterNativeWindows(Func<bool> current, BaiMeterNativeEffects effects)
    { this.current = current; this.effects = effects; pins = new BaiMeterPinLease(effects.CloseHandle); }
    private readonly HashSet<IntPtr> handles = new HashSet<IntPtr>();
    private readonly BaiMeterPinLease pins;
    private IntPtr parentInput, parentOutput, parentError, childInput, childOutput, childError;
    private IntPtr attributes, inheritedArray, job;
    private bool attributeInitialized;
    private BaiMeterProcessIdentity ownedChild;
    private string root;
    private int cleanupStarted;
    private bool childExited, returnedProcessClosed, returnedThreadClosed, graceAttempted;
    private volatile string cleanupState = "IDLE";
    private static readonly object pendingGate = new object();
    private static readonly HashSet<BaiMeterNativeWindows> pendingCleanup = new HashSet<BaiMeterNativeWindows>();

    private static bool ValidHandle(IntPtr handle) { return handle.ToInt64() > 0; }
    private IntPtr Own(IntPtr handle)
    {
        BaiMeterProtocol.Require(ValidHandle(handle) && handles.Add(handle));
        return handle;
    }
    private void CloseOwned(IntPtr handle)
    {
        if (handle != IntPtr.Zero && handles.Contains(handle)) {
            BaiMeterProtocol.Require(effects.CloseHandle(handle)); handles.Remove(handle);
            MarkReturnedClosed(handle);
        }
    }
    private void MarkReturnedClosed(IntPtr handle)
    {
        if (ownedChild == null) return;
        if (handle == ownedChild.Process) returnedProcessClosed = true;
        if (handle == ownedChild.Thread) returnedThreadClosed = true;
    }
    private static string FinalPath(IntPtr handle, out BaiMeterWin32.FileIdInfo identity, out uint attributes)
    {
        var path = new StringBuilder(32768);
        uint count = BaiMeterWin32.GetFinalPathNameByHandleW(handle, path, (uint)path.Capacity, 0);
        BaiMeterWin32.FileInfo info = default(BaiMeterWin32.FileInfo);
        identity = default(BaiMeterWin32.FileIdInfo);
        BaiMeterProtocol.Require(count > 0 && count < path.Capacity
            && BaiMeterWin32.GetFileInformationByHandle(handle, out info)
            && BaiMeterWin32.GetFileInformationByHandleEx(handle, 18, out identity,
                (uint)Marshal.SizeOf(typeof(BaiMeterWin32.FileIdInfo))));
        string value = path.ToString();
        BaiMeterProtocol.Require(value.StartsWith(@"\\?\", StringComparison.Ordinal)
            && !value.StartsWith(@"\\?\UNC\", StringComparison.Ordinal));
        attributes = info.Attributes; return value.Substring(4);
    }
    private static byte[] FileHash(IntPtr handle)
    {
        BaiMeterProtocol.Require(BaiMeterWin32.SetFilePointerEx(handle, 0, IntPtr.Zero, 0));
        byte[] digest;
        using (var stream = new FileStream(new SafeFileHandle(handle, false), FileAccess.Read, 65536, false))
        using (var sha = SHA256.Create()) digest = sha.ComputeHash(stream);
        BaiMeterProtocol.Require(BaiMeterWin32.SetFilePointerEx(handle, 0, IntPtr.Zero, 0));
        return digest;
    }
    private BaiMeterFilePin Pin(string path, bool directory, byte[] expected)
    {
        IntPtr handle = BaiMeterWin32.CreateFileW(path, directory ? 0x80U : 0x80000000U,
            directory ? 3U : 1U, IntPtr.Zero, 3, 0x00200000U | (directory ? 0x02000000U : 0), IntPtr.Zero);
        BaiMeterProtocol.Require(handle != IntPtr.Zero && handle != new IntPtr(-1));
        var pin = new BaiMeterFilePin { Handle = handle, Path = path, Directory = directory, Digest = expected };
        pins.Items.Add(pin);
        BaiMeterProtocol.Require(BaiMeterWin32.SetHandleInformation(handle, 1, 0));
        BaiMeterWin32.FileIdInfo identity; uint attributes;
        string final = FinalPath(handle, out identity, out attributes);
        BaiMeterProtocol.Require(final == path && (attributes & 0x400) == 0
            && ((attributes & 0x10) != 0) == directory);
        pin.Volume = identity.Volume; pin.FileId = identity.Id;
        if (!directory) BaiMeterProtocol.Require(BaiMeterProtocol.Equal(FileHash(handle), expected));
        return pin;
    }
    private void PinAncestors(string path)
    {
        var directories = new List<string>();
        string cursor = path;
        while (cursor != null) {
            directories.Add(cursor);
            var parent = Directory.GetParent(cursor); cursor = parent == null ? null : parent.FullName;
        }
        directories.Reverse();
        foreach (string directory in directories)
            if (!pins.Items.Any(x => x.Directory && x.Path == directory)) Pin(directory, true, null);
    }
    private static void SafeContained(string path, string allowed)
    {
        BaiMeterProtocol.Require(path != null && path.Length >= 4 && Char.IsLetter(path[0])
            && path[1] == ':' && path[2] == '\\' && Path.GetFullPath(path) == path
            && path.StartsWith(allowed.TrimEnd('\\') + "\\", StringComparison.Ordinal)
            && Directory.GetParent(path) != null
            && !String.Equals(Directory.GetParent(path).FullName.TrimEnd('\\'),
                Path.GetPathRoot(path).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase));
        foreach (string part in path.Substring(3).Split('\\'))
            BaiMeterProtocol.Require(part.Length > 0 && part != "." && part != ".."
                && !part.EndsWith(" ", StringComparison.Ordinal) && !part.EndsWith(".", StringComparison.Ordinal)
                && !part.Any(c => c < 32 || "<>:\"|?*".IndexOf(c) >= 0));
    }
    public BaiMeterImageIdentity PinExactBundle()
    {
        BaiMeterProtocol.Require(current() && IntPtr.Size == 8 && BaiMeterBuildIdentity.Files.Length > 0
            && BaiMeterBuildIdentity.Files.Length == BaiMeterBuildIdentity.Digests.Length
            && BaiMeterBuildIdentity.Files.Length <= 4096);
        root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\'));
        string workerRoot = Path.Combine(root, "worker");
        SafeContained(workerRoot, root); PinAncestors(workerRoot);
        var admitted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < BaiMeterBuildIdentity.Files.Length; i++) {
            string relative = BaiMeterBuildIdentity.Files[i];
            string file = Path.Combine(root, relative);
            SafeContained(file, workerRoot);
            BaiMeterProtocol.Require(admitted.Add(file));
            PinAncestors(Path.GetDirectoryName(file));
            Pin(file, false, BaiMeterProtocol.Hex(BaiMeterBuildIdentity.Digests[i]));
        }
        var actual = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var pending = new Stack<string>(); pending.Push(workerRoot);
        int entryCount = 0;
        while (pending.Count > 0) {
            foreach (string entry in Directory.GetFileSystemEntries(pending.Pop())) {
                BaiMeterProtocol.Require(++entryCount <= 8192);
                FileAttributes attributes = File.GetAttributes(entry);
                BaiMeterProtocol.Require((attributes & FileAttributes.ReparsePoint) == 0);
                if ((attributes & FileAttributes.Directory) != 0) {
                    PinAncestors(entry); pending.Push(entry);
                } else BaiMeterProtocol.Require(actual.Add(entry) && admitted.Contains(entry));
            }
        }
        BaiMeterProtocol.Require(actual.SetEquals(admitted));
        string image = Path.Combine(workerRoot, "BAI Meter Worker.exe");
        BaiMeterFilePin imagePin = pins.Items.Single(x => !x.Directory && x.Path == image);
        return new BaiMeterImageIdentity {
            CanonicalImage = image, Volume = imagePin.Volume, ImageFileId = imagePin.FileId,
            ImageSha256 = imagePin.Digest, Pins = pins
        };
    }
    public string CreateContainedUniqueRuntimeRoot()
    {
        string rawTemp = Path.GetTempPath();
        BaiMeterProtocol.Require(rawTemp.Length > 3 && !rawTemp.StartsWith("\\\\", StringComparison.Ordinal));
        string temp = Path.GetFullPath(rawTemp).TrimEnd('\\');
        string runtime = Path.Combine(temp, "bvp-task048-c1-worker-" + Guid.NewGuid().ToString("N"));
        SafeContained(runtime, temp); PinAncestors(temp);
        BaiMeterProtocol.Require(!Directory.Exists(runtime) && !File.Exists(runtime));
        BaiMeterProtocol.Require(BaiMeterWin32.CreateDirectoryW(runtime, IntPtr.Zero));
        Pin(runtime, true, null); return runtime; // Intentional residual, never auto-cleaned.
    }
    public void CreatePrivatePipes()
    {
        var security = new BaiMeterWin32.SecurityAttributes {
            Length = Marshal.SizeOf(typeof(BaiMeterWin32.SecurityAttributes)), Inherit = 1
        };
        IntPtr read, write;
        BaiMeterProtocol.Require(BaiMeterWin32.CreatePipe(out read, out write, ref security, 65536));
        childInput = Own(read); parentInput = Own(write);
        BaiMeterProtocol.Require(BaiMeterWin32.CreatePipe(out read, out write, ref security, 65536));
        parentOutput = Own(read); childOutput = Own(write);
        BaiMeterProtocol.Require(BaiMeterWin32.CreatePipe(out read, out write, ref security, 65536));
        parentError = Own(read); childError = Own(write);
        foreach (IntPtr handle in new[] { parentInput, parentOutput, parentError })
            BaiMeterProtocol.Require(BaiMeterWin32.SetHandleInformation(handle, 1, 0));
    }
    public void PrepareHandleList(uint attribute)
    {
        BaiMeterProtocol.Require(attribute == BaiMeterSuspendedLauncher.PROC_THREAD_ATTRIBUTE_HANDLE_LIST);
        UIntPtr size = UIntPtr.Zero;
        BaiMeterWin32.InitializeProcThreadAttributeList(IntPtr.Zero, 1, 0, ref size);
        BaiMeterProtocol.Require(size.ToUInt64() > 0 && size.ToUInt64() <= 65536);
        attributes = Marshal.AllocHGlobal((int)size.ToUInt64());
        BaiMeterProtocol.Require(BaiMeterWin32.InitializeProcThreadAttributeList(attributes, 1, 0, ref size));
        attributeInitialized = true;
        inheritedArray = Marshal.AllocHGlobal(IntPtr.Size * 3);
        Marshal.Copy(new[] { childInput, childOutput, childError }, 0, inheritedArray, 3);
        BaiMeterProtocol.Require(BaiMeterWin32.UpdateProcThreadAttribute(attributes, 0, new UIntPtr(attribute),
            inheritedArray, new UIntPtr((uint)(IntPtr.Size * 3)), IntPtr.Zero, IntPtr.Zero));
    }
    public BaiMeterProcessIdentity CreateProcessW(string application, uint flags, string runtimeRoot)
    {
        BaiMeterProtocol.Require(current() && ownedChild == null && cleanupStarted == 0);
        var startup = new BaiMeterWin32.StartupInfoEx();
        startup.Info.Cb = (uint)Marshal.SizeOf(typeof(BaiMeterWin32.StartupInfoEx));
        startup.Info.Flags = 0x100;
        startup.Info.Stdin = childInput; startup.Info.Stdout = childOutput; startup.Info.Stderr = childError;
        startup.Attributes = attributes;
        string win = effects.WindowsDirectory();
        BaiMeterProtocol.Require(System.Text.RegularExpressions.Regex.IsMatch(win, @"\A[A-Z]:\\[A-Za-z0-9 _-]+\z"));
        string environment = "PYTHONDONTWRITEBYTECODE=1\0PYTHONNOUSERSITE=1\0SystemRoot=" + win
            + "\0TEMP=" + runtimeRoot + "\0TMP=" + runtimeRoot + "\0WINDIR=" + win + "\0\0";
        var rawOwner = new BaiMeterProcessIdentity(); // Allocate before the native effect.
        IntPtr block = Marshal.StringToHGlobalUni(environment);
        try {
            BaiMeterWin32.ProcessInformation result;
            BaiMeterProtocol.Require(effects.Create(application, flags, block, runtimeRoot, ref startup, out result));
            rawOwner.Process = result.Process; rawOwner.Thread = result.Thread; rawOwner.Pid = result.Pid;
            ownedChild = rawOwner; // Publish BOTH raw handles before any fallible Own/validation.
            Own(result.Process); Own(result.Thread);
            return ownedChild;
        } finally { Marshal.FreeHGlobal(block); }
    }
    private static IntPtr TokenInfo(IntPtr token, int kind)
    {
        uint size;
        BaiMeterWin32.GetTokenInformation(token, kind, IntPtr.Zero, 0, out size);
        BaiMeterProtocol.Require(size > 0 && size <= 65536);
        IntPtr buffer = Marshal.AllocHGlobal((int)size);
        if (!BaiMeterWin32.GetTokenInformation(token, kind, buffer, size, out size)) {
            Marshal.FreeHGlobal(buffer); throw new BaiMeterProtocolException();
        }
        return buffer;
    }
    private static void Token(IntPtr process, BaiMeterProcessIdentity result)
    {
        IntPtr token;
        BaiMeterProtocol.Require(BaiMeterWin32.OpenProcessToken(process, 8, out token));
        try {
            IntPtr user = TokenInfo(token, 1);
            try {
                IntPtr text;
                BaiMeterProtocol.Require(BaiMeterWin32.ConvertSidToStringSidW(Marshal.ReadIntPtr(user), out text));
                try { result.Sid = Marshal.PtrToStringUni(text); } finally { BaiMeterWin32.LocalFree(text); }
            } finally { Marshal.FreeHGlobal(user); }
            IntPtr session = TokenInfo(token, 12), elevation = IntPtr.Zero;
            try {
                elevation = TokenInfo(token, 20);
                result.Session = unchecked((uint)Marshal.ReadInt32(session));
                int elevated = Marshal.ReadInt32(elevation);
                BaiMeterProtocol.Require(elevated == 0 || elevated == 1); result.Elevated = elevated == 1;
            } finally {
                Marshal.FreeHGlobal(session); if (elevation != IntPtr.Zero) Marshal.FreeHGlobal(elevation);
            }
        } finally { BaiMeterProtocol.Require(BaiMeterWin32.CloseHandle(token)); }
    }
    public BaiMeterProcessIdentity ObserveProcess(BaiMeterProcessIdentity receipt)
    {
        var result = new BaiMeterProcessIdentity { Process = receipt.Process, Thread = receipt.Thread };
        result.Pid = BaiMeterWin32.GetProcessId(receipt.Process);
        BaiMeterWin32.FileTime created, exited, kernel, user;
        BaiMeterProtocol.Require(BaiMeterWin32.GetProcessTimes(receipt.Process, out created, out exited, out kernel, out user));
        result.CreationTime = ((long)created.High << 32) | created.Low;
        var path = new StringBuilder(32768); uint size = (uint)path.Capacity;
        BaiMeterProtocol.Require(BaiMeterWin32.QueryFullProcessImageNameW(receipt.Process, 0, path, ref size));
        result.ImagePath = path.ToString();
        IntPtr file = BaiMeterWin32.CreateFileW(result.ImagePath, 0x80000000, 1, IntPtr.Zero, 3, 0x00200000, IntPtr.Zero);
        BaiMeterProtocol.Require(file != IntPtr.Zero && file != new IntPtr(-1));
        try {
            BaiMeterWin32.FileIdInfo identity; uint attributes;
            BaiMeterProtocol.Require(FinalPath(file, out identity, out attributes) == result.ImagePath
                && (attributes & 0x410) == 0);
            result.ImageVolume = identity.Volume; result.ImageFileId = identity.Id;
        } finally { BaiMeterProtocol.Require(BaiMeterWin32.CloseHandle(file)); }
        Token(receipt.Process, result); return result;
    }
    public void RevalidatePins(BaiMeterImageIdentity unused)
    {
        foreach (BaiMeterFilePin pin in pins.Items) {
            BaiMeterWin32.FileIdInfo identity; uint attributes;
            BaiMeterProtocol.Require(FinalPath(pin.Handle, out identity, out attributes) == pin.Path
                && identity.Volume == pin.Volume && BaiMeterProtocol.Equal(identity.Id, pin.FileId)
                && (attributes & 0x400) == 0 && ((attributes & 0x10) != 0) == pin.Directory);
            if (!pin.Directory) BaiMeterProtocol.Require(BaiMeterProtocol.Equal(FileHash(pin.Handle), pin.Digest));
        }
    }
    public void CheckCurrentUserSidSession(BaiMeterProcessIdentity child)
    {
        var current = new BaiMeterProcessIdentity(); Token(BaiMeterWin32.GetCurrentProcess(), current);
        BaiMeterProtocol.Require(!current.Elevated && !child.Elevated && child.Sid == current.Sid && child.Session == current.Session);
    }
    public void AssignOwnedWorkerJob(BaiMeterProcessIdentity child, uint flags, uint activeProcessLimit)
    {
        BaiMeterProtocol.Require(flags == 0x2008 && activeProcessLimit == 1);
        job = Own(BaiMeterWin32.CreateJobObjectW(IntPtr.Zero, null));
        BaiMeterProtocol.Require(BaiMeterWin32.SetHandleInformation(job, 1, 0));
        var limits = new BaiMeterWin32.JobExtended();
        limits.Basic.Flags = flags; limits.Basic.ActiveLimit = activeProcessLimit;
        BaiMeterProtocol.Require(BaiMeterWin32.SetInformationJobObject(job, 9, ref limits,
            (uint)Marshal.SizeOf(typeof(BaiMeterWin32.JobExtended))));
        BaiMeterProtocol.Require(BaiMeterWin32.AssignProcessToJobObject(job, child.Process));
    }
    public uint ResumeThread(IntPtr thread)
    { BaiMeterProtocol.Require(current()); return BaiMeterWin32.ResumeThread(thread); }
    public void CloseParentCopiesOfChildPipeEndsAndAttributes()
    {
        bool complete = TryAction(() => CloseOwned(childInput));
        complete = TryAction(() => CloseOwned(childOutput)) & complete;
        complete = TryAction(() => CloseOwned(childError)) & complete;
        if (attributeInitialized)
            complete = TryAction(() => { effects.DeleteAttributes(attributes); attributeInitialized = false; }) & complete;
        // A failed deletion retains its allocation and handle-array storage.
        if (!attributeInitialized) {
            if (attributes != IntPtr.Zero)
                complete = TryAction(() => { effects.FreeAllocation(attributes); attributes = IntPtr.Zero; }) & complete;
            if (inheritedArray != IntPtr.Zero)
                complete = TryAction(() => { effects.FreeAllocation(inheritedArray); inheritedArray = IntPtr.Zero; }) & complete;
        }
        BaiMeterProtocol.Require(complete);
    }
    public void WritePrivateBootstrap(byte[] bytes)
    {
        BaiMeterProtocol.Require(current());
        using (var output = new FileStream(new SafeFileHandle(parentInput, false), FileAccess.Write, 4096, false)) {
            output.Write(bytes, 0, bytes.Length); output.Flush();
        }
    }
    public IBaiMeterOwnedWorker CompleteOwnedWorker(BaiMeterProcessIdentity child, BaiMeterImageIdentity image, string runtimeRoot, byte[] bootstrapHash)
    {
        CloseOwned(child.Thread);
        return new BaiMeterNativeOwnedWorker(this, parentOutput, parentInput, parentError, bootstrapHash);
    }
    private void FinishCleanup()
    {
        bool complete = true;
        foreach (IntPtr handle in handles.ToArray()) complete = TryAction(() => CloseOwned(handle)) & complete;
        complete = TryAction(() => CloseReturned(false)) & complete;
        complete = TryAction(() => CloseReturned(true)) & complete;
        complete = TryAction(pins.Dispose) & complete;
        BaiMeterProtocol.Require(complete);
    }
    private void CloseReturned(bool primary)
    {
        if (ownedChild == null || (primary ? returnedProcessClosed : returnedThreadClosed)) return;
        IntPtr handle = primary ? ownedChild.Process : ownedChild.Thread;
        if (!ValidHandle(handle)) {
            if (primary) returnedProcessClosed = true; else returnedThreadClosed = true;
            return;
        }
        if (handles.Contains(handle)) CloseOwned(handle);
        else { BaiMeterProtocol.Require(effects.CloseHandle(handle)); MarkReturnedClosed(handle); }
    }
    private static bool TryAction(Action action)
    {
        try { action(); return true; } catch (Exception) { return false; }
    }
    private bool WaitExact()
    {
        try { return effects.Wait(ownedChild.Process, 1000) == 0; }
        catch (Exception) { return false; }
    }
    private bool CleanupRound(bool resumeAttempted, bool graceful)
    {
        bool auxiliary = TryAction(CloseParentCopiesOfChildPipeEndsAndAttributes);
        auxiliary = TryAction(() => CloseOwned(parentInput)) & auxiliary;
        if (ownedChild != null && !childExited) {
            if (!ValidHandle(ownedChild.Process)) return false;
            if (!resumeAttempted) {
                TryAction(() => BaiMeterProtocol.Require(effects.Terminate(ownedChild.Process)));
            } else {
                if (graceful && !graceAttempted) { graceAttempted = true; childExited = WaitExact(); }
                if (!childExited) TryAction(() => CloseOwned(job)); // Only this pure-worker Job.
            }
            // Always attempt exact exit observation, even if pipe/attribute/kill failed.
            if (!childExited) childExited = WaitExact();
            if (!childExited) return false;
        }
        return TryAction(FinishCleanup) & auxiliary;
    }
    private void StartCleanup(bool resumeAttempted, bool graceful)
    {
        if (Interlocked.Exchange(ref cleanupStarted, 1) != 0) return;
        cleanupState = "CLEANUP_PENDING";
        lock (pendingGate) pendingCleanup.Add(this); // Retain exact raw receipt even if scheduling fails.
        Action attempt = delegate {
            while (true) {
                bool complete = false;
                TryAction(() => { complete = CleanupRound(resumeAttempted, graceful); });
                if (complete) {
                    cleanupState = "CLOSED";
                    lock (pendingGate) pendingCleanup.Remove(this);
                    return;
                }
                Thread.Sleep(100);
            }
        };
        bool finished = false;
        TryAction(() => { finished = CleanupRound(resumeAttempted, graceful); });
        if (finished) {
            cleanupState = "CLOSED"; lock (pendingGate) pendingCleanup.Remove(this); return;
        }
        TryAction(() => effects.QueueCleanup(attempt));
    }
    public void CleanupOwnedFailure(BaiMeterProcessIdentity child, bool resumeAttempted)
    {
        // Only our raw CreateProcess success can authorize a process effect.
        // The caller's optional copy is not alternate ownership authority.
        StartCleanup(resumeAttempted, false);
    }
    internal void ClosePureWorker()
    {
        StartCleanup(true, true);
    }

    private sealed class CleanupTestEffects : BaiMeterNativeEffects
    {
        internal readonly List<string> Calls = new List<string>();
        internal string Fault;
        internal bool Exited, HoldExit, Failed;
        internal Action Queued;
        internal override string WindowsDirectory() { return @"C:\Windows"; }
        internal override bool Create(string application, uint flags, IntPtr environment, string runtimeRoot,
            ref BaiMeterWin32.StartupInfoEx startup, out BaiMeterWin32.ProcessInformation result)
        {
            BaiMeterProtocol.Require((flags & BaiMeterSuspendedLauncher.CREATE_SUSPENDED) != 0);
            Calls.Add("create");
            result = new BaiMeterWin32.ProcessInformation {
                Process = new IntPtr(700), Thread = Fault == "thread-invalid" ? IntPtr.Zero : new IntPtr(701), Pid = 77
            };
            return true;
        }
        private void FailOnce(bool matched)
        { if (matched && !Failed) { Failed = true; throw new InvalidOperationException("injected cleanup fault"); } }
        internal override bool CloseHandle(IntPtr handle)
        {
            long value = handle.ToInt64(); Calls.Add("close:" + value);
            FailOnce((Fault == "pipe" || Fault == "resume-pipe") && value == 101
                || (Fault == "parent-pipe" || Fault == "graceful-parent-pipe") && value == 104);
            if (value == 109 && !HoldExit) Exited = true;
            if (value == 700 || value == 701 || value == 120) BaiMeterProtocol.Require(Exited);
            return true;
        }
        internal override bool Terminate(IntPtr process)
        {
            BaiMeterProtocol.Require(process == new IntPtr(700)); Calls.Add("terminate");
            FailOnce(Fault == "terminate-failure");
            if (!HoldExit) Exited = true;
            return true;
        }
        internal override uint Wait(IntPtr process, uint milliseconds)
        {
            BaiMeterProtocol.Require(process == new IntPtr(700) && milliseconds <= 1000);
            Calls.Add("wait-attempt"); FailOnce(Fault == "wait-failure");
            Calls.Add(Exited ? "wait:0" : "wait:258"); return Exited ? 0U : 258U;
        }
        internal override void DeleteAttributes(IntPtr value)
        { Calls.Add("attributes"); FailOnce(Fault == "attributes" || Fault == "resume-attributes"); }
        internal override void FreeAllocation(IntPtr value)
        { Calls.Add("free"); FailOnce(Fault == "free"); }
        internal override void QueueCleanup(Action action) { Calls.Add("queue"); Queued = action; }
    }

    // Inert effects drive the same concrete ownership and cleanup methods. No
    // real Win32 process/pipe/file, OBS, microphone or thread is created here.
    internal static void AssertCleanupContracts()
    {
        foreach (string fault in new[] { "thread-invalid", "pipe", "parent-pipe", "attributes", "free",
            "resume-pipe", "resume-attributes", "resume-uncertain", "graceful-parent-pipe",
            "delayed-exit", "terminate-failure", "wait-failure" }) {
            var fake = new CleanupTestEffects { Fault = fault, HoldExit = fault == "delayed-exit" };
            var owner = new BaiMeterNativeWindows(() => true, fake);
            owner.childInput = owner.Own(new IntPtr(101)); owner.childOutput = owner.Own(new IntPtr(102));
            owner.childError = owner.Own(new IntPtr(103)); owner.parentInput = owner.Own(new IntPtr(104));
            owner.parentOutput = owner.Own(new IntPtr(105)); owner.parentError = owner.Own(new IntPtr(106));
            owner.job = owner.Own(new IntPtr(109));
            owner.attributes = new IntPtr(800); owner.inheritedArray = new IntPtr(801); owner.attributeInitialized = true;
            owner.pins.Items.Add(new BaiMeterFilePin { Handle = new IntPtr(120) });
            bool rejected = false;
            try { owner.CreateProcessW(@"C:\Users\fixture\worker.exe", 0x80404, @"C:\Users\fixture\runtime"); }
            catch (BaiMeterProtocolException) { rejected = true; }
            BaiMeterProtocol.Require(rejected == (fault == "thread-invalid") && owner.ownedChild != null
                && owner.ownedChild.Process == new IntPtr(700));
            bool resumed = fault.StartsWith("resume-", StringComparison.Ordinal)
                || fault.StartsWith("graceful-", StringComparison.Ordinal);
            if (fault.StartsWith("graceful-", StringComparison.Ordinal)) owner.ClosePureWorker();
            else owner.CleanupOwnedFailure(null, resumed);
            BaiMeterProtocol.Require(fake.Calls.Contains("wait-attempt"));
            BaiMeterProtocol.Require(resumed ? !fake.Calls.Contains("terminate")
                && fake.Calls.Contains("close:109") : fake.Calls.Contains("terminate"));
            if (fault == "delayed-exit" || fault == "wait-failure" || fault == "terminate-failure")
                BaiMeterProtocol.Require(owner.cleanupState == "CLEANUP_PENDING"
                    && owner.pins.Items[0].Handle == new IntPtr(120)
                    && !fake.Calls.Contains("close:700"));
            fake.HoldExit = false; fake.Exited = true;
            if (fake.Queued != null) fake.Queued();
            BaiMeterProtocol.Require(owner.cleanupState == "CLOSED" && owner.handles.Count == 0
                && owner.pins.Items.All(x => x.Handle == IntPtr.Zero));
            BaiMeterProtocol.Require(fake.Calls.IndexOf("wait:0") < fake.Calls.IndexOf("close:120"));
            int calls = fake.Calls.Count; owner.ClosePureWorker(); BaiMeterProtocol.Require(fake.Calls.Count == calls);
        }
        var foreign = new CleanupTestEffects();
        var empty = new BaiMeterNativeWindows(() => true, foreign);
        empty.CleanupOwnedFailure(new BaiMeterProcessIdentity { Process = new IntPtr(999), Thread = new IntPtr(998) }, false);
        BaiMeterProtocol.Require(!foreign.Calls.Contains("terminate") && !foreign.Calls.Contains("wait-attempt")
            && empty.cleanupState == "CLOSED");
    }
}

internal sealed class BaiMeterNativeOwnedWorker : IBaiMeterOwnedWorker
{
    private readonly BaiMeterNativeWindows owner;
    public Stream Reader { get; private set; }
    public Stream Writer { get; private set; }
    public Stream StderrReader { get; private set; }
    public byte[] BootstrapSha256 { get; private set; }
    internal BaiMeterNativeOwnedWorker(BaiMeterNativeWindows owner, IntPtr read, IntPtr write, IntPtr error, byte[] digest)
    {
        this.owner = owner; BootstrapSha256 = (byte[])digest.Clone();
        Reader = new FileStream(new SafeFileHandle(read, false), FileAccess.Read, 4096, false);
        Writer = new FileStream(new SafeFileHandle(write, false), FileAccess.Write, 4096, false);
        StderrReader = new FileStream(new SafeFileHandle(error, false), FileAccess.Read, 4096, false);
    }
    public void ClosePureWorker() { owner.ClosePureWorker(); }
}

internal sealed class BaiMeterParentInput : Stream
{
    private readonly IntPtr handle;
    private volatile bool cancelled;
    internal BaiMeterParentInput()
    {
        handle = BaiMeterWin32.GetStdHandle(-10);
        BaiMeterProtocol.Require(handle != IntPtr.Zero && handle != new IntPtr(-1)
            && BaiMeterWin32.GetFileType(handle) == 3
            && BaiMeterWin32.SetHandleInformation(handle, 1, 0));
    }
    internal void Cancel() { cancelled = true; }
    public override int Read(byte[] buffer, int offset, int count)
    {
        BaiMeterProtocol.Require(buffer != null && offset >= 0 && count >= 0 && offset <= buffer.Length - count);
        if (count == 0) return 0;
        while (!cancelled) {
            uint available;
            if (!BaiMeterWin32.PeekNamedPipe(handle, IntPtr.Zero, 0, IntPtr.Zero, out available, IntPtr.Zero)) {
                int error = Marshal.GetLastWin32Error();
                if (error == 109 || error == 232) return 0;
                throw new BaiMeterProtocolException();
            }
            if (available == 0) { Thread.Sleep(10); continue; }
            byte[] data = new byte[Math.Min((uint)count, available)];
            uint read;
            BaiMeterProtocol.Require(BaiMeterWin32.ReadFile(handle, data, (uint)data.Length, out read, IntPtr.Zero));
            Buffer.BlockCopy(data, 0, buffer, offset, (int)read); return (int)read;
        }
        return 0;
    }
    public override bool CanRead { get { return true; } }
    public override bool CanSeek { get { return false; } }
    public override bool CanWrite { get { return false; } }
    public override long Length { get { throw new NotSupportedException(); } }
    public override long Position { get { throw new NotSupportedException(); } set { throw new NotSupportedException(); } }
    public override void Flush() { }
    public override long Seek(long value, SeekOrigin origin) { throw new NotSupportedException(); }
    public override void SetLength(long value) { throw new NotSupportedException(); }
    public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
}

// Tap only the first complete READY/BOOTSTRAP_REJECTED frame. Reads still return
// each fragment immediately so the frozen bridge's partial-frame watchdog works.
internal sealed class BaiMeterReadyRelay : Stream
{
    private readonly Stream inner;
    private readonly Action<BaiMeterFrame> firstFrame;
    private readonly MemoryStream pending = new MemoryStream();
    private bool first = true;
    internal BaiMeterReadyRelay(Stream inner, Action<BaiMeterFrame> firstFrame)
    { this.inner = inner; this.firstFrame = firstFrame; }
    public override int Read(byte[] buffer, int offset, int count)
    {
        int read = inner.Read(buffer, offset, count);
        if (first && read > 0) {
            BaiMeterProtocol.Require(pending.Length + read <= BaiMeterProtocol.MaxFrameBytes);
            pending.Write(buffer, offset, read);
            byte[] bytes = pending.ToArray();
            if (bytes.Length >= 4) {
                uint size = BaiMeterProtocol.U32(bytes, 0);
                BaiMeterProtocol.Require(size >= 48 && size <= BaiMeterProtocol.MaxFrameBytes - 4);
                if (bytes.Length == size + 4) {
                    firstFrame(BaiMeterProtocol.Parse(bytes)); first = false; pending.Dispose();
                } else BaiMeterProtocol.Require(bytes.Length < size + 4);
            }
        }
        return read;
    }
    public override bool CanRead { get { return true; } }
    public override bool CanSeek { get { return false; } }
    public override bool CanWrite { get { return false; } }
    public override long Length { get { throw new NotSupportedException(); } }
    public override long Position { get { throw new NotSupportedException(); } set { throw new NotSupportedException(); } }
    public override void Flush() { }
    public override long Seek(long value, SeekOrigin origin) { throw new NotSupportedException(); }
    public override void SetLength(long value) { throw new NotSupportedException(); }
    public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
}
internal sealed class BaiMeterRelayedWorker : IBaiMeterOwnedWorker
{
    private readonly IBaiMeterOwnedWorker owned;
    public Stream Reader { get; private set; }
    public Stream Writer { get { return owned.Writer; } }
    public Stream StderrReader { get { return owned.StderrReader; } }
    public byte[] BootstrapSha256 { get { return owned.BootstrapSha256; } }
    internal BaiMeterRelayedWorker(IBaiMeterOwnedWorker owned, Action<BaiMeterFrame> ready)
    { this.owned = owned; Reader = new BaiMeterReadyRelay(owned.Reader, ready); }
    public void ClosePureWorker() { owned.ClosePureWorker(); }
}

internal static class BaiMeterScalarWindow
{
    private static void Metric(BinaryWriter writer, double amplitude, long samples)
    {
        byte state; double db = 0;
        if (samples <= 0) state = 2;
        else if (Double.IsNaN(amplitude) || amplitude < 0) state = 4;
        else if (Double.IsInfinity(amplitude)) state = 3;
        else if (amplitude == 0) state = 1;
        else { state = 0; db = 20.0 * Math.Log10(amplitude); }
        writer.Write(state); writer.Write(db);
    }
    internal static byte[] Create(Guid selection, Guid session, Guid consumer, Guid view, ulong sequence,
        AudioMeterSnapshot window, long samples, long clips, bool paused)
    {
        using (var stream = new MemoryStream())
        using (var writer = new BinaryWriter(stream)) {
            writer.Write(BaiMeterProtocol.UuidBytes(selection)); writer.Write(BaiMeterProtocol.UuidBytes(session));
            writer.Write(BaiMeterProtocol.UuidBytes(consumer)); writer.Write(BaiMeterProtocol.UuidBytes(view));
            writer.Write(sequence); writer.Write((byte)1); writer.Write((byte)(paused ? 1 : 0));
            writer.Write(BaiMeterProtocol.LegacyLossUnknown); writer.Write((byte)0);
            bool windowValid = new[] { window.Packet.SampleCount, window.Packet.NonFiniteSampleCount,
                window.Packet.ClipSampleCount }.All(x => x >= 0 && (ulong)x <= BaiMeterProtocol.MaxInteger)
                && window.Packet.ClipSampleCount <= window.Packet.SampleCount;
            writer.Write((byte)(windowValid ? 0 : 1));
            writer.Write(windowValid ? (ulong)window.Packet.SampleCount : 0UL);
            writer.Write(windowValid ? (ulong)window.Packet.NonFiniteSampleCount : 0UL);
            writer.Write(windowValid ? (ulong)window.Packet.ClipSampleCount : 0UL);
            bool sessionValid = samples >= 0 && clips >= 0 && clips <= samples
                && (ulong)samples <= BaiMeterProtocol.MaxInteger && (ulong)clips <= BaiMeterProtocol.MaxInteger;
            writer.Write((byte)(sessionValid ? 0 : 1));
            writer.Write(sessionValid ? (ulong)samples : 0UL); writer.Write(sessionValid ? (ulong)clips : 0UL);
            Metric(writer, window.Packet.Peak, window.Packet.SampleCount);
            Metric(writer, window.Packet.Rms, window.Packet.SampleCount);
            Metric(writer, window.SessionMaximum, samples);
            return BaiMeterProtocol.LegacyWindow(stream.ToArray());
        }
    }
}

internal sealed class BaiMeterManagedSession : IDisposable
{
    private readonly object gate = new object();
    private readonly object parentWriteGate = new object();
    private readonly IBaiMeterClock clock = new BaiMeterMonotonicClock();
    private BaiMeterRuntimeBridge bridge;
    private BaiMeterParentInput input;
    private Stream parentOutput;
    private BaiMeterFrame bootstrap;
    private Guid session = Guid.NewGuid(), consumer = Guid.NewGuid(), view = Guid.NewGuid();
    private ulong windowSequence;
    private volatile bool closed;
    private bool started, readyForwarded;
    private string reason = "NOT_CONNECTED";
    private long partialSince = -1, startedAt;
    private System.Threading.Timer deadline;

    internal void Start()
    {
        lock (gate) {
            BaiMeterProtocol.Require(!started); started = true; reason = "OPENING"; startedAt = clock.Now;
        }
        deadline = new System.Threading.Timer(CheckDeadline, null, 25, 25);
        var thread = new Thread(ReadMain); thread.IsBackground = true; thread.Name = "bvp-c1-parent";
        thread.Start();
    }
    private void CheckDeadline(object unused)
    {
        bool expired;
        lock (gate) {
            long now = clock.Now;
            expired = !closed && ((bootstrap == null && now - startedAt >= clock.Frequency * 5)
                || (partialSince >= 0 && now - partialSince >= clock.Frequency));
        }
        if (expired) Stop("TRANSPORT_TIMEOUT");
    }
    private void Partial(bool value) { lock (gate) partialSince = value ? clock.Now : -1; }
    private void ReadMain()
    {
        IBaiMeterOwnedWorker pendingWorker = null;
        try {
            input = new BaiMeterParentInput();
            if (closed) return;
            IntPtr output = BaiMeterWin32.GetStdHandle(-11);
            BaiMeterProtocol.Require(output != IntPtr.Zero && output != new IntPtr(-1)
                && BaiMeterWin32.GetFileType(output) == 3 && BaiMeterWin32.SetHandleInformation(output, 1, 0));
            // This process owns its inherited parent-link stdout, not a worker handle.
            parentOutput = new FileStream(new SafeFileHandle(output, true), FileAccess.Write, 4096, false);
            if (closed) return;
            byte[] raw = BaiMeterProtocol.Read(input, Partial);
            BaiMeterFrame initial = BaiMeterProtocol.Parse(raw);
            BaiMeterProtocol.Require(initial.Type == 1 && initial.Sequence == 1);
            lock (gate) { if (closed) return; bootstrap = initial; }
            pendingWorker = BaiMeterSuspendedLauncher.Launch(
                new BaiMeterNativeWindows(() => !closed), raw);
            lock (gate) {
                if (closed) return;
                bridge = new BaiMeterRuntimeBridge(new BaiMeterRelayedWorker(pendingWorker, ForwardReady), raw, clock);
                pendingWorker = null; // Bridge now owns all cleanup, including Start failures.
                bridge.Start();
            }
            ulong sequence = 1;
            while (!closed) {
                raw = BaiMeterProtocol.Read(input, Partial);
                if (raw == null) { Stop("PARENT_EXIT"); return; }
                BaiMeterFrame control = BaiMeterProtocol.Parse(raw);
                BaiMeterProtocol.Require(control.Sequence == ++sequence
                    && BaiMeterProtocol.Equal(control.Nonce, initial.Nonce)
                    && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(control.Body, 0, 16),
                        BaiMeterProtocol.Slice(initial.Body, 0, 16)));
                if (control.Type == 5) { Stop("PARENT_EXIT"); return; }
                BaiMeterProtocol.Require(control.Type == 4
                    && (control.Body[64] == 1 || control.Body[64] == 2 || control.Body[64] == 7));
                Stop("PROJECT_CHANGED"); return;
            }
        } catch (Exception) { Stop("BOOTSTRAP_REJECTED"); }
        finally {
            if (pendingWorker != null) {
                IBaiMeterOwnedWorker abandoned = pendingWorker;
                ThreadPool.QueueUserWorkItem(delegate {
                    try { abandoned.ClosePureWorker(); } catch (Exception) { }
                });
            }
            if (input != null) input.Cancel();
            CloseParentOutput();
        }
    }
    private void ForwardReady(BaiMeterFrame result)
    {
        BaiMeterFrame request;
        lock (gate) { if (closed) return; request = bootstrap; BaiMeterProtocol.Require(!readyForwarded); }
        byte[] body = result.Body;
        BaiMeterProtocol.Require(result.Type == 3 && result.Sequence == 1
            && BaiMeterProtocol.Equal(result.Nonce, request.Nonce)
            && BaiMeterProtocol.U16(body, 2) == 1 && BaiMeterProtocol.U64(body, 4) == 1
            && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(body, 12, 32), BaiMeterProtocol.Hash(request.Wire))
            && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(body, 44, 16), BaiMeterProtocol.Slice(request.Body, 0, 16)));
        if (body[0] == 0) {
            BaiMeterProtocol.Require(BaiMeterProtocol.U64(body, 60) == BaiMeterProtocol.U64(request.Body, 40)
                && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(body, 68, 32), BaiMeterProtocol.Slice(request.Body, 48, 32))
                && BaiMeterProtocol.U64(body, 100) == BaiMeterProtocol.U64(request.Body, 16)
                && BaiMeterProtocol.Equal(BaiMeterProtocol.Slice(body, 108, 16), BaiMeterProtocol.Slice(request.Body, 24, 16)));
        } else BaiMeterProtocol.Require(body[0] == 2 && body[1] == 1);
        lock (parentWriteGate) {
            if (closed) return;
            parentOutput.Write(result.Wire, 0, result.Wire.Length); parentOutput.Flush();
        }
        lock (gate) readyForwarded = true;
    }
    internal void Offer(AudioMeterSnapshot window, long samples, long clips, bool paused)
    {
        lock (gate) {
            if (closed || bridge == null) return;
            try {
                bridge.OfferNativeV1(BaiMeterScalarWindow.Create(
                    BaiMeterProtocol.GuidAt(bootstrap.Body, 0), session, consumer, view,
                    ++windowSequence, window, samples, clips, paused));
            } catch (Exception) { Stop("PROTOCOL_FAILURE"); }
        }
    }
    internal void Invalidate(byte why, bool paused)
    {
        lock (gate) {
            if (closed) return;
            if (why == 8) session = Guid.NewGuid();
            consumer = Guid.NewGuid(); view = Guid.NewGuid(); windowSequence = 0;
            if (bridge != null) {
                try { bridge.Invalidate(session, consumer, view, why, paused); }
                catch (Exception) { Stop("PROTOCOL_FAILURE"); }
            }
        }
    }
    internal BaiMeterDisplay Snapshot()
    {
        lock (gate) {
            if (closed || bridge == null) return new BaiMeterDisplay(false, 0, reason);
            BaiMeterDisplay display = bridge.Snapshot();
            if (!display.Connected && display.Reason != "NOT_CONNECTED"
                && display.Reason != "WINDOW_PENDING" && display.Reason != "INVALIDATED") {
                Stop(display.Reason); return new BaiMeterDisplay(false, 0, reason);
            }
            return display;
        }
    }
    private void CloseParentOutput()
    {
        lock (parentWriteGate) {
            Stream output = parentOutput; parentOutput = null;
            if (output != null) { try { output.Dispose(); } catch (Exception) { } }
        }
    }
    private void Stop(string code)
    {
        BaiMeterRuntimeBridge previous;
        lock (gate) {
            if (closed) return; closed = true; reason = code; previous = bridge; bridge = null;
        }
        if (input != null) input.Cancel();
        if (previous != null) previous.Dispose();
        // All pipe closure and worker grace happens off UI/capture/emergency paths.
        ThreadPool.QueueUserWorkItem(delegate { CloseParentOutput(); });
        if (deadline != null) deadline.Dispose();
    }
    public void Dispose() { Stop("CLOSED"); }
    internal static string ReasonLabel(string code)
    {
        if (code == "NOT_CONNECTED") return "未接続";
        if (code == "OPENING") return "接続確認中";
        if (code == "CONNECTED_NOT_CLASSIFIED" || code == "WINDOW_PENDING") return "観測窓を確認中";
        if (code == "WINDOW_EXPIRED") return "応答期限を超過";
        if (code == "INVALIDATED" || code == "PROJECT_CHANGED") return "接続条件が変わりました";
        if (code == "P2_REASON_1") return "表示方針が未選択";
        if (code == "P2_REASON_14") return "OBS側の欠落情報は未確認";
        if (code == "P2_REASON_13") return "観測窓に欠落あり";
        if (code == "P2_REASON_15") return "一時停止中";
        if (code == "P2_REASON_16") return "今回の入力なし";
        if (code == "P2_REASON_17") return "選択中の表示方針と照合";
        if (code.StartsWith("P2_REASON_", StringComparison.Ordinal)) return "方針または観測値を確認できません";
        if (code == "C1_STATUS_5") return "前の観測窓を処理中";
        if (code == "BOOTSTRAP_REJECTED") return "Project接続を確認できません";
        if (code == "PARENT_EXIT" || code == "CLOSED") return "メーター接続を終了";
        return "メーター接続を確認できません";
    }
}

internal static class BaiMeterScalarSelfTest
{
    internal static int Run()
    {
        try {
            var selection = Guid.NewGuid(); var session = Guid.NewGuid();
            var consumer = Guid.NewGuid(); var view = Guid.NewGuid();
            var packet = new AudioMeterPacket(4, 2, 1, 100.0, 8.0);
            byte[] value = BaiMeterScalarWindow.Create(selection, session, consumer, view, 1,
                new AudioMeterSnapshot(packet, 9.0), 100, 3, false);
            BaiMeterProtocol.Require(value.Length == 145 && value[74] == 2
                && BaiMeterProtocol.U64(value, 77) == 4 && BaiMeterProtocol.U64(value, 85) == 1
                && BaiMeterProtocol.U64(value, 93) == 2 && BaiMeterProtocol.U64(value, 102) == 100
                && BaiMeterProtocol.U64(value, 110) == 3 && BitConverter.ToDouble(value, 119) > 12.0);
            value = BaiMeterScalarWindow.Create(selection, session, consumer, view, 2,
                new AudioMeterSnapshot(default(AudioMeterPacket), 9.0), 100, 3, true);
            BaiMeterProtocol.Require(value[73] == 1 && value[118] == 2 && value[127] == 2
                && value[136] == 0 && BaiMeterProtocol.U64(value, 110) == 3);
            var silent = new AudioMeterPacket(4, 0, 0, 0, 0);
            value = BaiMeterScalarWindow.Create(selection, session, consumer, view, 3,
                new AudioMeterSnapshot(silent, 0), 4, 0, false);
            BaiMeterProtocol.Require(value[118] == 1 && value[127] == 1 && value[136] == 1);
            value = BaiMeterScalarWindow.Create(selection, session, consumer, view, 4,
                new AudioMeterSnapshot(packet, 9), Int64.MaxValue, 3, false);
            BaiMeterProtocol.Require(value[101] == 1 && BaiMeterProtocol.U64(value, 102) == 0);
            BaiMeterProtocol.Require(Marshal.SizeOf(typeof(BaiMeterWin32.StartupInfo)) == 104
                && Marshal.SizeOf(typeof(BaiMeterWin32.StartupInfoEx)) == 112
                && Marshal.SizeOf(typeof(BaiMeterWin32.SecurityAttributes)) == 24
                && Marshal.SizeOf(typeof(BaiMeterWin32.ProcessInformation)) == 24
                && Marshal.SizeOf(typeof(BaiMeterWin32.FileIdInfo)) == 24
                && Marshal.SizeOf(typeof(BaiMeterWin32.JobExtended)) == 144);
            BaiMeterNativeWindows.AssertCleanupContracts();
            byte[] ready = BaiMeterProtocol.Hex(BaiMeterProtocolSelfTest.Vectors[4].Bytes);
            int forwarded = 0;
            using (var raw = new MemoryStream(ready)) {
                var relay = new BaiMeterReadyRelay(raw, delegate(BaiMeterFrame frame) {
                    BaiMeterProtocol.Require(BaiMeterProtocol.Equal(frame.Wire, ready)); forwarded++;
                });
                byte[] copy = new byte[ready.Length];
                BaiMeterProtocol.Require(relay.Read(copy, 0, 3) == 3 && forwarded == 0);
                BaiMeterProtocol.Require(relay.Read(copy, 3, copy.Length - 3) == copy.Length - 3
                    && forwarded == 1 && BaiMeterProtocol.Equal(copy, ready));
                BaiMeterProtocol.Require(relay.Read(copy, 0, copy.Length) == 0 && forwarded == 1);
            }
            return 0;
        } catch (Exception) { return 96; }
    }
}

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--bvp-meter-protocol-self-test") return BaiMeterProtocolSelfTest.Run();
        if (args.Length == 1 && args[0] == "--bvp-meter-scalar-self-test") return BaiMeterScalarSelfTest.Run();
        if (args.Any(x => x == "--meter-self-test")) return MeterObservationSelfTest.Run();
        if (args.Any(x => x == "--self-test")) return ControllerSelfTest.Run();
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        bool managed = args.Length == 1 && args[0] == "--bvp-meter-managed-v1";
        Application.Run(new CaptureForm(args.Any(x => x == "--acceptance"), managed));
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
    private readonly Label meterAdvisory = new Label();
    private readonly BaiMeterManagedSession meterSession;
    private readonly System.Windows.Forms.Timer advisoryTimer = new System.Windows.Forms.Timer();
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
    private string completedGainSummary;
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

    public CaptureForm(bool acceptance, bool managed = false)
    {
        acceptanceMode = acceptance;
        meterSession = managed ? new BaiMeterManagedSession() : null;
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
            Dock = DockStyle.Fill, ColumnCount = 3, RowCount = 13,
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
        levelValues.Text = "Peak -- / RMS -- / 最大 -- dBFS\n0 dBFS = 基準線 / +値 = 基準超過 / 適正判定 未確定";
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
        meterAdvisory.AutoSize = true;
        meterAdvisory.MaximumSize = new Size(520, 0);
        meterAdvisory.Text = BaiMeterDisplay.ScopeLabel + "\n適正判定 未確定 / 未接続";
        AddRow(table, 12, "判定の状態", meterAdvisory, null);
        table.SetColumnSpan(meterAdvisory, 2);

        Controls.Add(table);
        Controls.Add(status);

        uiTimer.Interval = 250;
        uiTimer.Tick += delegate { RefreshUi(); };
        uiTimer.Start();
        // Read the advisory between 250ms scalar offers; offering a new window
        // invalidates the previous band, so these two refresh paths are separate.
        advisoryTimer.Interval = 25;
        advisoryTimer.Tick += delegate { RefreshMeterAdvisory(); };
        advisoryTimer.Start();
        if (meterSession != null) meterSession.Start();
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
        completedGainSummary = null;
        if (meterSession != null) meterSession.Invalidate(8, false);
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
                    if (meterSession != null) meterSession.Invalidate(6, false);
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
        if (meterSession != null) meterSession.Invalidate(4, true);
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
        if (meterSession != null) meterSession.Invalidate(5, false);
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
        if (meterSession != null) meterSession.Invalidate(6, false);
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
        completedGainSummary = completedGainMeasurement ? FormatGainSummary() : null;
        RefreshUi();
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
        if (meterSession != null) meterSession.Offer(window, samples, clips, paused);
        double livePeak = window.Packet.Peak;
        double liveRms = window.Packet.Rms;
        double livePeakDb = livePeak > 0.0 ? 20.0 * Math.Log10(livePeak) : -60.0;
        double liveRmsDb = liveRms > 0.0 ? 20.0 * Math.Log10(liveRms) : -60.0;
        levelMeter.UpdateLevels(livePeakDb, liveRmsDb, window.Packet.ClipSampleCount > 0, clips > 0);
        levelValues.Text = String.Format(CultureInfo.InvariantCulture,
            "Peak {0} / RMS {1} / 最大 {2} dBFS\n" +
            "clip 今回 {4}（赤バー）/ 累計 {3}（赤枠）\n" +
            "非有限(今回) {5} / {6} / {7}\n" +
            "0 dBFS = 基準線 / +値 = 基準超過 / 適正判定 未確定",
            AudioMeterSnapshot.FormatDbfs(livePeak, window.Packet.SampleCount),
            AudioMeterSnapshot.FormatDbfs(liveRms, window.Packet.SampleCount),
            AudioMeterSnapshot.FormatDbfs(window.SessionMaximum, samples),
            clips, window.Packet.ClipSampleCount, window.Packet.NonFiniteSampleCount,
            paused ? "一時停止" : window.ObservationState, window.RangeState);
        try {
            var root = Path.GetPathRoot(Path.GetFullPath(destination.Text));
            freeSpace.Text = FormatBytes(new DriveInfo(root).AvailableFreeSpace);
        } catch { freeSpace.Text = "未確認"; }
        if (!recording && !String.IsNullOrEmpty(terminalReason))
            detail.Text = CaptureTerminalDisplay.Format(terminalReason, completedGainSummary);
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
        advisoryTimer.Stop();
        if (meterSession != null) meterSession.Dispose();
    }

    private void RefreshMeterAdvisory()
    {
        BaiMeterDisplay display = meterSession == null
            ? new BaiMeterDisplay(false, 0, "NOT_CONNECTED") : meterSession.Snapshot();
        meterAdvisory.Text = BaiMeterDisplay.ScopeLabel + "\n" + display.Label + " / "
            + BaiMeterManagedSession.ReasonLabel(display.Reason);
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
            if (Packet.Peak > AudioMeterScale.MaximumAmplitude) return "表示範囲(+12)超過(今回)";
            if (SessionMaximum > AudioMeterScale.MaximumAmplitude) return "表示範囲(+12)超過(履歴)";
            if (Packet.Peak > 1.0) return "入力範囲外(今回)";
            if (SessionMaximum > 1.0) return "入力範囲外(履歴)";
            return Packet.SampleCount > 0 ? "範囲外の検出なし" : "入力範囲 未観測";
        }
    }

    public static string FormatDbfs(double amplitude, long sampleCount)
    {
        if (sampleCount == 0) return "--";
        return amplitude > 0.0
            ? (20.0 * Math.Log10(amplitude)).ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture)
            : "-∞";
    }
}

// Only the drawing coordinate saturates at +12 dBFS. Numeric readings and
// receipts keep the original float amplitude, including values above this range.
internal static class AudioMeterScale
{
    public const double MinimumDb = -60.0;
    public const double MaximumDb = 12.0;
    public static readonly double MaximumAmplitude = Math.Pow(10.0, MaximumDb / 20.0);

    public static double Clamp(double value)
    {
        if (Double.IsNaN(value) || Double.IsInfinity(value)) return MinimumDb;
        return Math.Max(MinimumDb, Math.Min(MaximumDb, value));
    }

    public static double Position(double value)
    {
        return (Clamp(value) - MinimumDb) / (MaximumDb - MinimumDb);
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
        if (Double.IsNaN(peakDb) || Double.IsInfinity(peakDb) ||
            peakDb < AudioMeterScale.MinimumDb || peakDb > AudioMeterScale.MaximumDb)
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
        int zeroX = DbToX(0.0, bounds);
        using (var overrangeBackground = new SolidBrush(Color.FromArgb(65, 28, 28)))
            e.Graphics.FillRectangle(overrangeBackground, zeroX, bounds.Top, bounds.Right - zeroX, bounds.Height);
        int rmsX = DbToX(rmsDb, bounds);
        int peakX = DbToX(peakDb, bounds);
        using (var rmsBrush = new SolidBrush(clipDisplay.WindowClipped ? Color.FromArgb(220, 45, 45) : Color.FromArgb(65, 120, 180)))
            e.Graphics.FillRectangle(rmsBrush, bounds.Left, bounds.Top, Math.Max(0, rmsX - bounds.Left), bounds.Height);
        using (var peakBrush = new SolidBrush(clipDisplay.WindowClipped ? Color.FromArgb(220, 45, 45) : Color.FromArgb(45, 155, 230)))
            e.Graphics.FillRectangle(peakBrush, rmsX, bounds.Top, Math.Max(0, peakX - rmsX), bounds.Height);
        int holdX = DbToX(peakHold.PeakDb, bounds);
        using (var holdPen = new Pen(Color.White, 2F))
            e.Graphics.DrawLine(holdPen, holdX, bounds.Top, holdX, bounds.Bottom);
        using (var referencePen = new Pen(Color.Gold, 1F))
            e.Graphics.DrawLine(referencePen, zeroX, bounds.Top, zeroX, bounds.Bottom);
        using (var border = new Pen(clipDisplay.SessionClipped ? Color.Red : Color.DimGray)) e.Graphics.DrawRectangle(border, bounds);
        using (var labelBrush = new SolidBrush(Color.WhiteSmoke)) {
            foreach (int tick in new[] { -60, -48, -36, -24, -12, 0, 6, 12 }) {
                int x = DbToX(tick, bounds);
                string label = tick.ToString("+0;-0;0", CultureInfo.InvariantCulture);
                float labelWidth = e.Graphics.MeasureString(label, Font).Width;
                float labelX = Math.Max(bounds.Left, Math.Min(bounds.Right - labelWidth, x - labelWidth / 2));
                e.Graphics.DrawString(label, Font, labelBrush, labelX, bounds.Top + 2);
            }
        }
    }

    private static double ClampDb(double value)
    {
        return AudioMeterScale.Clamp(value);
    }

    private static int DbToX(double value, Rectangle bounds)
    {
        return bounds.Left + checked((int)Math.Round(AudioMeterScale.Position(value) * bounds.Width));
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
internal static class CaptureTerminalDisplay
{
    public static string Format(string reason, string gainSummary)
    {
        return "停止理由: " + reason +
            (String.IsNullOrEmpty(gainSummary) ? "" : "\n" + gainSummary);
    }
}

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
            const string summary = "GAIN測定: Peak -26.4 dBFS / 音声保存なし。適正判定は未確定です。";
            string terminal = CaptureTerminalDisplay.Format("GAIN_CHECK_COMPLETED", summary);
            Require(terminal == "停止理由: GAIN_CHECK_COMPLETED\n" + summary,
                "gain_summary_and_reason_remain_visible");
            Require(CaptureTerminalDisplay.Format("GAIN_CHECK_COMPLETED", summary) == terminal,
                "gain_summary_survives_repeated_refresh");
            Require(CaptureTerminalDisplay.Format("FINALIZE_FAILED: IOException", summary) ==
                "停止理由: FINALIZE_FAILED: IOException\n" + summary,
                "gain_summary_does_not_hide_finalize_failure");
            Require(CaptureTerminalDisplay.Format("USER_STOP", null) == "停止理由: USER_STOP" &&
                CaptureTerminalDisplay.Format("USER_STOP", "") == "停止理由: USER_STOP",
                "ordinary_recording_has_no_previous_gain_summary");
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
            Require(AudioMeterSnapshot.FormatDbfs(1.25, 3) == "+1.9" &&
                clipped.RangeState == "入力範囲外(今回)", "overrange_numeric_value_is_positive_and_explicit");
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
                AudioMeterSnapshot.FormatDbfs(quiet.SessionMaximum, 3) == "+1.9",
                "overrange_history_preserves_raw_session_maximum");
            Require(window.SnapshotAndReset().Packet.ClipSampleCount == 0,
                "window_clip_delta_not_replayed");
            foreach (double db in new[] { -60.0, -24.0, -12.0, -1.0, 0.0, 6.0, 12.0, 18.0 }) {
                var measured = Packet((float)Math.Pow(10.0, db / 20.0));
                Require(Math.Abs(20.0 * Math.Log10(measured.Peak) - db) < 0.001,
                    "known_dbfs_vector");
                Require(measured.ClipSampleCount == (db >= 0.0 ? 1 : 0),
                    "zero_dbfs_clip_is_not_warning_band");
            }
            Require(AudioMeterScale.Position(-60.0) == 0.0 && AudioMeterScale.Position(12.0) == 1.0 &&
                Math.Abs(AudioMeterScale.Position(0.0) - 5.0 / 6.0) < 1e-12 &&
                AudioMeterScale.Position(6.0) > AudioMeterScale.Position(0.0),
                "meter_has_visible_positive_headroom");
            Require(AudioMeterScale.Position(18.0) == 1.0 && AudioMeterScale.Position(-80.0) == 0.0 &&
                AudioMeterSnapshot.FormatDbfs(Math.Pow(10.0, 18.0 / 20.0), 1) == "+18.0",
                "only_drawing_saturates_above_positive_scale");
            window.ResetSession();
            window.Accumulate(Packet(8.0F));
            var aboveScale = window.SnapshotAndReset();
            Require(aboveScale.RangeState == "表示範囲(+12)超過(今回)" &&
                AudioMeterSnapshot.FormatDbfs(aboveScale.Packet.Peak, 1) == "+18.1" &&
                window.SnapshotAndReset().RangeState == "表示範囲(+12)超過(履歴)",
                "above_scale_current_and_history_remain_explicit");
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
            hold.Observe(6.0, 0);
            hold.Observe(-12.0, TimeSpan.FromMilliseconds(1499).Ticks);
            Require(hold.PeakDb == 6.0, "positive_peak_hold_is_not_clamped_to_zero");
            hold.Observe(-12.0, TimeSpan.FromMilliseconds(1500).Ticks);
            Require(hold.PeakDb == -12.0, "positive_peak_hold_expires");
            hold.Reset();
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
