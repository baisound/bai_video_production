"""Private one-directory meter worker: fixed mode, metadata-only anonymous pipes."""
from __future__ import annotations

import sys
import threading


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["--bvp-meter-worker-v1"] or getattr(sys, "frozen", False) is not True:
        return 64
    worker = None
    try:
        from ai_video_production.task048_meter_controller_host import (
            Win32MeterOperations, WindowsProjectInspector,
        )
        from ai_video_production.task048_meter_worker import MeterWorker, serve_metadata_stream

        operations = Win32MeterOperations()
        input_handle = operations.standard_pipe(-10)
        output_handle = operations.standard_pipe(-11)
        operations.standard_pipe(-12)
        cancelled = threading.Event()

        class Reader:
            def read(self, count: int) -> bytes:
                while not cancelled.is_set():
                    data = operations.read_pipe_available(input_handle, min(count, 4096))
                    if data is not None:
                        return data
                    cancelled.wait(0.01)
                return b""

        class Writer:
            def write(self, data: bytes) -> int:
                operations.write_bootstrap(output_handle, data)
                return len(data)

            def flush(self) -> None:
                pass

        worker = MeterWorker(WindowsProjectInspector(operations))
        serve_metadata_stream(Reader(), Writer(), worker, cancel_read=cancelled.set)
        return 0
    except BaseException:
        # No traceback, Project root, nonce, policy body or environment output.
        return 97
    finally:
        if worker is not None:
            try:
                worker.close()
            except BaseException:
                return 97


if __name__ == "__main__":
    raise SystemExit(main())
