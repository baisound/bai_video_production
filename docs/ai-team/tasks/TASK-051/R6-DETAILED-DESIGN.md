# TASK-051 R6 — Unified Learning / Registered-data Review

Governance: `DEV-3 HIGH ASSURANCE`

## Goal
Replace the old Visual-only `学習データを確認` with `学習・登録データを確認`.

Subtabs:
- すべて
- ゲーム情報
- 画像・Crop学習
- 右上通知
- 実況・豆知識
- Human Gold / その他

## Review boundaries
- Game information review operates on the auxiliary Entity Alias index only; it does not silently rewrite canonical game facts.
- Visual review retains relabel/delete controls.
- OCR review supports list/delete and routes deeper editing to the dedicated OCR tab.
- Trivia review supports verify/reject and routes content editing to the R5 append-only editor.
- Human Gold is shown only from bounded known locations; zero state is explicit.
- No unbounded recursive workspace scan is introduced.

## Dashboard
Shows registered counts plus Candidate/Verified counts where those semantics exist.
Zero-state wording is explicit for every data class.
