#ifndef AppVersion
  #define AppVersion "0.24.1"
#endif
#ifndef AppName
  #define AppName "BAI DbD Utility"
#endif
#ifndef AppIdValue
  #define AppIdValue "64DA649A-8C31-41D1-B613-17B4898C27DE"
#endif
#ifndef ExecutableName
  #define ExecutableName "BAI DbD Utility.exe"
#endif
#ifndef OutputBaseName
  #define OutputBaseName "bai-dbd-utility-0.24.1-windows-x64-setup"
#endif
#ifndef PayloadRoot
  #define PayloadRoot "payload"
#endif
#ifndef PayloadTreeSha
  #define PayloadTreeSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif

[Setup]
AppId={{{#AppIdValue}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BAI
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename={#OutputBaseName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
Uninstallable=yes
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousLanguage=yes
ChangesEnvironment=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} per-user installer
VersionInfoCompany=BAI
VersionInfoCopyright=Copyright (c) 2026 BAI

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.UnsafeDestination=Installation stopped because the destination is a drive root, a direct child of a drive root, a network path, or crosses a reparse point. No payload file was written.
ja.UnsafeDestination=インストール先がドライブルート、その直下、ネットワークパス、またはreparse pointをまたぐため停止しました。製品ファイルは書き込んでいません。

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut / デスクトップにショートカットを作成"; GroupDescription: "Shortcuts / ショートカット"; Flags: unchecked

[Files]
Source: "{#PayloadRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExecutableName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExecutableName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\BAI\{#AppName}"; ValueType: string; ValueName: "PayloadTreeSha256"; ValueData: "sha256:{#PayloadTreeSha}"; Flags: uninsdeletekey

[Code]
const
  BAI_FILE_ATTRIBUTE_REPARSE_POINT = $00000400;
  BAI_FILE_ATTRIBUTE_DIRECTORY = $00000010;
  BAI_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;
  BAI_FILE_SHARE_READ = $00000001;
  BAI_FILE_SHARE_WRITE = $00000002;
  BAI_FILE_SHARE_DELETE = $00000004;
  BAI_OPEN_EXISTING = 3;
  BAI_FILE_FLAG_OPEN_REPARSE_POINT = $00200000;
  BAI_FILE_FLAG_BACKUP_SEMANTICS = $02000000;
  BAI_INVALID_HANDLE_VALUE = $FFFFFFFF;
  BAI_HEX_DIGITS = '0123456789abcdef';

type
  TBaiFileInformation = record
    FileAttributes: LongWord;
    CreationTimeLow: LongWord;
    CreationTimeHigh: LongWord;
    LastAccessTimeLow: LongWord;
    LastAccessTimeHigh: LongWord;
    LastWriteTimeLow: LongWord;
    LastWriteTimeHigh: LongWord;
    VolumeSerialNumber: LongWord;
    FileSizeHigh: LongWord;
    FileSizeLow: LongWord;
    NumberOfLinks: LongWord;
    FileIndexHigh: LongWord;
    FileIndexLow: LongWord;
  end;

var
  PreparedInstallRoot: String;
  PreparedExistingAncestor: String;
  PreparedAncestorSnapshot: String;

function GetFileAttributesW(FileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function CreateFileW(FileName: String; DesiredAccess: LongWord;
  ShareMode: LongWord; SecurityAttributes: LongWord;
  CreationDisposition: LongWord; FlagsAndAttributes: LongWord;
  TemplateFile: LongWord): LongWord;
  external 'CreateFileW@kernel32.dll stdcall';
function GetFileInformationByHandle(Handle: LongWord;
  var FileInformation: TBaiFileInformation): Boolean;
  external 'GetFileInformationByHandle@kernel32.dll stdcall';
function CloseHandle(Handle: LongWord): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function DirectoryIsReparsePoint(const Path: String): Boolean;
var
  Attributes: LongWord;
begin
  Attributes := GetFileAttributesW(Path);
  Result := (Attributes <> BAI_INVALID_FILE_ATTRIBUTES) and
    ((Attributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0);
end;

function LongWordToFixedHex(Value: LongWord): String;
var
  Index: Integer;
begin
  Result := '';
  for Index := 1 to 8 do
  begin
    Result := Copy(BAI_HEX_DIGITS, (Value mod 16) + 1, 1) + Result;
    Value := Value div 16;
  end;
end;

function ReadDirectoryIdentity(const Path: String; var Identity: String): Boolean;
var
  Handle: LongWord;
  Info: TBaiFileInformation;
begin
  Result := False;
  Handle := CreateFileW(Path, 0,
    BAI_FILE_SHARE_READ or BAI_FILE_SHARE_WRITE or BAI_FILE_SHARE_DELETE,
    0, BAI_OPEN_EXISTING,
    BAI_FILE_FLAG_OPEN_REPARSE_POINT or BAI_FILE_FLAG_BACKUP_SEMANTICS, 0);
  if Handle = BAI_INVALID_HANDLE_VALUE then exit;
  try
    if not GetFileInformationByHandle(Handle, Info) then exit;
    if (Info.FileAttributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0 then exit;
    if (Info.FileAttributes and BAI_FILE_ATTRIBUTE_DIRECTORY) = 0 then exit;
    Identity := LongWordToFixedHex(Info.VolumeSerialNumber) + ':' +
      LongWordToFixedHex(Info.FileIndexHigh) + LongWordToFixedHex(Info.FileIndexLow);
    Result := True;
  finally
    CloseHandle(Handle);
  end;
end;

function BuildExistingAncestorSnapshot(const Path: String; var Snapshot: String): Boolean;
var
  Current: String;
  Parent: String;
  Identity: String;
begin
  Result := False;
  Snapshot := '';
  Current := RemoveBackslashUnlessRoot(ExpandFileName(Path));
  while Current <> '' do
  begin
    if FileExists(Current) and not DirExists(Current) then exit;
    if DirExists(Current) then
    begin
      if DirectoryIsReparsePoint(Current) or
        not ReadDirectoryIdentity(Current, Identity) then exit;
      Snapshot := Lowercase(Current) + '|' + Identity + ';' + Snapshot;
    end;
    Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Current));
    if (Parent = '') or (CompareText(Parent, Current) = 0) then break;
    Current := Parent;
  end;
  Result := True;
end;

function FindDeepestExistingAncestor(const Path: String; var ExistingAncestor: String): Boolean;
var
  Current: String;
  Parent: String;
begin
  Result := False;
  Current := RemoveBackslashUnlessRoot(ExpandFileName(Path));
  while Current <> '' do
  begin
    if FileExists(Current) and not DirExists(Current) then exit;
    if DirExists(Current) then
    begin
      ExistingAncestor := Current;
      Result := True;
      exit;
    end;
    Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Current));
    if (Parent = '') or (CompareText(Parent, Current) = 0) then exit;
    Current := Parent;
  end;
end;

function InstallRootIsContained(const Path: String): Boolean;
var
  Normalized: String;
  DriveRoot: String;
  Parent: String;
begin
  Result := False;
  Normalized := RemoveBackslashUnlessRoot(ExpandFileName(Path));
  if Pos('\\', Normalized) = 1 then exit;
  DriveRoot := AddBackslash(ExtractFileDrive(Normalized));
  if DriveRoot = '\' then exit;
  if CompareText(AddBackslash(Normalized), DriveRoot) = 0 then exit;
  Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Normalized));
  if CompareText(AddBackslash(Parent), DriveRoot) = 0 then exit;
  Result := True;
