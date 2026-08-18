# DbD Data Backup / Restore and PC Migration

This guide covers the portable **DbD Game Intelligence migration bundle** used by `BAI DbD Training Studio.exe`.

Use it when moving reviewed recognition/training/knowledge data to another Windows PC or when creating a portable safety copy before replacing local DbD data.

## What is included

A migration ZIP can contain three independent scopes:

| Scope | Included data |
|---|---|
| Project Game Intelligence | `.bvp/game-intelligence/` CGEL analysis, Human Review, Commentary, Perk Knowledge and Killer/Power Knowledge databases for the selected BVP Project |
| Training Studio workspace | teacher CSV, exact-frame video slices, reference indexes, OCR vocabulary/candidates, transcript artifacts and the Training Studio trivia store |
| Global Trivia Editor knowledge | the global `DbD Commentary Trivia` SQLite database used by `BAI DbD Trivia Editor.exe` |

The bundle records:

- bundle/schema version;
- logical data path instead of machine-specific absolute path;
- file size;
- SHA-256 for every payload;
- manifest SHA-256;
- whether a SQLite file was captured through a consistent SQLite snapshot;
- excluded sensitive-path list.

## What is deliberately NOT included

The migration bundle does **not** contain:

- OpenAI / Anthropic / Google API keys;
- Credential Manager / OS-vault secrets;
- `.env`, credential/secret files, private keys or certificates;
- original DbD source videos that live outside the Training Studio workspace;
- the complete BAI Video Production Project/media library;
- provider accounts or cloud-side data.

Reconfigure provider credentials on the destination PC using the normal AI Connection settings flow.

If a CGEL Project references original media, migrate/copy that BVP Project and its media separately. This DbD migration feature preserves the Game Intelligence data, not the original source movie itself.

## Before creating a backup

For the cleanest cross-store snapshot:

1. Finish any running Training Studio video/OCR/ASR job.
2. Close `BAI Video Production.exe` if you want to include Project Game Intelligence.
3. Close `BAI DbD Trivia Editor.exe`.
4. Open `BAI DbD Training Studio.exe`.
5. Open **Backup / Restore**.

SQLite databases are captured through the SQLite backup API, but stopping writers avoids a cross-database snapshot changing while the portable bundle is assembled.

## Create a migration backup in the GUI

1. Open **Backup / Restore** in Training Studio.
2. Select the data scopes you want.
3. If **Project Game Intelligence** is enabled, press **Project folder...** and select the BAI Video Production Project root.
4. Keep **Training Studio workspace** enabled to move training slices/indexes/CSV/OCR/transcripts.
5. Keep **Global Trivia Editor knowledge DB** enabled to move manually verified trivia.
6. Press **Create backup ZIP**.
7. Save the ZIP to a location outside the live Training Studio data folder, preferably another drive or a transfer folder.

The completion dialog shows the file count, byte count and manifest checksum.

## Restore on another PC

First install/build the same compatible BVP/Training Studio version on the destination PC. Then:

1. Copy the migration ZIP to the destination PC.
2. Close BAI Video Production and Trivia Editor.
3. Start `BAI DbD Training Studio.exe`.
4. Open **Backup / Restore**.
5. If the bundle contains Project Game Intelligence, choose the destination BVP Project root.
6. Press **Preview restore**.
7. Confirm:
   - bundle ID;
   - file count;
   - scopes;
   - conflict count.
8. If the preview is correct, press **Restore**.
9. Confirm the Human replacement dialog if existing data will be replaced.
10. Restart Training Studio and BAI Video Production after restore.

## Restore conflict behavior

Restore is fail-closed by default.

If an existing target file differs from the backup:

```text
Preview
-> conflict detected
-> no write
-> Human explicitly chooses Restore
-> automatic pre-restore safety backup
-> checksum-verified staged restore
```

The safety backup is stored under:

```text
%LOCALAPPDATA%\BAI Video Production\migration-restore-backups
```

If a restore operation fails after writing starts, the implementation restores files from its temporary rollback copy before returning the error.

## Integrity and security checks

Restore rejects:

- unknown bundle format/schema;
- missing or modified manifest;
- unexpected ZIP members;
- duplicate logical paths;
- `..`, absolute, drive-qualified or unsafe paths;
- payload SHA-256 mismatch;
- unsafe symlink destinations;
- a Project-containing bundle when no destination Project is selected;
- existing conflicting data unless replacement is explicitly authorized.

SQLite `-wal` / `-shm` sidecars are not migrated; canonical SQLite snapshots are used instead.

## Default data locations

Training Studio:

```text
%LOCALAPPDATA%\BAI Video Production\training\dbd
```

Global Trivia Editor knowledge:

```text
%LOCALAPPDATA%\BAI Video Production\knowledge\dbd-commentary-knowledge.sqlite3
```

Selected Project Game Intelligence:

```text
<BAI Video Production Project>\.bvp\game-intelligence
```

Environment overrides such as `BVP_DBD_TRAINING_ROOT` and `BVP_DBD_TRIVIA_DB` continue to work; restore targets the configured local roots rather than restoring old machine absolute paths.

## Recommended migration verification

After restore:

1. Open Training Studio and confirm registered samples are visible.
2. Rebuild or open the reference indexes/vocabulary as needed.
3. Open Trivia Editor and confirm verified entries exist.
4. Open the destination BVP Project and Game Intelligence workspace.
5. Confirm existing CGEL Matches/Events/Review state can be read.
6. Run a small held-out recognition sample before deleting the old PC copy.

Keep the original migration ZIP until the destination PC has been verified.

## Related

- [Training Studio usage](DBD-TRAINING-STUDIO-USAGE.md)
- [Training Studio EXE build](../windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md)
- [Windows Game Intelligence environment setup](../windows/WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md)
- [Recognition accuracy and training](../game-intelligence/DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [Commentary Trivia Knowledge](../game-intelligence/DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)
