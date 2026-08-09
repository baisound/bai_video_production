from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import shutil
import wave

from .assets import AssetType, PermissionState, RightsStatus
from .audacity_openvino import AudioAiOperation, AudioAiRequest, AudacityOpenVinoService, SeparationMode
from .derived_assets import sha256_file
from .errors import ProductError
from .ingest import AssetIngestRequest, AssetIngestService
from .paths import LogicalPathResolver, PathMapping, SourcePathPolicy
from .profile import ProfileSnapshot
from .store import SQLiteProductStore


def _pcm16(value: float) -> bytes:
    sample = max(-32768, min(32767, int(round(value * 32767.0))))
    return int(sample).to_bytes(2, byteorder="little", signed=True)


def _write_probe_wav(path: Path, *, kind: str, seconds: float, sample_rate: int = 48000) -> None:
    """Generate deterministic stereo probe material without using user media."""
    frames = max(1, int(seconds * sample_rate))
    rng = random.Random(4004 if kind == "noise" else 4014)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        chunks = bytearray()
        for index in range(frames):
            t = index / sample_rate
            if kind == "noise":
                # Speech-like harmonic carrier plus deterministic broadband noise.
                envelope = 0.55 + 0.45 * math.sin(2.0 * math.pi * 2.3 * t) ** 2
                voiced = (
                    0.24 * math.sin(2.0 * math.pi * 185.0 * t)
                    + 0.10 * math.sin(2.0 * math.pi * 370.0 * t)
                    + 0.06 * math.sin(2.0 * math.pi * 740.0 * t)
                ) * envelope
                noise = 0.16 * rng.uniform(-1.0, 1.0)
                left = voiced + noise
                right = voiced * 0.96 + 0.16 * rng.uniform(-1.0, 1.0)
            elif kind == "music":
                # Deterministic music-like stereo mixture with several harmonic sources.
                beat = 0.5 + 0.5 * math.sin(2.0 * math.pi * 2.0 * t) ** 8
                bass = 0.20 * math.sin(2.0 * math.pi * 82.41 * t)
                chord = (
                    0.10 * math.sin(2.0 * math.pi * 261.63 * t)
                    + 0.08 * math.sin(2.0 * math.pi * 329.63 * t)
                    + 0.07 * math.sin(2.0 * math.pi * 392.00 * t)
                )
                lead = 0.12 * math.sin(2.0 * math.pi * (440.0 + 12.0 * math.sin(2.0 * math.pi * 0.35 * t)) * t)
                transient = 0.10 * beat * rng.uniform(-1.0, 1.0)
                left = bass + chord + lead + transient
                right = bass + chord * 0.92 + 0.11 * math.sin(2.0 * math.pi * 523.25 * t) + transient
            else:
                raise ValueError(f"unknown probe kind: {kind}")
            chunks.extend(_pcm16(left))
            chunks.extend(_pcm16(right))
            if len(chunks) >= 1024 * 1024:
                out.writeframesraw(bytes(chunks))
                chunks.clear()
        if chunks:
            out.writeframesraw(bytes(chunks))


def _asset_summary(asset) -> dict[str, object]:
    return {
        "asset_id": asset.asset_id,
        "logical_uri": asset.logical_uri,
        "checksum": asset.checksum,
        "media_metadata": asset.media_metadata,
        "generation_provenance": asset.generation_provenance,
    }