end;

function PreparedAncestorsStillMatch(): Boolean;
var
  CurrentSnapshot: String;
begin
  Result := BuildExistingAncestorSnapshot(PreparedExistingAncestor, CurrentSnapshot) and
    (CurrentSnapshot = PreparedAncestorSnapshot);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  CurrentSnapshot: String;
begin
  Result := '';
  PreparedInstallRoot := RemoveBackslashUnlessRoot(ExpandFileName(ExpandConstant('{app}')));
  if (not InstallRootIsContained(PreparedInstallRoot)) or
    (not FindDeepestExistingAncestor(PreparedInstallRoot, PreparedExistingAncestor)) or
    (not BuildExistingAncestorSnapshot(PreparedExistingAncestor, CurrentSnapshot)) then
    Result := CustomMessage('UnsafeDestination');
  if Result = '' then PreparedAncestorSnapshot := CurrentSnapshot;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  CurrentRoot: String;
begin
  if CurStep = ssInstall then
  begin
    CurrentRoot := RemoveBackslashUnlessRoot(ExpandFileName(ExpandConstant('{app}')));
    if (CompareText(CurrentRoot, PreparedInstallRoot) <> 0) or
      (not PreparedAncestorsStillMatch()) then
      RaiseException(CustomMessage('UnsafeDestination'));
  end
  else if CurStep = ssPostInstall then
  begin
    if not PreparedAncestorsStillMatch() then
      RaiseException(CustomMessage('UnsafeDestination'));
  end;
end;
