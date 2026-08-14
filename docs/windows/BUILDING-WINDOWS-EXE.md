# WindowsクライアントをEXEへビルドする

この手順は、既存のTASK-036 Windows Unified Desktop Editing Shellをローカルでビルドします。新しいアプリや別のPyInstaller設定は作らず、正本の `packaging/task036_shell.spec` を使用します。

## 前提

- Windows 10またはWindows 11
- Python 3.11〜3.13（検証基準はPython 3.12）
- Microsoft Edge WebView2 Runtime
- リポジトリを通常の書き込み可能な場所へclone済み

DaVinci Resolve、Cubase、ProviderのAPIキーは、EXEを作るだけなら不要です。

## 初回セットアップ

PowerShellをリポジトリのルートで開き、仮想環境とビルド用依存を明示的に準備します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[windows-build]"
```

最後のコマンドはPythonパッケージを取得するためネットワークを使う場合があります。`build-windows-exe.bat` 自身がパッケージを勝手にインストールすることはありません。

## ビルド

```powershell
.\build-windows-exe.bat
```

別のPythonを使う場合だけ、先に環境変数を指定します。

```powershell
$env:BVP_BUILD_PYTHON = "C:\Python312\python.exe"
.\build-windows-exe.bat
```

何も指定しない場合は `.venv\Scripts\python.exe`、それもなければPATH上の `python` を使用します。

## 出力

成功すると、次のone-dir形式で作成されます。

```text
builds\
  BAI Video Production\
    BAI Video Production.exe
    _internal\
```

`BAI Video Production` フォルダー全体が1つのアプリです。EXEだけを別の場所へ移動しないでください。`builds/` 内はローカル生成物で、Gitには登録されません。

## 簡単な確認

```powershell
Test-Path ".\builds\BAI Video Production\BAI Video Production.exe"
.\build-windows-exe.bat --help
```

実際にEXEを起動するとローカルのWindows UIが開きます。ユーザープロジェクトへ接続する操作やResolve/Cubase連携は、それぞれのHuman Gateと対象確認を終えてから行ってください。

## 作り直す場合

アプリを終了したうえで、`builds\BAI Video Production` と `builds\work` だけを削除してから再実行できます。ソース、Evidence、ユーザープロジェクトは削除しません。

## よくあるエラー

- `Windows build dependencies are missing`: 表示されたPythonで `python -m pip install -e ".[windows-build]"` を実行します。
- `python` が見つからない: `.venv` を作るか、`BVP_BUILD_PYTHON` にPythonのフルパスを指定します。
- WebViewが開かない: Microsoft Edge WebView2 Runtimeを確認します。
- EXEが使用中で上書きできない: 起動中のBAI Video Productionを終了して再実行します。

## このビルドが行わないこと

この手順はローカルの未署名EXEを作るだけです。Tag、GitHub Release、Deploy、Provider呼び出し、有料実行、クレジット購入、Production Activation、DaVinci Resolve/Cubaseプロジェクトへの書き込みは行いません。ビルド成功だけでリリース完了とはみなしません。
