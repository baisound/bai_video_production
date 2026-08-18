# BAI DbD Trivia Editor Usage

`BAI DbD Trivia Editor.exe` is a small manual registration/review tool for DbD commentary trivia.

Build it first with [Build BAI DbD Trivia Editor EXE](../windows/BUILDING-DBD-TRIVIA-EDITOR-EXE.md).

## Start

```powershell
& ".\builds\BAI DbD Trivia Editor\BAI DbD Trivia Editor.exe"
```

## Default database

On Windows the editor stores trivia in:

```text
%LOCALAPPDATA%\BAI Video Production\knowledge\dbd-commentary-knowledge.sqlite3
```

Override only when needed:

```powershell
$env:BVP_DBD_TRIVIA_DB = "D:\BVP\dbd-trivia.sqlite3"
```

## Register a fact/trivia item

1. Enter a short Title.
2. Enter the trivia text.
3. Add optional Category and comma-separated Tags.
4. Optionally associate CGEL event types such as `WINDOW_VAULT`, `HOOK`, `CHASE_START`.
5. Optionally associate `perk_*`, `killer_*`, or `power_*` entity refs.
6. Enter a source reference.
7. Set LIVE/PTB and optional game-version range.
8. Leave **Register as VERIFIED** off if the statement still needs checking.
9. Press **Register**.


## Import past commentary/transcript

Press **Import commentary file** and choose a UTF-8 `.txt`, `.md`, or `.srt` file. The editor scans bounded trivia-like sentences and stores them as **CANDIDATE** entries.

Import never auto-verifies. Review each candidate before promotion because commentary may contain old-patch information, tactical opinion, jokes, or mistakes.

## Verify extracted candidates

Past-commentary/trancript mining creates CANDIDATE entries. Select an entry and press **Verify selected** only after checking its meaning, patch compatibility, and source.

Use **Reject selected** for incorrect/outdated candidates.

## How the main commentary system uses it

Only VERIFIED, patch-compatible entries are eligible for automatic retrieval. They become bounded `TRIVIA` facts supplied to the commentary LLM. The LLM cannot create a new verified trivia item by itself.

See [DbD Commentary Trivia Knowledge](../game-intelligence/DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md).
