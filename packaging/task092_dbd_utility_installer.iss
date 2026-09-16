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
DisableDirPage=no
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
en.UnsafeDestination=Installation stopped because the destination is a drive root, a network path, or crosses a reparse point. A product-specific folder directly below a local drive is supported. No payload file was written.
en.ExistingInstallTitle=Existing installation found
en.ExistingInstallDescription=Choose how Setup should handle the existing installation.
en.ExistingInstallPrompt=Update/reinstall preserves the current location. Uninstall runs the existing uninstaller first. To make no changes, choose Cancel.
en.ExistingInstallUpdate=Update or reinstall in the existing location
en.ExistingInstallUninstall=Uninstall the existing version, then continue
en.ExistingInstallCancel=Cancel Setup without making changes
en.ExistingUninstallerMissing=The existing uninstaller is missing. Choose update/reinstall or cancel, then repair the installation first.
en.ExistingUninstallFailed=The existing installation could not be uninstalled from:%n%1%nSetup has stopped without installing the replacement.
ja.UnsafeDestination=インストール先がドライブルート、ネットワークパス、またはreparse pointをまたぐため停止しました。ローカルドライブ直下の製品専用フォルダーは使用できます。製品ファイルは書き込んでいません。
ja.ExistingInstallTitle=既存のインストールが見つかりました
ja.ExistingInstallDescription=既存版をどのように扱うか選択してください。
ja.ExistingInstallPrompt=更新・再インストールは現在の場所を使用します。アンインストールを選ぶと既存のアンインストーラーを先に実行します。変更しない場合はキャンセルを選んでください。
ja.ExistingInstallUpdate=既存の場所へ更新または再インストールする
ja.ExistingInstallUninstall=既存版をアンインストールしてから続行する
ja.ExistingInstallCancel=変更せずセットアップをキャンセルする
ja.ExistingUninstallerMissing=既存のアンインストーラーが見つかりません。更新・再インストールまたはキャンセルを選び、先にインストールを修復してください。
ja.ExistingUninstallFailed=次の場所の既存版をアンインストールできませんでした:%n%1%n新しい版はインストールせずに停止しました。

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

function Task094ExistingInstallMarker(const InstallRoot: String): String;
begin
  Result := AddBackslash(InstallRoot) + '{#ExecutableName}';
end;

function Task094UninstallRegistryKey: String;
begin
  Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' +
    '{#AppIdValue}' + '}_is1';
end;

#include "task094_existing_install_choice.iss"

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
begin
  Result := False;
  Normalized := RemoveBackslashUnlessRoot(ExpandFileName(Path));
  if Pos('\\', Normalized) = 1 then exit;
  DriveRoot := AddBackslash(ExtractFileDrive(Normalized));
  if DriveRoot = '\' then exit;
  if CompareText(AddBackslash(Normalized), DriveRoot) = 0 then exit;
  Result := True;
end;

function PreparedAncestorsStillMatch(): Boolean;
var
  CurrentSnapshot: String;
begin
  Result := BuildExistingAncestorSnapshot(PreparedExistingAncestor, CurrentSnapshot) and
    (CurrentSnapshot = PreparedAncestorSnapshot);
end;

procedure InitializeWizard;
begin
  Task094InitializeExistingInstallChoice;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := Task094ShouldSkipExistingInstallPage(PageID);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := Task094ExistingInstallChoiceNext(CurPageID);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  CurrentSnapshot: String;
begin
  Result := Task094PrepareExistingInstall;
  if Result <> '' then
    exit;
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
