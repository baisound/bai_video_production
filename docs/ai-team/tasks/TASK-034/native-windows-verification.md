# TASK-034 Native Windows Verification / 動作確認

## Before starting

- Extract the `0.12.0` ZIP into a new folder.
- Use a disposable test key when possible. Never include the key in screenshots, terminal output, chat, Issue, log or Evidence ZIP.
- This check does not contact the Provider and therefore cannot validate the key.

From the Repository root run only:

```powershell
python -m pip install -e .
python -c "import ai_video_production; print(ai_video_production.__version__)"
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-ai-connection-settings.ps1
```

The second command must print `0.12.0`. In the opened screen:

1. Open **APIキーの安全な保管 / Secure credentials**.
2. Choose a Route that says **未登録 / Not registered**, enter a disposable key, and press **保管 / Save**.
3. Confirm **登録済み / Registered** and the message saying no Provider call occurred.
4. Close and rerun the launcher. Confirm it remains **登録済み / Registered**.
5. Open Windows **Credential Manager → Windows Credentials** and confirm a generic target beginning `BAI.VideoProduction/` exists. Do not expose its secret.
6. Press **削除 / Delete**, reload, and confirm **未登録 / Not registered**.

## Output

No new Evidence directory is generated automatically because screenshots must be reviewed for secret leakage before sharing. Return only secret-free screenshots of the status and opaque target plus the terminal test results below:

```powershell
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

If registration fails, return the visible normalized error only. Do not paste the key and do not reinstall a Provider SDK.
