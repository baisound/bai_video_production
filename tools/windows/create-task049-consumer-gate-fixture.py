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
    parser.add_argument("--root")
    parser.add_argument("--verify-metadata")
    parser.add_argument("--verification-output")
    args = parser.parse_args()

    if bool(args.root) == bool(args.verify_metadata):
        parser.error("specify exactly one of --root or --verify-metadata")
    if args.verify_metadata:
        metadata_path = Path(args.verify_metadata).resolve()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("rights_basis") != "SYNTHETIC_CREATED_FOR_LOCAL_TEST":
            raise ValueError("fixture rights basis mismatch")
        if any(
            metadata.get(name) is not False
            for name in (
                "real_media_used",
                "private_media_used",
                "human_gold_labels_created",
                "provider_execution_started",
                "model_or_runtime_acquired",
                "production_timeline_mutated",
                "resolve_write_performed",
                "release_or_deploy_performed",
            )
        ):
            raise ValueError("fixture non-effect boundary mismatch")
        stored = DbDTriviaStore(metadata["trivia_database"]).latest(metadata["trivia_id"])
        if stored.status is not TriviaStatus.CANDIDATE or stored.title != metadata["trivia_title"]:
            raise ValueError("synthetic trivia candidate read-back mismatch")
        marker = Path(metadata["training_workspace"]) / "workspace.json"
        workspace_payload = json.loads(marker.read_text(encoding="utf-8"))
        if workspace_payload.get("workspace_id") != metadata["training_workspace_id"]:
            raise ValueError("training workspace read-back mismatch")
        verification = {
            "verification_version": "1.0.0",
            "task": "TASK-049",
            "result": "PASS",
            "trivia_id": stored.trivia_id,
            "trivia_status": stored.status.value,
            "training_workspace_id": workspace_payload["workspace_id"],
            "real_media_used": False,
            "human_gold_labels_created": False,
        }
        if args.verification_output:
            output = Path(args.verification_output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(verification, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(verification, ensure_ascii=False, sort_keys=True))
        return 0

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
