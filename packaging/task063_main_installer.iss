#define AppName "BAI Video Production"
#ifndef AppVersion
  #define AppVersion "0.23.0-task063"
#endif
#ifndef PayloadRoot
  #define PayloadRoot "builds\BAI Video Production"
#endif
#ifndef PayloadTreeSha
  #define PayloadTreeSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif

[Setup]
AppId={{A6313D5D-7E87-4EC6-A6B2-C0EDBA5D7B63}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BAI
DefaultDirName={localappdata}\Programs\BAI Video Production
DefaultGroupName=BAI Video Production
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=bai-video-production-{#AppVersion}-windows-x64-setup
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
VersionInfoVersion=0.23.0.63
VersionInfoProductName={#AppName}
VersionInfoDescription=BAI Video Production unified desktop application
VersionInfoCompany=BAI
VersionInfoCopyright=Copyright (c) 2026 BAI

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.ReparseUnsupported=Installation stopped because the destination or an existing ancestor is unsafe. Product payload placement was not started.
en.BridgeProvisionFailed=The installer-relative montage learning bridge could not be provisioned or read back. Installation is not complete.
en.DataNotice=Uninstall preserves data\montage-learning-bridge by default. Delete it only after a separate reviewed backup decision.
ja.ReparseUnsupported=インストール先または既存ancestorが安全でないため停止しました。Product payloadの配置は開始していません。
ja.BridgeProvisionFailed=インストール先相対のモンタージュ学習Bridgeを作成・読戻しできませんでした。導入完了ではありません。
ja.DataNotice=アンインストール時も data\montage-learning-bridge は既定で保持します。別途バックアップ確認後に削除してください。

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut / デスクトップにショートカットを作成"; GroupDescription: "Shortcuts / ショートカット"; Flags: unchecked

[Files]
Source: "{#PayloadRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\BAI Video Production"; Filename: "{app}\BAI Video Production.exe"
Name: "{autodesktop}\BAI Video Production"; Filename: "{app}\BAI Video Production.exe"; Tasks: desktopicon

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
  if Handle = BAI_INVALID_HANDLE_VALUE then
    exit;
  try
    if not GetFileInformationByHandle(Handle, Info) then
      exit;
    if (Info.FileAttributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0 then
      exit;
    if (Info.FileAttributes and BAI_FILE_ATTRIBUTE_DIRECTORY) = 0 then
      exit;
    Identity := IntToHex(Info.VolumeSerialNumber, 8) + ':' +
      IntToHex(Info.FileIndexHigh, 8) + IntToHex(Info.FileIndexLow, 8);
    Result := True;
  finally
    CloseHandle(Handle);
  end;
end;

function BuildExistingAncestorSnapshot(const Path: String;
  var Snapshot: String): Boolean;
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
    if FileExists(Current) and not DirExists(Current) then
      exit;
    if DirExists(Current) then
    begin
      if DirectoryIsReparsePoint(Current) or
        not ReadDirectoryIdentity(Current, Identity) then
        exit;
      Snapshot := Lowercase(Current) + '|' + Identity + ';' + Snapshot;
    end;
    Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Current));
    if (Parent = '') or (CompareText(Parent, Current) = 0) then
      break;
    Current := Parent;
  end;
  Result := True;
end;

function FindDeepestExistingAncestor(const Path: String;
  var ExistingAncestor: String): Boolean;
var
  Current: String;
  Parent: String;
begin
  Result := False;
  Current := RemoveBackslashUnlessRoot(ExpandFileName(Path));
  while Current <> '' do
  begin
    if FileExists(Current) and not DirExists(Current) then
      exit;
    if DirExists(Current) then
    begin
      ExistingAncestor := Current;
      Result := True;
      exit;
    end;
    Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Current));
    if (Parent = '') or (CompareText(Parent, Current) = 0) then
      exit;
    Current := Parent;
  end;
end;

function PreparedAncestorsStillMatch(): Boolean;
var
  CurrentSnapshot: String;
begin
  Result := BuildExistingAncestorSnapshot(
    PreparedExistingAncestor, CurrentSnapshot) and
    (CurrentSnapshot = PreparedAncestorSnapshot);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  CurrentSnapshot: String;
begin
  Result := '';
  PreparedInstallRoot := RemoveBackslashUnlessRoot(
    ExpandFileName(ExpandConstant('{app}')));
  if (not FindDeepestExistingAncestor(
      PreparedInstallRoot, PreparedExistingAncestor)) or
    (not BuildExistingAncestorSnapshot(
      PreparedExistingAncestor, CurrentSnapshot)) then
    Result := CustomMessage('ReparseUnsupported');
  if Result = '' then
    PreparedAncestorSnapshot := CurrentSnapshot;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  ReceiptPath: String;
  CurrentRoot: String;
begin
  if CurStep = ssInstall then
  begin
    CurrentRoot := RemoveBackslashUnlessRoot(
      ExpandFileName(ExpandConstant('{app}')));
    if (CompareText(CurrentRoot, PreparedInstallRoot) <> 0) or
      (not PreparedAncestorsStillMatch()) then
      RaiseException(CustomMessage('ReparseUnsupported'));
  end
  else if CurStep = ssPostInstall then
  begin
    if not PreparedAncestorsStillMatch() then
      RaiseException(CustomMessage('ReparseUnsupported'));

    Params := '--bvp-installer-bridge provision-readback --install-root "' +
      ExpandConstant('{app}') + '" --installer-manifest-sha256 "sha256:{#PayloadTreeSha}"';
    if (not Exec(ExpandConstant('{app}\BAI Video Production.exe'), Params,
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode)) or
      (ResultCode <> 0) then
      RaiseException(CustomMessage('BridgeProvisionFailed'));

    ReceiptPath := ExpandConstant(
      '{app}\data\montage-learning-bridge\migration\installer-readback.json');
    if (not FileExists(ReceiptPath)) or
      (not PreparedAncestorsStillMatch()) then
      RaiseException(CustomMessage('BridgeProvisionFailed'));
    Log('TASK-063 installer-relative bridge provision/read-back: PASS');
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption +
      Chr(13) + Chr(10) + CustomMessage('DataNotice');
end;

// No bridge directories are installer-owned or recursively removed. The private
// installer helper creates them after payload placement; uninstall therefore
// preserves learning data and receipts by default.
