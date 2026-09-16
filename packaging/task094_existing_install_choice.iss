{ Shared TASK-094 existing-install decision page.
  Each including installer must provide:
    Task094ExistingInstallMarker(InstallRoot)
    Task094UninstallRegistryKey()
}

var
  Task094ExistingInstallPage: TInputOptionWizardPage;
  Task094DetectedInstallRoot: String;
  Task094DetectedUninstaller: String;
  Task094RequestedInstallRoot: String;
  Task094ExistingInstallDetected: Boolean;
  Task094ExistingInstallAction: Integer;
  Task094UninstallCompleted: Boolean;

function Task094NormalizeInstallRoot(const Value: String): String;
begin
  Result := RemoveBackslashUnlessRoot(ExpandFileName(Value));
end;

function Task094RootContainsProduct(const InstallRoot: String): Boolean;
begin
  Result := FileExists(AddBackslash(InstallRoot) + 'unins000.exe') or
    FileExists(Task094ExistingInstallMarker(InstallRoot));
end;

function Task094RefreshExistingInstall: Boolean;
var
  RegisteredRoot: String;
begin
  Task094RequestedInstallRoot := Task094NormalizeInstallRoot(WizardDirValue);
  Task094DetectedInstallRoot := '';
  Task094DetectedUninstaller := '';

  { Prefer the folder the user just selected. This also detects a partial
    install whose uninstall registry entry was already removed. }
  if Task094RootContainsProduct(Task094RequestedInstallRoot) then
    Task094DetectedInstallRoot := Task094RequestedInstallRoot
  else if RegQueryStringValue(HKCU, Task094UninstallRegistryKey(),
      'InstallLocation', RegisteredRoot) then
  begin
    RegisteredRoot := Task094NormalizeInstallRoot(RegisteredRoot);
    if Task094RootContainsProduct(RegisteredRoot) then
      Task094DetectedInstallRoot := RegisteredRoot;
  end;

  Task094ExistingInstallDetected := Task094DetectedInstallRoot <> '';
  if Task094ExistingInstallDetected then
  begin
    Task094DetectedUninstaller := AddBackslash(Task094DetectedInstallRoot) +
      'unins000.exe';
    Task094ExistingInstallPage.Values[0] := True;
    Task094ExistingInstallPage.Values[1] := False;
    Task094ExistingInstallPage.Values[2] := False;
    Task094ExistingInstallAction := 0;
    Log('TASK-094 existing installation detected: ' +
      Task094DetectedInstallRoot);
  end;
  Result := Task094ExistingInstallDetected;
end;

procedure Task094InitializeExistingInstallChoice;
begin
  Task094ExistingInstallPage := CreateInputOptionPage(wpSelectDir,
    CustomMessage('ExistingInstallTitle'),
    CustomMessage('ExistingInstallDescription'),
    CustomMessage('ExistingInstallPrompt'), True, False);
  Task094ExistingInstallPage.Add(CustomMessage('ExistingInstallUpdate'));
  Task094ExistingInstallPage.Add(CustomMessage('ExistingInstallUninstall'));
  Task094ExistingInstallPage.Add(CustomMessage('ExistingInstallCancel'));
  Task094ExistingInstallPage.Values[0] := True;
end;

function Task094ShouldSkipExistingInstallPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = Task094ExistingInstallPage.ID then
    Result := WizardSilent or (not Task094RefreshExistingInstall);
end;

function Task094ExistingInstallChoiceNext(PageID: Integer): Boolean;
begin
  Result := True;
  if PageID <> Task094ExistingInstallPage.ID then
    exit;

  if Task094ExistingInstallPage.Values[2] then
  begin
    Result := False;
    WizardForm.Close;
    exit;
  end;

  if Task094ExistingInstallPage.Values[1] then
  begin
    if not FileExists(Task094DetectedUninstaller) then
    begin
      MsgBox(CustomMessage('ExistingUninstallerMissing'), mbError, MB_OK);
      Result := False;
      exit;
    end;
    Task094ExistingInstallAction := 1;
  end
  else
  begin
    Task094ExistingInstallAction := 0;
    { Update/reinstall always targets the detected installation rather than
      silently creating a second copy under the same AppId. }
    WizardForm.DirEdit.Text := Task094DetectedInstallRoot;
  end;
end;

function Task094PrepareExistingInstall: String;
var
  ResultCode: Integer;
begin
  Result := '';
  if WizardSilent or (not Task094ExistingInstallDetected) or
    (Task094ExistingInstallAction <> 1) or Task094UninstallCompleted then
    exit;

  if (Task094NormalizeInstallRoot(Task094DetectedInstallRoot) = '') or
    (not FileExists(Task094DetectedUninstaller)) then
  begin
    Result := CustomMessage('ExistingUninstallerMissing');
    exit;
  end;

  if (not Exec(Task094DetectedUninstaller,
      '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
      Task094DetectedInstallRoot, SW_SHOW, ewWaitUntilTerminated,
      ResultCode)) or (ResultCode <> 0) then
  begin
    Result := FmtMessage(CustomMessage('ExistingUninstallFailed'),
      Task094DetectedInstallRoot);
    exit;
  end;

  Task094UninstallCompleted := True;
  Log('TASK-094 existing installation uninstall completed: ' +
    Task094DetectedInstallRoot);
end;
