from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.game_event_store import GameIntelligenceStore
from ai_video_production.game_intelligence_shell import GameIntelligenceShellApplication
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.timebase import FrameRate


JOB_ID = "JOB-00000000000000000000000000"
PROFILE_ID = "PSN-00000000000000000000000000"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a bounded TASK-049 packaged UI smoke fixture")
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("fixture root must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)

    project = root / "project"
    incoming = root / "incoming"
    project.mkdir()
    incoming.mkdir()
    source = incoming / "synthetic-source.mp4"
    source.write_bytes(b"TASK-049-SYNTHETIC-SOURCE-NOT-REAL-MEDIA")
    analysis = project / "analysis.wav"
    analysis.write_bytes(b"TASK-049-SYNTHETIC-ANALYSIS-NOT-EXECUTED")

    directories = {
        name: project / name
        for name in (
            "assets", "jobs", "model-cache", "transcription", "cut", "handoff", "native-render",
        )
    }
    for directory in directories.values():
        directory.mkdir()

    manifest = ProductProjectManifest.create(
        project_id="task049-r9b2-packaged-smoke",
        project_revision=1,
        product_version="0.21.0",
        timebase=ProjectTimebase(30000, 1001),
        child_bindings=(),
        created_at="2026-08-18T00:00:00.000Z",
        updated_at="2026-08-18T00:00:00.000Z",
    )
    ProductProjectManifestStore.save(project, manifest)

    app = GameIntelligenceShellApplication(project)
    store = GameIntelligenceStore(app.database_path)
    match = GameMatch(
        production_job_id=JOB_ID,
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001),
        status=GameMatchStatus.ANALYZING,
    )
    store.put_match(match)
    evidence = GameEvidence(
        production_job_id=JOB_ID,
        match_id=match.match_id,
        source_asset_id=match.source_asset_id,
        producer="task049.r9b2.synthetic-fixture",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(300, 330),
        confidence_milli=900,
        artifact_ref="fixture://task049-r9b2/window-vault",
    )
    store.append_evidence(evidence)
    event = CanonicalGameEvent(
        match_id=match.match_id,
        revision=1,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=evidence.source_range,
        game_version=match.game_version,
        environment=match.environment,
        perspective=match.perspective,
        state={"fixture": True, "real_media": False},
        confidence_milli=900,
        confirmation_state=EventConfirmationState.NEEDS_REVIEW,
        evidence_refs=(evidence.game_evidence_id,),
        review_status=EventReviewStatus.PENDING,
    )
    store.append_event(event)

    config = {
        "launch_config_version": "1.0.0",
        "project": {
            "project_id": manifest.project_id,
            "display_name": "TASK-049 R9B2 Packaged Smoke",
            "project_root": str(project),
        },
        "paths": {
            "source_roots": [str(incoming)],
            "asset_root": str(directories["assets"]),
            "job_root": str(directories["jobs"]),
            "database_path": str(project / "product.sqlite3"),
            "analysis_source_path": str(source),
            "analysis_audio_path": str(analysis),
            "asr_cache_directory": str(directories["model-cache"]),
            "transcription_output": str(directories["transcription"]),
            "cut_output": str(directories["cut"]),
            "handoff_destination": str(directories["handoff"]),
            "native_render_evidence_root": str(directories["native-render"]),
            "native_render_report_path": str(project / "native-render-report.json"),
        },
        "ingest": {
            "production_job_id": JOB_ID,
            "profile_snapshot_id": PROFILE_ID,
            "owner": "task049-r9b2-smoke",
        },
        "asr": {
            "model": "not-executed",
            "device": "cpu",
            "compute_type": "int8",
            "beam_size": 5,
            "vad_filter": True,
            "allow_model_download": False,
            "language": "ja",
        },
        "resolve": {
            "sandbox_project": "BAI_TASK049_R9B2_SMOKE",
            "timeline_rate": "30000/1001",
            "source_frame_rate": "30000/1001",
        },
    }
    config_path = root / "task049-launch.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    metadata = {
        "fixture_version": "1.0.0",
        "fixture_root": str(root),
        "project_root": str(project),
        "launch_config": str(config_path),
        "game_database": str(app.database_path),
        "match_id": match.match_id,
        "event_id": event.event_id,
        "event_revision": event.revision,
        "expected_initial_confirmation": event.confirmation_state.value,
        "real_media": False,
        "provider_execution_started": False,
        "production_timeline_mutated": False,
        "resolve_write_performed": False,
    }
    metadata_path = root / "task049-fixture-metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
