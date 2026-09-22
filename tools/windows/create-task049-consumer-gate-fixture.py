from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_video_production.dbd_commentary_knowledge import DbDTriviaStore, TriviaStatus
from ai_video_production.dbd_training_studio_foundation import WorkspaceRegistry, WorkspaceService


FIXTURE_TITLE = "TASK-049 synthetic package fixture"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create rights-safe synthetic fixtures for the TASK-049 Windows Consumer Gate"
    )
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("fixture root must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)

    trivia_database = root / "trivia" / "dbd-commentary-knowledge.sqlite3"
    trivia = DbDTriviaStore(trivia_database)
    entry = trivia.create_manual(
        title=FIXTURE_TITLE,
        text=(
            "Synthetic packaging fixture only. It contains no DbD claim, "
            "private media, or Human Gold label."
        ),
        source_ref="fixture://task049-consumer-gate/synthetic-no-game-fact",
        category="PACKAGING_FIXTURE",
        tags=("SYNTHETIC", "NO_GAME_FACT"),
        verify=False,
    )
    if entry.status is not TriviaStatus.CANDIDATE:
        raise AssertionError("synthetic trivia fixture must remain CANDIDATE")

    settings_root = root / "training-settings"
    registry = WorkspaceRegistry(settings_root / "workspace-registry.json")
    workspace = WorkspaceService(registry).create(
        display_name="TASK-049 Synthetic Consumer Gate",
        parent_directory=root / "training-workspaces",
    )

    metadata = {
        "fixture_version": "1.0.0",
        "task": "TASK-049",
        "atomic_unit": "WINDOWS_CONSUMER_GATE",
        "fixture_root": str(root),
        "trivia_database": str(trivia_database.resolve()),
        "trivia_id": entry.trivia_id,
        "trivia_title": entry.title,
        "trivia_status": entry.status.value,
        "training_settings_root": str(settings_root.resolve()),
        "training_workspace": workspace.root_path,
        "training_workspace_id": workspace.workspace_id,
        "rights_basis": "SYNTHETIC_CREATED_FOR_LOCAL_TEST",
        "real_media_used": False,
        "private_media_used": False,
        "human_gold_labels_created": False,
        "provider_execution_started": False,
        "model_or_runtime_acquired": False,
        "production_timeline_mutated": False,
        "resolve_write_performed": False,
        "release_or_deploy_performed": False,
    }
    metadata_path = root / "task049-consumer-gate-fixture.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
