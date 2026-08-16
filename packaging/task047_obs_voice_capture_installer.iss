#define AppName "BAI Voice Capture"
#define AppVersion "0.1.0-dev.8-installer.4"
#ifndef PayloadRoot
  #define PayloadRoot "payload"
#endif
#define PluginSha "14839bcad60fe47583a97729e3dc41c23b9f6c06012d5a83a38d8fc04b435b38"
#define EnSha "066718cb394b9af07319f4bb4a0f6eb7cc50e45e73ffc76662c588ccbaa8ae8d"
#define JaSha "c55315f3973893bfe9303766df7ab824751e93a84a0a607224a3b465fbf63f4e"

[Setup]
AppId={{91F1D154-4D4E-44C9-9856-313FD30B4C47}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BAI
DefaultDirName={code:DefaultAppDir}
DefaultGroupName=BAI Voice Capture
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputDir=output
OutputBaseFilename=bai-voice-capture-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
Uninstallable=yes
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousLanguage=yes
VersionInfoVersion=0.1.0.8
VersionInfoProductName={#AppName}
VersionInfoDescription=OBS 32.2.1 voice capture plugin installer
VersionInfoCompany=BAI
VersionInfoCopyright=Copyright (c) 2026 BAI

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.ObsPageTitle=Choose the OBS Studio folder
en.ObsPageDescription=Select the folder that contains bin\64bit\obs64.exe. OBS must be closed.
en.ObsRootLabel=OBS Studio folder:
en.BadObsRoot=OBS Studio 32.2.1 was not found in the selected folder.%nExpected: %1
en.BadObsVersion=This installer supports OBS Studio 32.2.1 only.%nDetected version: %1
en.ObsRunning=Close OBS Studio before continuing. The installer never closes OBS automatically.
en.ObsNetworkUnsupported=Network/UNC OBS paths are not supported. Select a local OBS Studio folder.
en.ObsReparseUnsupported=Installation stopped because the OBS Studio folder is a reparse point. No file was changed.
en.ObsNotWritable=The OBS Studio folder is not writable. Check its permissions or run the installer with the required account.
en.ObsDiskLow=The OBS drive has less than 16 MB free. Free space and try again.
en.TargetCollision=Installation stopped because an existing plugin file has different content:%n%1%nNo file was changed.
en.ReadbackFailed=Installation finished copying files, but verification failed:%n%1%nDo not start OBS. Keep the installer log for recovery.
ja.ObsPageTitle=OBS Studio の場所を選択
ja.ObsPageDescription=bin\64bit\obs64.exe があるフォルダーを選びます。OBS は終了してください。
ja.ObsRootLabel=OBS Studio フォルダー:
ja.BadObsRoot=選択した場所に OBS Studio 32.2.1 が見つかりません。%n確認先: %1
ja.BadObsVersion=このインストーラーが対応するのは OBS Studio 32.2.1 だけです。%n検出したバージョン: %1
ja.ObsRunning=続ける前に OBS Studio を終了してください。インストーラーが自動終了することはありません。
ja.ObsNetworkUnsupported=ネットワーク/UNC上のOBSには導入できません。ローカルのOBS Studioフォルダーを選んでください。
ja.ObsReparseUnsupported=OBS Studioフォルダーがreparse pointのため停止しました。ファイルは変更していません。
ja.ObsNotWritable=OBS Studioフォルダーへ書き込めません。権限を確認するか、必要なアカウントでインストーラーを実行してください。
ja.ObsDiskLow=OBSがあるドライブの空き容量が16 MB未満です。空き容量を確保して再実行してください。
ja.TargetCollision=内容の異なる既存Pluginファイルがあるため停止しました:%n%1%nファイルは変更していません。
ja.ReadbackFailed=コピー後の検証に失敗しました:%n%1%nOBSを起動せず、復旧のためインストーラーログを保管してください。

[Files]
Source: "{#PayloadRoot}\controller\bai-voice-capture-controller.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\obs-plugins\64bit\bai-voice-capture.dll"; DestDir: "{code:PluginDir}"; Flags: ignoreversion uninsneveruninstall
Source: "{#PayloadRoot}\data\obs-plugins\bai-voice-capture\locale\en-US.ini"; DestDir: "{code:LocaleDir}"; Flags: ignoreversion uninsneveruninstall
Source: "{#PayloadRoot}\data\obs-plugins\bai-voice-capture\locale\ja-JP.ini"; DestDir: "{code:LocaleDir}"; Flags: ignoreversion uninsneveruninstall
Source: "{#PayloadRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\NOTICE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\package-manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\UPSTREAM-OBS-COPYING.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BAI Voice Capture Controller"; Filename: "{app}\bai-voice-capture-controller.exe"

[UninstallDelete]
Type: files; Name: "{app}\install-state.txt"
Type: files; Name: "{app}\install-journal.jsonl"
Type: files; Name: "{app}\install-journal-v2.jsonl"
Type: files; Name: "{app}\install-journal-v2-head.txt"
Type: filesandordirs; Name: "{app}\backup"

[Code]
const
  BAI_FILE_ATTRIBUTE_REPARSE_POINT = $00000400;
  BAI_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;
  BAI_TH32CS_SNAPPROCESS = $00000002;
  BAI_MAX_PATH = 260;

type
  TBAIProcessEntry32 = record
    dwSize: LongWord;
    cntUsage: LongWord;
    th32ProcessID: LongWord;
    th32DefaultHeapID: LongWord;
    th32ModuleID: LongWord;
    cntThreads: LongWord;
    th32ParentProcessID: LongWord;
    pcPriClassBase: Integer;
    dwFlags: LongWord;
    szExeFile: array[0..BAI_MAX_PATH - 1] of Char;
  end;

function GetFileAttributesW(FileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function CreateToolhelp32Snapshot(Flags, ProcessId: LongWord): THandle;
  external 'CreateToolhelp32Snapshot@kernel32.dll stdcall';
function Process32FirstW(Snapshot: THandle; var Entry: TBAIProcessEntry32): Boolean;
  external 'Process32FirstW@kernel32.dll stdcall';
function Process32NextW(Snapshot: THandle; var Entry: TBAIProcessEntry32): Boolean;
  external 'Process32NextW@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

var
  ObsPage: TInputDirWizardPage;
  ObsRoot: String;
  JournalPath: String;
  JournalPrevHash: String;
  JournalSequence: Integer;
  T1Preexisting: Boolean;
  T2Preexisting: Boolean;
  T3Preexisting: Boolean;
  LastPreflightError: String;
  PublishStarted: Boolean;
  InstallVerified: Boolean;

function NormalizeRoot(Value: String): String;
begin
  Result := RemoveBackslashUnlessRoot(Trim(Value));
end;

function DefaultAppDir(Param: String): String;
begin
  Result := AddBackslash(GetEnv('LOCALAPPDATA')) + 'BAI Voice Capture';
end;

function PluginDir(Param: String): String;
begin
  Result := AddBackslash(ObsRoot) + 'obs-plugins\64bit';
end;

function LocaleDir(Param: String): String;
begin
  Result := AddBackslash(ObsRoot) + 'data\obs-plugins\bai-voice-capture\locale';
end;

function Target1: String;
begin
  Result := AddBackslash(PluginDir('')) + 'bai-voice-capture.dll';
end;

function Target2: String;
begin
  Result := AddBackslash(LocaleDir('')) + 'en-US.ini';
end;

function Target3: String;
begin
  Result := AddBackslash(LocaleDir('')) + 'ja-JP.ini';
end;

function ASCIIEqualIgnoreCase(Value, LowercaseValue: Char): Boolean;
begin
  Result := (Value = LowercaseValue) or (Ord(Value) = Ord(LowercaseValue) - 32);
end;

function ProcessEntryIsObs(const Entry: TBAIProcessEntry32): Boolean;
begin
  Result := ASCIIEqualIgnoreCase(Entry.szExeFile[0], 'o') and
    ASCIIEqualIgnoreCase(Entry.szExeFile[1], 'b') and
    ASCIIEqualIgnoreCase(Entry.szExeFile[2], 's') and
    (Entry.szExeFile[3] = '6') and
    (Entry.szExeFile[4] = '4') and
    (Entry.szExeFile[5] = '.') and
    ASCIIEqualIgnoreCase(Entry.szExeFile[6], 'e') and
    ASCIIEqualIgnoreCase(Entry.szExeFile[7], 'x') and
    ASCIIEqualIgnoreCase(Entry.szExeFile[8], 'e') and
    (Entry.szExeFile[9] = #0);
end;

function IsObsRunning: Boolean;
var
  Snapshot: THandle;
  Entry: TBAIProcessEntry32;
begin
  Result := True;
  Snapshot := CreateToolhelp32Snapshot(BAI_TH32CS_SNAPPROCESS, 0);
  if Snapshot = THandle(-1) then
  begin
    Log('OBS process probe failed to create a snapshot; blocking fail-closed.');
    exit;
  end;
  try
    Entry.dwSize := SizeOf(Entry);
    if not Process32FirstW(Snapshot, Entry) then
    begin
      Log('OBS process probe failed to read the first entry; blocking fail-closed.');
      exit;
    end;
    repeat
      if ProcessEntryIsObs(Entry) then
      begin
        Log(Format('OBS process probe: running=1 pid=%d', [Entry.th32ProcessID]));
        exit;
      end;
    until not Process32NextW(Snapshot, Entry);
    Result := False;
    Log('OBS process probe: running=0');
  finally
    CloseHandle(Snapshot);
  end;
end;

function ExistingFileIsAllowed(const Path, ExpectedSha: String; var WasPresent: Boolean): Boolean;
begin
  WasPresent := FileExists(Path);
  if not WasPresent then
  begin
    Result := True;
    exit;
  end;
  Result := CompareText(GetSHA256OfFile(Path), ExpectedSha) = 0;
end;

function DirectoryIsReparsePoint(const Path: String): Boolean;
var
  Attributes: LongWord;
begin
  Attributes := GetFileAttributesW(Path);
  Result := (Attributes <> BAI_INVALID_FILE_ATTRIBUTES) and
    ((Attributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0);
end;

function DirectoryIsWritable(const Path: String): Boolean;
var
  ProbePath: String;
begin
  ProbePath := AddBackslash(Path) + '.bai-voice-capture-write-probe.tmp';
  DeleteFile(ProbePath);
  Result := SaveStringToFile(ProbePath, 'BAI_WRITE_PROBE', False);
  if Result then Result := DeleteFile(ProbePath);
end;

function ValidateObsAndTargets(ShowErrors: Boolean): Boolean;
var
  ObsExe, VersionText, BadTarget: String;
  FreeBytes, TotalBytes: Int64;
begin
  Result := False;
  LastPreflightError := '';
  ObsRoot := NormalizeRoot(ObsRoot);
  ObsExe := AddBackslash(ObsRoot) + 'bin\64bit\obs64.exe';
  Log('Validating OBS root: ' + ObsRoot);
  if Pos('\\', ObsRoot) = 1 then
  begin
    LastPreflightError := CustomMessage('ObsNetworkUnsupported');
    if ShowErrors then MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if not FileExists(ObsExe) then
  begin
    LastPreflightError := FmtMessage(CustomMessage('BadObsRoot'), ObsExe);
    if ShowErrors then
      MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if not GetVersionNumbersString(ObsExe, VersionText) then
    VersionText := '';
  if (VersionText <> '32.2.1') and (VersionText <> '32.2.1.0') then
  begin
    LastPreflightError := FmtMessage(CustomMessage('BadObsVersion'), VersionText);
    if ShowErrors then
      MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if IsObsRunning then
  begin
    LastPreflightError := CustomMessage('ObsRunning');
    if ShowErrors then
      MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if DirectoryIsReparsePoint(ObsRoot) then
  begin
    LastPreflightError := CustomMessage('ObsReparseUnsupported');
    if ShowErrors then MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if not DirectoryIsWritable(ObsRoot) then
  begin
    LastPreflightError := CustomMessage('ObsNotWritable');
    if ShowErrors then MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  if (not GetSpaceOnDisk64(ObsRoot, FreeBytes, TotalBytes)) or (FreeBytes < 16777216) then
  begin
    LastPreflightError := CustomMessage('ObsDiskLow');
    if ShowErrors then MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  BadTarget := '';
  if not ExistingFileIsAllowed(Target1, '{#PluginSha}', T1Preexisting) then BadTarget := Target1;
  if (BadTarget = '') and (not ExistingFileIsAllowed(Target2, '{#EnSha}', T2Preexisting)) then BadTarget := Target2;
  if (BadTarget = '') and (not ExistingFileIsAllowed(Target3, '{#JaSha}', T3Preexisting)) then BadTarget := Target3;
  if BadTarget <> '' then
  begin
    LastPreflightError := FmtMessage(CustomMessage('TargetCollision'), BadTarget);
    if ShowErrors then
      MsgBox(LastPreflightError, mbError, MB_OK);
    exit;
  end;
  Result := True;
  Log('OBS and exact3 target preflight: PASS');
end;

procedure AppendJournal(const Phase, Action, ResultText, Detail: String);
var
  Body, EntryHash, EscapedBody, Line, HeadText: String;
begin
  JournalSequence := JournalSequence + 1;
  Body := Format('schema=1;sequence=%d;phase=%s;action=%s;result=%s;detail=%s;prev_sha256=%s', [JournalSequence, Phase, Action, ResultText, Detail, JournalPrevHash]);
  EntryHash := GetSHA256OfString(Body);
  EscapedBody := Body;
  StringChangeEx(EscapedBody, '\', '\\', True);
  StringChangeEx(EscapedBody, '"', '\"', True);
  StringChangeEx(EscapedBody, #13, '\r', True);
  StringChangeEx(EscapedBody, #10, '\n', True);
  Line := Format('{"body":"%s","entry_sha256":"%s"}', [EscapedBody, EntryHash]) + #13#10;
  SaveStringToFile(JournalPath, Line, True);
  JournalPrevHash := EntryHash;
  HeadText := Format('Sequence=%d'#13#10'PrevHash=%s'#13#10, [JournalSequence, JournalPrevHash]);
  SaveStringToFile(ExpandConstant('{app}\install-journal-v2-head.txt'), HeadText, False);
end;

function ReadStateValue(const Text, Name: String): String; forward;

procedure SaveInstallState;
var
  ExistingAnsi: AnsiString;
  ExistingText, StatePath, ExistingObsRoot: String;
  ExistingInstall: Boolean;
  StateText: String;
begin
  StatePath := ExpandConstant('{app}\install-state.txt');
  ExistingInstall := False;
  if LoadStringFromFile(StatePath, ExistingAnsi) then
  begin
    ExistingText := String(ExistingAnsi);
    ExistingObsRoot := NormalizeRoot(ReadStateValue(ExistingText, 'ObsRoot'));
    ExistingInstall := CompareText(ExistingObsRoot, ObsRoot) = 0;
    if ExistingInstall then
    begin
      T1Preexisting := ReadStateValue(ExistingText, 'T1Preexisting') = '1';
      T2Preexisting := ReadStateValue(ExistingText, 'T2Preexisting') = '1';
      T3Preexisting := ReadStateValue(ExistingText, 'T3Preexisting') = '1';
      Log('Repair/update detected; preserving original exact3 ownership state.');
    end;
  end;
  ForceDirectories(ExpandConstant('{app}\backup'));
  if (not ExistingInstall) and T1Preexisting then CopyFile(Target1, ExpandConstant('{app}\backup\t1.bin'), False);
  if (not ExistingInstall) and T2Preexisting then CopyFile(Target2, ExpandConstant('{app}\backup\t2.bin'), False);
  if (not ExistingInstall) and T3Preexisting then CopyFile(Target3, ExpandConstant('{app}\backup\t3.bin'), False);
  StateText := Format('ObsRoot=%s'#13#10'T1Preexisting=%d'#13#10'T2Preexisting=%d'#13#10'T3Preexisting=%d'#13#10, [ObsRoot, Ord(T1Preexisting), Ord(T2Preexisting), Ord(T3Preexisting)]);
  SaveStringToFile(StatePath, StateText, False);
end;

function ReadStateValue(const Text, Name: String): String;
var
  StartPos, EndPos: Integer;
begin
  Result := '';
  StartPos := Pos(Name + '=', Text);
  if StartPos = 0 then exit;
  StartPos := StartPos + Length(Name) + 1;
  EndPos := Pos(#13#10, Copy(Text, StartPos, MaxInt));
  if EndPos = 0 then
    Result := Copy(Text, StartPos, MaxInt)
  else
    Result := Copy(Text, StartPos, EndPos - 1);
end;

procedure InitializeJournal;
var
  HeadAnsi: AnsiString;
  HeadText, SequenceText: String;
begin
  JournalPath := ExpandConstant('{app}\install-journal-v2.jsonl');
  JournalPrevHash := '';
  JournalSequence := 0;
  if LoadStringFromFile(ExpandConstant('{app}\install-journal-v2-head.txt'), HeadAnsi) then
  begin
    HeadText := String(HeadAnsi);
    SequenceText := ReadStateValue(HeadText, 'Sequence');
    if SequenceText <> '' then JournalSequence := StrToInt(SequenceText);
    JournalPrevHash := ReadStateValue(HeadText, 'PrevHash');
    Log(Format('Continuing journal: sequence=%d prev=%s', [JournalSequence, JournalPrevHash]));
  end;
end;

procedure RestoreOrRemove(const TargetPath, BackupPath, ExpectedSha: String; WasPresent: Boolean);
begin
  if not FileExists(TargetPath) then exit;
  if CompareText(GetSHA256OfFile(TargetPath), ExpectedSha) <> 0 then exit;
  if WasPresent and FileExists(BackupPath) then
    CopyFile(BackupPath, TargetPath, False)
  else
    DeleteFile(TargetPath);
end;

procedure InitializeWizard;
var
  InitialRoot: String;
begin
  ObsPage := CreateInputDirPage(wpSelectDir, CustomMessage('ObsPageTitle'),
    CustomMessage('ObsPageDescription'), CustomMessage('ObsRootLabel'), False, '');
  ObsPage.Add('');
  InitialRoot := ExpandConstant('{param:OBSROOT|}');
  if InitialRoot = '' then InitialRoot := ExpandConstant('{autopf}\obs-studio');
  ObsPage.Values[0] := InitialRoot;
  ObsRoot := NormalizeRoot(InitialRoot);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ObsPage.ID then
  begin
    ObsRoot := NormalizeRoot(ObsPage.Values[0]);
    Result := ValidateObsAndTargets(not WizardSilent);
    if not Result then Log('NextButton preflight blocked: ' + LastPreflightError);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  ObsRoot := NormalizeRoot(ExpandConstant('{param:OBSROOT|' + ObsPage.Values[0] + '}'));
  if not ValidateObsAndTargets(False) then
    Result := LastPreflightError
  else
    Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  FailurePath: String;
begin
  if CurStep = ssInstall then
  begin
    PublishStarted := True;
    InstallVerified := False;
    InitializeJournal;
    ForceDirectories(ExpandConstant('{app}'));
    AppendJournal('PREPARE', 'PREFLIGHT', 'PASS', ObsRoot);
    SaveInstallState;
    AppendJournal('PREPARE', 'BACKUP', 'PASS', 'exact3');
  end;
  if CurStep = ssPostInstall then
  begin
    FailurePath := '';
    if CompareText(GetSHA256OfFile(Target1), '{#PluginSha}') <> 0 then FailurePath := Target1;
    if (FailurePath = '') and (CompareText(GetSHA256OfFile(Target2), '{#EnSha}') <> 0) then FailurePath := Target2;
    if (FailurePath = '') and (CompareText(GetSHA256OfFile(Target3), '{#JaSha}') <> 0) then FailurePath := Target3;
    if FailurePath = '' then
    begin
      InstallVerified := True;
      AppendJournal('VERIFY', 'READ_BACK', 'PASS', 'exact3')
    end
    else
    begin
      AppendJournal('VERIFY', 'READ_BACK', 'UNKNOWN', FailurePath);
      MsgBox(FmtMessage(CustomMessage('ReadbackFailed'), FailurePath), mbError, MB_OK);
    end;
  end;
end;

procedure DeinitializeSetup;
begin
  if PublishStarted and (not InstallVerified) then
  begin
    Log('FAILED_PARTIAL_PUBLISH or UNKNOWN: automatic rollback is disabled; reconcile exact3 and journal before retry.');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  StateAnsi: AnsiString;
  StateText: String;
  Was1, Was2, Was3: Boolean;
begin
  if CurUninstallStep = usUninstall then
  begin
    if not LoadStringFromFile(ExpandConstant('{app}\install-state.txt'), StateAnsi) then exit;
    StateText := String(StateAnsi);
    ObsRoot := NormalizeRoot(ReadStateValue(StateText, 'ObsRoot'));
    Was1 := ReadStateValue(StateText, 'T1Preexisting') = '1';
    Was2 := ReadStateValue(StateText, 'T2Preexisting') = '1';
    Was3 := ReadStateValue(StateText, 'T3Preexisting') = '1';
    RestoreOrRemove(Target1, ExpandConstant('{app}\backup\t1.bin'), '{#PluginSha}', Was1);
    RestoreOrRemove(Target2, ExpandConstant('{app}\backup\t2.bin'), '{#EnSha}', Was2);
    RestoreOrRemove(Target3, ExpandConstant('{app}\backup\t3.bin'), '{#JaSha}', Was3);
  end;
end;
