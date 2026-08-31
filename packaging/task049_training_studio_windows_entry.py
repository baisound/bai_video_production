from ai_video_production.dbd_reasoning_local_runtime import (
    prepare_packaged_dbd_compute_profile,
)
from ai_video_production.dbd_training_studio import main


def packaged_main() -> int:
    readback = prepare_packaged_dbd_compute_profile(
        application_family="dbd.training"
    )
    return main(compute_profile_readback=readback)


if __name__ == "__main__":
    raise SystemExit(packaged_main())
