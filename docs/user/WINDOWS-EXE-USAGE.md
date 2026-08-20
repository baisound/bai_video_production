# Windows EXE 利用ガイド

このページは、BAI Video Productionの現在のWindowsテストビルドを **構築した後に、どのように起動・確認・利用するか** を説明します。

EXEをまだ作っていない場合は、先に [Windows EXEビルド手順](../windows/BUILDING-WINDOWS-EXE.md) を実行してください。

> **状態: Alpha / Test build**
>
> 現在のEXEは、BAI Video Productionの統合Desktop Shellと段階的に接続済みの機能を検証するためのものです。すべての動画制作工程や、任意のDead by Daylight動画の完全自動解析がProduction品質で完成しているわけではありません。

## 1. EXEの場所

ビルドに成功すると、リポジトリ配下に次のone-dirアプリが作成されます。

```text
builds\
  BAI Video Production\
    BAI Video Production.exe
    _internal\
```

`BAI Video Production.exe` **だけを別の場所へ移動しないでください**。

`BAI Video Production` フォルダー全体を1つのアプリとして扱います。

## 2. 起動する

PowerShellから起動する場合は、リポジトリルートで次を実行します。

```powershell
& ".\builds\BAI Video Production\BAI Video Production.exe"
```

Explorerから起動する場合は、次をダブルクリックします。

```text
builds\BAI Video Production\BAI Video Production.exe
```

Microsoft Edge WebView2 Runtimeが利用できない場合、Desktop UIが正常に表示されないことがあります。

## 3. 最初に確認する画面

起動後はBAI Video Productionの統合Desktop Shellが開きます。

現在のShellでは、Projectや機能の状態に応じて次のWorkspaceを利用します。

- Home / Edit
- Planning
- Generation関連
- Audio
- Subtitle
- Review
- Production Control
- Export
- Game Intelligence（TASK-049）

未接続・未実装の機能は、利用可能であるかのように自動実行しません。

## 4. 既存Projectを開く

画面の `プロジェクト` またはHomeのProject選択操作から、**既存のBAI Video Production Projectフォルダー**を選択します。

Projectを選択すると、利用可能なCanonical StateがDesktop Shellへ読み込まれます。

注意:

- 不明なフォルダーを既存Projectとして推測して上書きしません。
- 破損・未知Version・互換性不明の状態はfail closedで停止する場合があります。
- Human-owned Projectを暗黙にMigrationしません。

## 5. Mediaを選択する

画面の `メディア` 操作から対象Mediaを選択できます。

Media選択は、外部AIの実行、課金、DaVinci Resolveへの書き込み、公開を自動的に許可するものではありません。

各処理は、それぞれのCapability / Human Gate / Authorityに従います。

## 6. Game Intelligenceを利用する

TASK-049で、V6 Shellへ `Game Intelligence` Workspaceが追加されています。

現在のWorkspaceでは、接続済みのGame Intelligence Project Stateに対して、主に次を確認・操作できます。

```text
Match
  ↓
Canonical Game Event Timeline (CGEL)
  ↓
Event / Evidence
  ↓
Human Review
```

Human Reviewでは、利用可能なEventに対して承認・訂正・Reject・UNKNOWN等のCanonical Reviewを行います。

### 現在できること

- 保存済みGame Intelligence Matchの表示
- CGEL Eventの表示
- Event Evidence / Review状態の確認
- Human ReviewによるEvent状態更新
- 保存後の状態Read-back
- 解析結果のJSON / JSONL / CSV / Markdown / SRT Export Backendの利用

### 現在まだProduction完成扱いではないこと

任意のDbD録画を選択しただけで、すべてのイベント・パーク・キラー・マップをProduction精度で自動認識する機能は、R10Bの実動画・Human Gold Datasetを使った精度開発が必要です。

そのため、現在のWindowsテストEXEでGame Intelligence画面が動作することと、DbD認識精度がProduction Gateを通過したことは別です。


### LLM解説候補を生成する

CGEL EventをHuman Confirmしてあり、SettingsでPlanning用AI Provider/ModelとCredentialが設定済みの場合、Game Intelligenceの **`LLM解説候補を生成`** を利用できます。

ボタンを押しただけでは直ちに実行せず、Provider送信・課金可能性を示す確認ダイアログを表示します。確認した操作だけ `execution_authorized=true` として実行します。

```text
CONFIRMED CGEL Event
+ patch-compatible Perk Knowledge
+ VERIFIED DbD Trivia
-> Commentary Plan
-> configured OpenAI / Anthropic / Google route
-> strict JSON claim response
-> deterministic Fact Validator
-> Commentary Candidate
```

Fact Validatorを通らない候補はVALIDATED扱いになりません。LLM生成だけでCGEL Event、Perk発動、Production Timeline、Resolve、Publishを書き換えることもありません。

LLMが解説中に豆知識らしい文を生成した場合はTrivia Storeへ **CANDIDATE** として抽出できます。自動VERIFIEDにはならず、Trivia Editorで確認してから再利用対象になります。

