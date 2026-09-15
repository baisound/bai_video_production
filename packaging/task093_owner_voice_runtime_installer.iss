#define AppName "BAI Owner Voice Runtime"
#ifndef AppVersion
  #define AppVersion "0.24.2"
#endif
#ifndef PayloadRoot
  #define PayloadRoot "payload"
#endif

[Setup]
AppId={{9B42FB3B-AD03-4C77-8C9D-42F6C680B253}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BAI
DefaultDirName={localappdata}\Programs\BAI Owner Voice Runtime
DefaultGroupName=BAI Owner Voice Runtime
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=bai-owner-voice-runtime-{#AppVersion}-windows-x64-setup
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
VersionInfoVersion=0.24.2.0
VersionInfoProductName={#AppName}
VersionInfoDescription=Installer-managed Qwen3-TTS Owner Voice runtime and SRT WAV maker
VersionInfoCompany=BAI
VersionInfoCopyright=Copyright (c) 2026 BAI

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.DataRootTitle=Owner Voice data location
en.DataRootDescription=Choose a local folder with at least 12 GB free. Recordings and generated WAV files are preserved when the app is uninstalled.
en.DataRootPrompt=Owner Voice data folder:
en.DataRootUnsafe=Choose a local folder below a normal parent directory. A drive root, its direct child, network path, or reparse point is not allowed.
en.DiskLow=The selected drive has less than 12 GB free.
en.RuntimeFailed=Owner Voice runtime setup or verification failed. Review the setup log and run Repair; do not treat this installation as complete.
en.RuntimeStatus=Installing and verifying the private Python, CUDA PyTorch, Qwen model, and ffmpeg runtime. This can take a long time on the first install.
en.DataNotice=Uninstall preserves the selected data folder, model, receipts, recordings, datasets, and generated WAV files.
ja.DataRootTitle=本人声データの保存先
ja.DataRootDescription=12 GB以上の空きがあるローカルフォルダーを選択してください。アンインストールしても録音・生成WAVは残します。
ja.DataRootPrompt=本人声データフォルダー:
ja.DataRootUnsafe=通常フォルダーの配下を選択してください。ドライブルート、ドライブ直下、ネットワークパス、reparse pointは使用できません。
ja.DiskLow=選択したドライブの空き容量が12 GB未満です。
ja.RuntimeFailed=本人声runtimeの構築または検証に失敗しました。セットアップログを確認して修復を実行し、導入完了として扱わないでください。
ja.RuntimeStatus=専用Python、CUDA PyTorch、Qwen Model、ffmpegを構築・検証しています。初回は長い時間がかかります。
ja.DataNotice=アンインストールしても、選択したデータフォルダー、Model、receipt、録音、Dataset、生成WAVは削除しません。

[Files]
Source: "{#PayloadRoot}\bootstrap\*"; DestDir: "{app}\bootstrap"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadRoot}\tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadRoot}\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadRoot}\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\runtime-manifest.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\本人声Master WAV 利用ガイド"; Filename: "{app}\docs\SRT-OWNER-VOICE-WAV.md"

[Code]
const
  BAI_FILE_ATTRIBUTE_REPARSE_POINT = $00000400;
  BAI_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;
  BAI_MINIMUM_FREE_BYTES = 12884901888;

var
  DataRootPage: TInputDirWizardPage;
  RuntimeSetupFailed: Boolean;

function GetFileAttributesW(FileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function DirectoryIsReparsePoint(const Path: String): Boolean;
var
  Attributes: LongWord;
begin
  Attributes := GetFileAttributesW(Path);
  Result := (Attributes <> BAI_INVALID_FILE_ATTRIBUTES) and
    ((Attributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0);
end;

function IsUnsafeDataRoot(const Value: String): Boolean;
var
  Path: String;
  Root: String;
  Parent: String;
begin
  Path := RemoveBackslashUnlessRoot(ExpandFileName(Value));
  Root := AddBackslash(ExtractFileDrive(Path));
  Parent := RemoveBackslashUnlessRoot(ExtractFileDir(Path));
  Result := (Path = '') or (Copy(Path, 1, 2) = '\\') or
    (CompareText(Path, RemoveBackslashUnlessRoot(Root)) = 0) or
    (CompareText(Parent, RemoveBackslashUnlessRoot(Root)) = 0) or
    (DirExists(Path) and DirectoryIsReparsePoint(Path));
end;

function SelectedDataRoot(Param: String): String;
begin
  Result := RemoveBackslashUnlessRoot(ExpandFileName(DataRootPage.Values[0]));
end;

procedure InitializeWizard;
var
  CommandLineDataRoot: String;
begin
  DataRootPage := CreateInputDirPage(wpSelectDir,
    CustomMessage('DataRootTitle'), CustomMessage('DataRootDescription'),
    CustomMessage('DataRootPrompt'), False, '');
  DataRootPage.Add('');
  CommandLineDataRoot := ExpandConstant('{param:DataRoot|}');
  if CommandLineDataRoot <> '' then
    DataRootPage.Values[0] := CommandLineDataRoot
  else
    DataRootPage.Values[0] := ExpandConstant(
      '{localappdata}\BAI Video Production\Owner Voice Data');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeBytes: Int64;
  TotalBytes: Int64;
  Path: String;
begin
  Result := True;
  if CurPageID <> DataRootPage.ID then
    exit;
  Path := SelectedDataRoot('');
  if IsUnsafeDataRoot(Path) then
  begin
    MsgBox(CustomMessage('DataRootUnsafe'), mbError, MB_OK);
    Result := False;
    exit;
  end;
  if (not GetSpaceOnDisk64(ExtractFileDrive(Path), FreeBytes, TotalBytes)) or
    (FreeBytes < BAI_MINIMUM_FREE_BYTES) then
  begin
    MsgBox(CustomMessage('DiskLow'), mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  WizardForm.StatusLabel.Caption := CustomMessage('RuntimeStatus');
  Params := '-NoProfile -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{app}\tools\install-owner-voice-runtime.ps1') +
    '" -DataRoot "' + SelectedDataRoot('') + '" -InstallRoot "' +
    ExpandConstant('{app}') + '" -ManifestPath "' +
    ExpandConstant('{app}\runtime-manifest.json') + '"';
  { Inno Setup is a 32-bit process. Use sysnative so filesystem redirection does
    not select 32-bit PowerShell, whose module path may omit Get-FileHash. }
  if (not Exec(ExpandConstant('{sysnative}\WindowsPowerShell\v1.0\powershell.exe'),
      Params, ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode)) or
    (ResultCode <> 0) then
  begin
    RuntimeSetupFailed := True;
    RaiseException(CustomMessage('RuntimeFailed'));
  end;
end;

function GetCustomSetupExitCode: Integer;
begin
  if RuntimeSetupFailed then
    Result := 1
  else
    Result := 0;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption +
      Chr(13) + Chr(10) + CustomMessage('DataNotice');
end;

// The data root and runtime-config live outside {app}. Inno therefore removes
// only installer-owned application/bootstrap files and preserves Owner data.
