"""Credential-free five-minute demonstration of core deterministic contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from . import __version__
from .ai_connections import (
    AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability,
    CostClass, ModelRoute, ProviderFamily, SelectionMode,
)
from .ids import IdKind, generate_id
from .atomic import AtomicJsonWriter
from .serialization import canonical_json_bytes, sha256_bytes
from .timebase import FrameRate
from .timeline_mapping import EditSegment, TimelineMappingService


def build_demo_document() -> dict[str, object]:
    """Build a deterministic-shape demo without credentials, network, or paid APIs."""
    route = ModelRoute(
        route_id="local-planning-demo",
        workload=AiWorkload.PLANNING,
        provider_family=ProviderFamily.LOCAL_OPEN_SOURCE,
        provider_id="local-demo",
        model_id="no-network-demo",
        cost_class=CostClass.LOCAL_FREE_AI,
        priority=1,
        capabilities=("SCRIPT_PLANNING",),
    )
    profile = AiConnectionProfile("quickstart", "1.0.0", SelectionMode.OFFLINE_ONLY, (route,))
    selected = AiConnectionResolver.resolve(
        profile,
        AiWorkload.PLANNING,
        ConnectionAvailability(frozenset({route.route_id})),
        required_capabilities=("SCRIPT_PLANNING",),
    )
    source_asset_id = generate_id(IdKind.ASSET)
    plan = TimelineMappingService.build(
        (
            EditSegment("intro", source_asset_id, 0, 2_000_000),
            EditSegment("main", source_asset_id, 2_000_000, 7_000_000, gap_before_frames=15),
        ),
        timeline_rate=FrameRate(30000, 1001),
    )
    body: dict[str, object] = {
        "demo_version": "1.0.0",
        "package_version": __version__,
        "network_used": False,
        "credentials_used": False,
        "paid_provider_used": False,
        "selected_route": selected.to_dict(),
        "timeline_plan": plan.to_dict(),
        "next_step": "Replace synthetic IDs with ingested Assets; no media was uploaded or modified.",
    }
    body["demo_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("quickstart-output.json"))
    args = parser.parse_args(argv)
    document = build_demo_document()
    AtomicJsonWriter.write(args.output.resolve(), document)
    print(json.dumps({"ok": True, "output": str(args.output), "sha256": document["demo_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
