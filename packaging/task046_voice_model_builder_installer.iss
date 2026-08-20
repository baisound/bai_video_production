#define AppName "BAI Voice Model Builder"
#ifndef AppVersion
  #define AppVersion "0.1.0-dev.1-installer.2"
#endif
#ifndef PayloadRoot
  #define PayloadRoot "payload"
#endif
#ifndef ExecutableSha
  #define ExecutableSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif
#ifndef GuideSha
  #define GuideSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif
#ifndef LicenseSha
  #define LicenseSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif
#ifndef ManifestSha
  #define ManifestSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif
#ifndef NoticeSha
  #define NoticeSha "0000000000000000000000000000000000000000000000000000000000000000"
#endif

[Setup]
AppId={{4DA96B8F-C27E-4AD8-B7C5-5F8EF105AEEA}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BAI
DefaultDirName={localappdata}\Programs\BAI Voice Model Builder
DefaultGroupName=BAI Voice Model Builder
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=bai-voice-model-builder-{#AppVersion}-windows-x64-setup
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
VersionInfoVersion=0.1.0.1
VersionInfoProductName={#AppName}
VersionInfoDescription=Beginner-facing local voice model workflow guide
VersionInfoCompany=BAI
VersionInfoCopyright=Copyright (c) 2026 BAI

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.DiskLow=The destination has less than 64 MB free. Free space and try again.
en.ReparseUnsupported=Installation stopped because the destination is a reparse point. No file was changed.
en.TargetCollision=Installation stopped because an existing application file has different content:%n%1%nUninstall or reconcile that file before retrying.
en.ReadbackFailed=Installed-file verification failed:%n%1%nDo not treat this installation as complete.
en.DataNotice=Uninstalling the application does not delete your recordings, datasets, checkpoints, models, or generated audio.
ja.DiskLow=インストール先の空き容量が64 MB未満です。空き容量を確保して再実行してください。
ja.ReparseUnsupported=インストール先がreparse pointのため停止しました。ファイルは変更していません。
ja.TargetCollision=内容の異なる既存アプリファイルがあるため停止しました:%n%1%n再試行前にアンインストールまたは照合してください。
ja.ReadbackFailed=インストール後のファイル検証に失敗しました:%n%1%n導入完了として扱わないでください。
ja.DataNotice=アンインストールしても、録音・Dataset・checkpoint・model・生成音声は削除しません。

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut / デスクトップにショートカットを作成"; GroupDescription: "Shortcuts / ショートカット"; Flags: unchecked

[Files]
Source: "{#PayloadRoot}\application\bai-voice-model-builder.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\docs\VOICE-MODEL-BUILDER.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#PayloadRoot}\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\package-manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadRoot}\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BAI Voice Model Builder"; Filename: "{app}\bai-voice-model-builder.exe"
Name: "{group}\Voice Model Builder Guide"; Filename: "{app}\docs\VOICE-MODEL-BUILDER.md"
Name: "{group}\Third-Party Notices"; Filename: "{app}\THIRD-PARTY-NOTICES.txt"
Name: "{autodesktop}\BAI Voice Model Builder"; Filename: "{app}\bai-voice-model-builder.exe"; Tasks: desktopicon

[Code]
const
  BAI_FILE_ATTRIBUTE_REPARSE_POINT = $00000400;
  BAI_INVALID_FILE_ATTRIBUTES = $FFFFFFFF;

function GetFileAttributesW(FileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function TargetExecutable: String;
begin
  Result := ExpandConstant('{app}\bai-voice-model-builder.exe');
end;

function TargetGuide: String;
begin
  Result := ExpandConstant('{app}\docs\VOICE-MODEL-BUILDER.md');
end;

function TargetLicense: String;
begin
  Result := ExpandConstant('{app}\LICENSE.md');
end;

function TargetManifest: String;
begin
  Result := ExpandConstant('{app}\package-manifest.json');
end;

function TargetNotice: String;
begin
  Result := ExpandConstant('{app}\THIRD-PARTY-NOTICES.txt');
end;

function DirectoryIsReparsePoint(const Path: String): Boolean;
var
  Attributes: LongWord;
begin
  Attributes := GetFileAttributesW(Path);
  Result := (Attributes <> BAI_INVALID_FILE_ATTRIBUTES) and
    ((Attributes and BAI_FILE_ATTRIBUTE_REPARSE_POINT) <> 0);
end;

function ExistingFileIsAllowed(const Path, ExpectedSha: String): Boolean;
begin
  Result := (not FileExists(Path)) or
    (CompareText(GetSHA256OfFile(Path), ExpectedSha) = 0);
end;

function ValidateDestination: String;
var
  FreeBytes, TotalBytes: Int64;
begin
  Result := '';
  if DirExists(ExpandConstant('{app}')) and DirectoryIsReparsePoint(ExpandConstant('{app}')) then
  begin
    Result := CustomMessage('ReparseUnsupported');
    exit;
  end;
  if (not GetSpaceOnDisk64(ExpandConstant('{localappdata}'), FreeBytes, TotalBytes)) or
    (FreeBytes < 67108864) then
  begin
    Result := CustomMessage('DiskLow');
    exit;
  end;
  if not ExistingFileIsAllowed(TargetExecutable, '{#ExecutableSha}') then
    Result := FmtMessage(CustomMessage('TargetCollision'), TargetExecutable)
  else if not ExistingFileIsAllowed(TargetGuide, '{#GuideSha}') then
    Result := FmtMessage(CustomMessage('TargetCollision'), TargetGuide)
  else if not ExistingFileIsAllowed(TargetLicense, '{#LicenseSha}') then
    Result := FmtMessage(CustomMessage('TargetCollision'), TargetLicense)
  else if not ExistingFileIsAllowed(TargetManifest, '{#ManifestSha}') then
    Result := FmtMessage(CustomMessage('TargetCollision'), TargetManifest)
  else if not ExistingFileIsAllowed(TargetNotice, '{#NoticeSha}') then
    Result := FmtMessage(CustomMessage('TargetCollision'), TargetNotice);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := ValidateDestination;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  FailurePath: String;
begin
  if CurStep = ssPostInstall then
  begin
    FailurePath := '';
    if CompareText(GetSHA256OfFile(TargetExecutable), '{#ExecutableSha}') <> 0 then
      FailurePath := TargetExecutable
    else if CompareText(GetSHA256OfFile(TargetGuide), '{#GuideSha}') <> 0 then
      FailurePath := TargetGuide
    else if CompareText(GetSHA256OfFile(TargetLicense), '{#LicenseSha}') <> 0 then
      FailurePath := TargetLicense
    else if CompareText(GetSHA256OfFile(TargetManifest), '{#ManifestSha}') <> 0 then
      FailurePath := TargetManifest
    else if CompareText(GetSHA256OfFile(TargetNotice), '{#NoticeSha}') <> 0 then
      FailurePath := TargetNotice;
    if FailurePath <> '' then
      MsgBox(FmtMessage(CustomMessage('ReadbackFailed'), FailurePath), mbError, MB_OK)
    else
      Log('TASK-046 exact4 installed-file read-back: PASS');
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10 + CustomMessage('DataNotice');
end;

// Deliberately no [Run] section: installation never launches the app, downloads a
// model, starts training, accesses audio, records, or publishes an artifact.