def _run(evidence_root: Path, timeout_seconds: int) -> dict[str, object]:
    runtime = evidence_root / "_runtime" / "audacity-openvino-behavior"
    if runtime.exists():
        shutil.rmtree(runtime)
    incoming = runtime / "incoming"
    assets = runtime / "assets"
    jobs = runtime / "jobs"
    for path in (incoming, assets, jobs):
        path.mkdir(parents=True, exist_ok=True)

    noise_source = incoming / "synthetic-noise-probe.wav"
    music_source = incoming / "synthetic-music-probe.wav"
    _write_probe_wav(noise_source, kind="noise", seconds=3.0)
    _write_probe_wav(music_source, kind="music", seconds=5.0)

    store = SQLiteProductStore(runtime / "behavior.sqlite3")
    profile = ProfileSnapshot.create("task004-live-behavior", "1.0.0", {"synthetic_probe_only": True})
    job = store.create_job(profile.profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping("asset://", assets.resolve()),
        PathMapping("job://", jobs.resolve()),
    ])
    ingest = AssetIngestService(
        store=store,
        resolver=resolver,
        source_policy=SourcePathPolicy((incoming.resolve(),)),
    )
    noise_asset = ingest.ingest(AssetIngestRequest(
        job.job_id,
        noise_source,
        AssetType.AUDIO,
        RightsStatus.OWNED,
        "BAI_SYNTHETIC_PROBE",
        "task004-live-noise-source",
        commercial_use=PermissionState.ALLOWED,
        derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED,
        generation_provenance={"kind": "TASK004_SYNTHETIC_BEHAVIOR_PROBE", "source": "generated_locally"},
    )).asset
    music_asset = ingest.ingest(AssetIngestRequest(
        job.job_id,
        music_source,
        AssetType.AUDIO,
        RightsStatus.OWNED,
        "BAI_SYNTHETIC_PROBE",
        "task004-live-music-source",
        commercial_use=PermissionState.ALLOWED,
        derivative_allowed=PermissionState.ALLOWED,
        reuse_allowed=PermissionState.ALLOWED,
        generation_provenance={"kind": "TASK004_SYNTHETIC_BEHAVIOR_PROBE", "source": "generated_locally"},
    )).asset

    report: dict[str, object] = {
        "ok": False,
        "probe_kind": "TASK004_AUDACITY_OPENVINO_SYNTHETIC_BEHAVIOR",
        "safety": {
            "user_media_used": False,
            "requires_empty_audacity_project": True,
            "synthetic_inputs_only": True,
            "canonical_product_assets_are_isolated_under_probe_runtime": True,
        },
        "job_id": job.job_id,
        "inputs": {
            "noise": {"path_basename": noise_source.name, "checksum": sha256_file(noise_source), "asset_id": noise_asset.asset_id},
            "music": {"path_basename": music_source.name, "checksum": sha256_file(music_source), "asset_id": music_asset.asset_id},
        },
        "noise_suppression": {"status": "NOT_RUN"},
        "music_separation_2_stem": {"status": "NOT_RUN"},
        "four_stem_status": {
            "status": "NOT_LIVE_VERIFIED",
            "reason": "Installed Intel Audacity OpenVINO descriptor exposes no scriptable separation-mode parameter; 4-stem UI choice is not treated as safely script-selectable.",
        },
    }

    service = AudacityOpenVinoService(store=store, resolver=resolver)
    try:
        noise = service.process(AudioAiRequest(
            production_job_id=job.job_id,
            source_asset_id=noise_asset.asset_id,
            idempotency_key="task004-live-noise-behavior",
            operation=AudioAiOperation.NOISE_SUPPRESSION,
            authorize_execution=True,
            timeout_seconds=timeout_seconds,
        ))
        report["noise_suppression"] = {
            "status": "PASS",
            "operation_status": noise.operation.status,
            "roles": list(noise.roles),
            "outputs": [_asset_summary(asset) for asset in noise.output_assets],
            "manifest_uri": noise.manifest_uri,
            "capability_summary": noise.capability_report,
        }
    except ProductError as exc:
        report["noise_suppression"] = {"status": "FAIL", "error": exc.to_envelope()["error"]}
        return report

    try:
        separation = service.process(AudioAiRequest(
            production_job_id=job.job_id,
            source_asset_id=music_asset.asset_id,
            idempotency_key="task004-live-music-separation-2stem",
            operation=AudioAiOperation.MUSIC_SEPARATION,
            authorize_execution=True,
            separation_mode=SeparationMode.TWO_STEM,
            timeout_seconds=timeout_seconds,
        ))
        report["music_separation_2_stem"] = {
            "status": "PASS",
            "operation_status": separation.operation.status,
            "roles": list(separation.roles),
            "outputs": [_asset_summary(asset) for asset in separation.output_assets],
            "manifest_uri": separation.manifest_uri,
            "capability_summary": separation.capability_report,
        }
    except ProductError as exc:
        report["music_separation_2_stem"] = {"status": "FAIL", "error": exc.to_envelope()["error"]}
        return report

    report["ok"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TASK-004 Audacity/OpenVINO synthetic behavioral probe")
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    if not 30 <= args.timeout_seconds <= 7200:
        parser.error("--timeout-seconds must be 30-7200")
    evidence_root = Path(args.evidence_root).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    report_path = evidence_root / "audacity-openvino-behavior.json"
    try:
        report = _run(evidence_root, args.timeout_seconds)
        rc = 0 if report.get("ok") is True else 2
    except ProductError as exc:
        report = {"ok": False, "error": exc.to_envelope()["error"]}
        rc = 2
    except Exception as exc:
        report = {
            "ok": False,
            "error": {
                "code": "ERR_TASK004_AUDACITY_BEHAVIOR_PROBE_FAILED",
                "category": "EXTERNAL_DEPENDENCY",
                "message": str(exc),
            },
        }
        rc = 3
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": bool(report.get("ok")), "report": str(report_path)}, ensure_ascii=False, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