## 7. TASK-049 Windows packaged smokeを実行する

Game IntelligenceのWindowsテストEXE経路を自動確認する場合は、リポジトリルートのPowerShellで次を実行します。

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\tools\windows\run-task049-r9b2-packaged-smoke.ps1 `
  -EvidenceDirectory .\evidence\task049-r9b2
```

このHarnessは、現在のテストビルドについて少なくとも次を確認します。

```text
Windows EXE build
  ↓
BAI Video Production.exe 起動
  ↓
Game Intelligence Workspace表示
  ↓
Synthetic Event表示
  ↓
Human Confirm
  ↓
アプリ終了 / 再起動
  ↓
Canonical State Read-back
```

詳細は [TASK-049 R9B2 Windows Packaged Smoke](../ai-team/tasks/TASK-049/TASK-049-R9B2-WINDOWS-PACKAGED-SMOKE.md) を参照してください。

このHarnessはSynthetic fixtureを使用するため、DbD実動画の認識精度Evidenceにはなりません。

## 8. アプリを終了する

通常のWindowsアプリと同様にウィンドウを閉じます。

永続化済みCanonical Stateは再起動後にRead-backされる設計です。ただし、処理中のJobや外部Runtimeについては各機能のRecovery / Handoff契約に従ってください。

## 9. EXEを作り直す

アプリを終了した後、ローカル生成物だけを削除して再ビルドできます。

```powershell
Remove-Item -Recurse -Force ".\builds\BAI Video Production" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\builds\work" -ErrorAction SilentlyContinue
.\build-windows-exe.bat
```

ソース、Project、Evidenceを削除する必要はありません。

## 10. よくある問題

### EXEを移動したら起動しない

one-dir形式です。`BAI Video Production.exe`だけを移動せず、`BAI Video Production`フォルダー全体を使用してください。

### UIが開かない

Microsoft Edge WebView2 Runtimeと、Windows Event Viewer / Terminalへ出た起動エラーを確認してください。

### Game Intelligenceが「未接続」になる

現在選択しているProjectにGame Intelligence Stateが存在するかを確認してください。任意の動画を選択しただけで自動的にProduction品質の解析Stateを作る段階にはまだ到達していません。

### ProviderやResolveが勝手に実行されない

正常です。Projectを開くこと、Mediaを選ぶこと、Game Intelligenceを表示することだけでは、Provider実行・課金・Resolve mutation・公開Authorityは発生しません。

## 11. 関連ページ

- [Windows EXEビルド手順](../windows/BUILDING-WINDOWS-EXE.md)
- [統合Desktop Applicationの位置付け](UNIFIED-DESKTOP-APPLICATION.md)
- [やさしい導入ガイド](GETTING-STARTED.md)
- [TASK-049 R9B2 Windows Packaged Smoke](../ai-team/tasks/TASK-049/TASK-049-R9B2-WINDOWS-PACKAGED-SMOKE.md)

## 12. DbD recognition, LLM, and trivia knowledge

TASK-049 includes deterministic recognition baselines and ports for:

- lower-left Survivor HUD state slices;
- upper-right notification OCR;
- bottom-right four perk slots;
- Killer / Power reference recognition and patch-aware knowledge;
- Cross-modal Fusion;
- configured OpenAI / Anthropic / Google commentary drafting through the existing BVP provider boundary.

Provider execution remains explicitly authorized. Recognition components return UNKNOWN when evidence is weak and do not claim Production accuracy without a real-media Human Gold benchmark.

Accuracy improvement and slice-data training:

- [DbD Recognition Accuracy and Training](../game-intelligence/DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [DbD Slice Dataset Guide](../game-intelligence/DBD-SLICE-DATASET-GUIDE.md)

DbD commentary trivia can be maintained with a separate small editor:

- [Build BAI DbD Trivia Editor EXE](../windows/BUILDING-DBD-TRIVIA-EDITOR-EXE.md)
- [BAI DbD Trivia Editor Usage](DBD-TRIVIA-EDITOR-USAGE.md)
- [DbD Commentary Trivia Knowledge](../game-intelligence/DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)

## DbD teacher-data / learning companion

The main `BAI Video Production.exe` is the Product entrypoint for analysis and production workflows. DbD teacher-data preparation is handled by the bounded companion utility **BAI DbD Training Studio** so dataset maintenance does not require opening a production Project.

- [Build BAI DbD Training Studio EXE](../windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md)
- [BAI DbD Training Studio Usage](DBD-TRAINING-STUDIO-USAGE.md)

The Training Studio supports single registration, CSV one/many and direct video learning for the current DbD recognition baseline.


### DbD lower-left Item / Add-on recognition

A calibrated HUD profile may additionally define a lower-left loadout parent ROI, one Item slot, and two Add-on slots. These are recognized independently from Survivor status and are bound to patch-compatible `ITEM` / `ADDON` knowledge references when the corresponding Knowledge Store is available. Missing calibration fails closed instead of guessing coordinates.
