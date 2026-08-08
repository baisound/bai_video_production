from __future__ import annotations

import argparse
import json
from pathlib import Path

from .comfyui import ComfyEndpointPolicy, ComfyUIClient, VisualModelFamily, builtin_image_model_profile
from .h3_acceleration import SPECTRUM_CLASS_TYPE
from .h3_single_frame import H3SingleFrameContract, H3SingleFrameMode
from .errors import ProductError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TASK-004 ComfyUI local capability probe")
    p.add_argument("--endpoint", default="http://127.0.0.1:8188")
    p.add_argument("--allow-host", action="append", default=[])
    args = p.parse_args(argv)
    try:
        client = ComfyUIClient(args.endpoint, endpoint_policy=ComfyEndpointPolicy(tuple(args.allow_host)))
        stats = client.system_stats()
        info = client.object_info()
        image_profiles = [builtin_image_model_profile(f).to_dict() for f in (
            VisualModelFamily.FLUX_1_SCHNELL, VisualModelFamily.FLUX_1_DEV, VisualModelFamily.SDXL_1_0,
            VisualModelFamily.SD3_5, VisualModelFamily.SD1_5,
        )]
        single_frame_classes = sorted(set(
            H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT).required_node_classes
            + H3SingleFrameContract(H3SingleFrameMode.START_END_INTERPOLATE).required_node_classes
        ))
        payload = {
            "ok": True, "reachable": True, "class_count": len(info), "system_stats": stats,
            "image_provider_profiles": image_profiles,
            "video_provider_profiles": ["minimax-h3-native", "minimax-h3-easy-compatible"],
            "h3_optional_runtime_capabilities": {
                "spectrum": {"class_type": SPECTRUM_CLASS_TYPE, "available": SPECTRUM_CLASS_TYPE in info, "quality_claim": False},
                "single_frame": {
                    "required_class_types": single_frame_classes,
                    "available": all(name in info for name in single_frame_classes),
                    "external_license_verified": False,
                },
                "foley_fast_32": {"contract_available": True, "live_quality_verified": False, "community_derived": True},
            },
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except ProductError as exc:
        print(json.dumps({"ok": False, "error": exc.to_envelope()["error"]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
