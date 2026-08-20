# TASK-051 R7K — OCR Review Locale Contract Fix

## Status

`IMPLEMENTED / TARGETED_VERIFICATION_READY / WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

## Finding

After R7J, opening the Training Studio with at least one upper-right notification OCR record can fail while the review surface refreshes with:

`AttributeError: 'OcrVocabularySample' object has no attribute 'language'`

This is a Human Acceptance blocker because a record can be present in `右上通知を学習 > 登録済み一覧` while `学習・登録データを確認 > 右上通知` cannot render that same canonical record.

## Root cause

`OcrVocabularySample` defines the locale field as `locale`. R7J review rendering accidentally referenced a non-existent `language` attribute. The defect is in the review adapter, not in the canonical OCR store and not in the registration path.

## Design decision

- Keep the canonical model unchanged: `OcrVocabularySample.locale`.
- Do not introduce a `language` compatibility alias because that would create a second vocabulary for the same contract.
- Correct the review renderer to use `item.locale`.
- Preserve the Japanese display normalization: `ja-JP` is shown as `日本語`; other locale values are shown verbatim.
- Add a regression test that binds the review source to the actual OCR vocabulary field name.

## Scope

Changed behavior is intentionally bounded to the OCR review presentation contract. No OCR storage schema, semantics store, workspace routing, notification registration, or Task lifecycle state is changed.

## Acceptance

1. Existing upper-right notification records remain readable from the active workspace.
2. `学習・登録データを確認 > 右上通知` renders a non-empty OCR list without startup/navigation exception.
3. `ja-JP` displays as `日本語`.
4. Review continues to read the same canonical OCR/semantic stores used by registration.
5. R7J auto-refresh behavior remains unchanged.
