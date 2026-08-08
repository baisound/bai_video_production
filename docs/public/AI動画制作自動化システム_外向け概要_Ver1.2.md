# AI動画制作自動化システム — Project Overview Ver.1.2

## 何を目指しているか

長時間の動画素材から、編集に必要な情報をAIと自動処理で整理し、**DaVinci Resolveで人が安全に仕上げられる状態まで持っていく動画制作基盤**を開発しています。

目標は「AIに全部任せて勝手に公開すること」ではありません。

人の判断を残しながら、素材整理、字幕、シーン把握、見どころ候補、タイムライン作成、品質確認といった時間のかかる作業を自動化し、クリエイターが**構成・演出・最終判断に集中できること**を目指します。

## できるようになること

1. 元動画・音声・画像・字幕などを安全に登録
2. 動画の時間軸や形式を自動確認・正規化
3. 音声認識やシーン解析から内容を構造化
4. 見どころ候補を理由付きで提案
5. 採用した編集案をDaVinci Resolveへ自動配置
6. 人が通常の編集作業として続きを仕上げる
7. 音量・映像・字幕などを公開前に自動チェック
8. 効果音・BGM・ナレーションを生成/取得し、Resolveの適切なAudio Trackへ自動配置
9. 将来は生成映像、自声TTS高度化、縦動画化へ拡張

## このシステムの特徴

### 人間の編集を壊さない

自動生成用Timelineと、人が仕上げるTimelineを分離します。AIが再解析しても、人が行った編集を勝手に上書きしない設計です。

### 途中からやり直せる

長時間動画の処理途中で問題が起きても、完了済み工程をできるだけ再利用し、Checkpointから安全に再開する設計です。

### 「なぜその編集になったか」を残す

字幕、シーン、候補区間、採否、生成素材、処理結果をEvidenceとして残し、後から確認できる構造を採用しています。

### DaVinci Resolveを中心に、交換可能な構造

編集の中心はDaVinci Resolveですが、解析AIや生成AIを一社のサービスへ固定しないAdapter方式を採用します。将来的にはPremiere向け出力やRemotionによる量産動画にも展開できます。

## 現在の進捗 — 2026年8月9日

### 完了

システムの土台となるJob State、ID、Manifest、Asset、権利情報、Checkpoint、Evidence、Path安全性、DB基盤を実装済みです。

### DaVinci Resolve実機接続

DaVinci Resolve Studio 21.0.2.4へのPython Scripting接続を実機で確認しました。Read-only Capability Probeでは、接続・Version取得・Project Manager・Current Project・Media Pool等の基本機能を実測できています。

### Resolve基盤の実機検証完了

専用Sandbox ProjectでProject保存/Export、Bin作成、テスト音声取込、Timeline作成、Timeline配置、Marker追加を実機確認しました。WSL2側からWindows側への認証付きHTTP/JSON通信も、未認証拒否・再接続・同一Endpoint再起動まで確認済みです。これにより、次は動画素材を扱うAsset/Timebase/Timeline Mapping基盤へ進める状態になりました。

## 開発ロードマップ

### Step 1 — 基盤とDaVinci Resolve接続

状態管理、再開、Evidence、実機Capabilityを確立。

### Step 2 — 編集に直結する素材解析

素材取込と時間軸正規化の後、音声認識・SRT生成、無音や「えー」「あのー」などのフィラー/言い直し候補を優先して実装します。Scene解析は並列で精度を高めます。

### Step 3 — Cut・字幕のDaVinci Resolve自動編集

不要区間のCut Planを作り、元動画のカットとSRT/字幕Track配置をResolve上で自動化します。

### Step 4 — SE・BGM・ナレーション

効果音/BGM/ナレーションを生成または取得し、タイミング、Loop、Fade等を含めてResolve Timelineへ配置します。

### Step 5 — 編集精度と生成表現の高度化

Scene/Multimodal/ゲーム別Profile、生成映像、自声TTS高度化、縦動画等を追加します。

### Step 6 — 運用・学習

Privacy Guard、保存管理、Dashboard、公開後Feedback、精度改善を統合。

## 最初の完成イメージ

長時間のゲーム動画を投入すると、システムが素材を確認し、字幕・Scene・見どころ候補を整理。採用候補をEdit Planにまとめ、DaVinci Resolveに自動編集Timelineを作成します。

その後は編集者が通常どおりResolve上で仕上げ、最後に音量・黒画面・字幕などの品質検査を通して完成させます。

**AIが編集者を置き換えるのではなく、編集者が判断するまでの準備時間を大幅に圧縮すること**が、このProjectの中心コンセプトです。

## 現在の開発ステータス

- Foundation: 完了
- DaVinci Resolve Read-only実機接続: 確認済み
- Sandbox編集Capability検証: 完了
- WSL2→Windows IPC基盤: 完了
- 素材解析/自動編集MVP: 次工程から順次実装

未実装機能を完成済みとして扱わず、実機検証を通過した機能から段階的に利用可能へ昇格させる方針です。
