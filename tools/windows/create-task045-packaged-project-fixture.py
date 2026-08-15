from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore


JOB_ID = "JOB-00000000000000000000000000"
PROFILE_ID = "PSN-00000000000000000000000000"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an owned TASK-045 packaged Project fixture")
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
    source.write_bytes(b"TASK-045-SYNTHETIC-SOURCE")
    analysis = project / "analysis.wav"
    analysis.write_bytes(b"TASK-045-SYNTHETIC-ANALYSIS")
    directories = {
        name: project / name
        for name in (
            "assets", "jobs", "model-cache", "transcription", "cut", "handoff",
            "native-render",
        )
    }
    for directory in directories.values():
        directory.mkdir()

    manifest = ProductProjectManifest.create(
        project_id="task045-release-acceptance",
        project_revision=1,
        product_version="0.20.1",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at="2026-08-15T00:00:00.000Z",
        updated_at="2026-08-15T00:00:00.000Z",
    )
    ProductProjectManifestStore.save(project, manifest)
    config = {
        "launch_config_version": "1.0.0",
        "project": {
            "project_id": manifest.project_id,
            "display_name": "TASK-045 Release Acceptance",
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
            "owner": "task045-acceptance",
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
            "sandbox_project": "BAI_CAPABILITY_PROBE_TASK045_RELEASE",
            "timeline_rate": "30",
            "source_frame_rate": "30",
        },
    }
    config_path = root / "task045-launch.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "fixture_root": str(root),
        "launch_config": str(config_path),
        "project_manifest": str(ProductProjectManifestStore.path(project)),
        "project_manifest_sha256": manifest.project_manifest_sha256,
        "provider_execution_started": False,
        "native_mutation_authorized": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
