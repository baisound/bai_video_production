from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

from ai_video_production.production_control_store import _exclusive_snapshot_lock


def test_empty_snapshot_lock_initialization_is_inside_exclusive_region(
    tmp_path: Path,
) -> None:
    target = tmp_path / "snapshot.json"
    barrier = Barrier(8)
    sequence_lock = Lock()
    active = 0
    peak = 0

    def enter_once(_: int) -> None:
        nonlocal active, peak
        barrier.wait()
        with _exclusive_snapshot_lock(target):
            with sequence_lock:
                active += 1
                peak = max(peak, active)
            with sequence_lock:
                active -= 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(enter_once, range(8)))

    assert peak == 1
    assert target.with_name(".snapshot.json.lock").read_bytes() == b"0"


def test_repeated_fresh_lock_races_do_not_raise_or_leave_empty_files(
    tmp_path: Path,
) -> None:
    for round_number in range(8):
        target = tmp_path / f"snapshot-{round_number}.json"
        barrier = Barrier(4)

        def enter_once(_: int) -> None:
            barrier.wait()
            with _exclusive_snapshot_lock(target):
                pass

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(enter_once, range(4)))
        assert target.with_name(f".snapshot-{round_number}.json.lock").read_bytes() == b"0"
