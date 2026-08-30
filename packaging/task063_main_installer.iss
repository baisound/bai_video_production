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
en.ReparseUnsupported=Installation stopped because the destination is a reparse point. No file was changed.
en.BridgeProvisionFailed=The installer-relative montage learning bridge could not be provisioned or read back. Installation is not complete.
en.DataNotice=Uninstall preserves data\montage-learning-bridge by default. Delete it only after a separate reviewed backup decision.
ja.ReparseUnsupported=インストール先がreparse pointのため停止しました。ファイルは変更していません。
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
  BAI_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;

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

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if DirExists(ExpandConstant('{app}')) and DirectoryIsReparsePoint(ExpandConstant('{app}')) then
    Result := CustomMessage('ReparseUnsupported');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  ReceiptPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    Params := '--bvp-installer-bridge provision --install-root "' +
      ExpandConstant('{app}') + '" --installer-manifest-sha256 "sha256:{#PayloadTreeSha}"';
    if (not Exec(ExpandConstant('{app}\BAI Video Production.exe'), Params,
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode)) or
      (ResultCode <> 0) then
      RaiseException(CustomMessage('BridgeProvisionFailed'));

    ReceiptPath := ExpandConstant(
      '{app}\data\montage-learning-bridge\migration\installer-readback.json');
    Params := '--bvp-installer-bridge discover --install-root "' +
      ExpandConstant('{app}') + '" --receipt-output "' + ReceiptPath + '"';
    if (not Exec(ExpandConstant('{app}\BAI Video Production.exe'), Params,
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode)) or
      (ResultCode <> 0) or (not FileExists(ReceiptPath)) then
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
