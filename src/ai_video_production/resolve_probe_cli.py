from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from .atomic import AtomicJsonWriter
from .errors import ProductError, ProductErrorCategory
from .ipc_probe import build_ipc_unavailable_report, run_ipc_probe
from .resolve_capabilities import ProbeMode, ResolveCapabilityProbe
from .resolve_sandbox_probe import run_resolve_sandbox_probe
from .resolve_loader import ResolveModuleLoader
from .schema_contracts import validate_instance


def _schema(name: str) -> dict[str, Any]:
    """Load a report schema from checkout or installed package resources."""
    checkout_path = Path(__file__).resolve().parents[2] / "schemas" / name
    if checkout_path.is_file():
        return json.loads(checkout_path.read_text(encoding="utf-8"))
    resource = resources.files("ai_video_production").joinpath("schema_resources", name)
    return json.loads(resource.read_text(encoding="utf-8"))


def _write_report(path: Path, payload: dict[str, Any], schema_name: str) -> None:
    schema = _schema(schema_name)
    AtomicJsonWriter.write(path, payload, validator=lambda value: validate_instance(value, schema))


def _supervision(*, timed_out: bool, timeout_seconds: int, worker_exit_code: int | None) -> dict[str, Any]:
    return {
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "worker_exit_code": worker_exit_code,
    }


def _write_supervision_failure(
    output: Path,
    *,
    kind: str,
    timeout_seconds: int,
    timed_out: bool,
    worker_exit_code: int | None,
) -> None:
    if timed_out:
        code = "ERR_RESOLVE_PROBE_TIMEOUT" if kind == "resolve" else "ERR_RESOLVE_IPC_PROBE_TIMEOUT"
        message = "supervised probe exceeded its execution deadline"
        category = ProductErrorCategory.TIMEOUT
    else:
        code = "ERR_RESOLVE_PROBE_WORKER_FAILED" if kind == "resolve" else "ERR_RESOLVE_IPC_PROBE_WORKER_FAILED"
        message = "supervised probe worker exited without a usable report"
        category = ProductErrorCategory.EXTERNAL_DEPENDENCY

    supervision = _supervision(
        timed_out=timed_out,
        timeout_seconds=timeout_seconds,
        worker_exit_code=worker_exit_code,
    )
    error = ProductError(
        code,
        message,
        category,
        retryable=True,
        details={"timeout_seconds": timeout_seconds, "worker_exit_code": worker_exit_code},
    ).to_envelope()["error"]

    if kind == "resolve":
        payload = ResolveCapabilityProbe(None, module_source_kind="SUPERVISOR_FAILURE").run()
        payload["connection_error"] = error
        payload["supervision"] = supervision
        _write_report(output, payload, "resolve-capability-report.schema.json")
        return

    payload = build_ipc_unavailable_report(
        reason=message,
        supervision=supervision,
    )
    _write_report(output, payload, "resolve-ipc-probe-report.schema.json")


def _run_worker(args: argparse.Namespace) -> int:
    output = Path(args.output)
    if args.kind == "ipc":
        payload = run_ipc_probe()
        _write_report(output, payload, "resolve-ipc-probe-report.schema.json")
        return 0

    loader = ResolveModuleLoader()
    try:
        resolve, source_kind = loader.connect()
    except ProductError as exc:
        source_kind = str(exc.details.get("module_source_kind") or {
            "ERR_RESOLVE_SCRIPT_MODULE_NOT_FOUND": "MODULE_NOT_FOUND",
            "ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED": "MODULE_IMPORT_FAILED",
        }.get(exc.code, "DISCOVERY_OR_CONNECTION_ERROR"))
        payload = ResolveCapabilityProbe(None, module_source_kind=source_kind).run()
        payload["connection_error"] = exc.to_envelope()["error"]
        # Preserve the exact loader/connection failure on the root capability row.
        # Historical reports before TASK-002 Attempt 02 used the generic
        # ERR_RESOLVE_NOT_AVAILABLE here, even when discovery itself failed.
        for row in payload["capabilities"]:
            if row["capability_id"] == "resolve.connection":
                row["error_code"] = exc.code
                row["error_type"] = exc.category.value
                row["notes"] = [exc.message]
                break
    else:
        if args.allow_mutation_probes:
            try:
                if not args.sandbox_project:
                    raise ProductError(
                        "ERR_RESOLVE_SANDBOX_REQUIRED",
                        "--sandbox-project is required for sandbox mutation evidence",
                        ProductErrorCategory.SECURITY,
                    )
                if not args.probe_assets_dir:
                    raise ProductError(
                        "ERR_RESOLVE_PROBE_ASSETS_DIR_REQUIRED",
                        "--probe-assets-dir is required for sandbox mutation evidence",
                        ProductErrorCategory.SECURITY,
                    )
                payload = run_resolve_sandbox_probe(
                    resolve,
                    module_source_kind=source_kind,
                    sandbox_project=args.sandbox_project,
                    probe_assets_dir=Path(args.probe_assets_dir),
                )
            except ProductError as exc:
                payload = ResolveCapabilityProbe(
                    resolve, module_source_kind=source_kind, mode=ProbeMode.SANDBOX_MUTATION
                ).run()
                if args.sandbox_project.startswith("BAI_CAPABILITY_PROBE_"):
                    payload["mutation_gate"] = {
                        "authorized": False,
                        "sandbox_project": args.sandbox_project,
                        "executed": False,
                        "note": "Sandbox mutation was refused before any TASK-002 behavioral change executed.",
                    }
                payload["mutation_error"] = exc.to_envelope()["error"]
                _write_report(output, payload, "resolve-capability-report.schema.json")
                return 2
        else:
            payload = ResolveCapabilityProbe(resolve, module_source_kind=source_kind, mode=ProbeMode.READ_ONLY).run()

    _write_report(output, payload, "resolve-capability-report.schema.json")
    return 0


def _run_supervised(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.allow_mutation_probes and not args.probe_assets_dir:
        # Keep mutation probe media alive after the supervised worker exits so
        # Resolve does not mark the imported test asset offline merely because
        # the worker temporary directory is cleaned up. Sandbox-name safety is
        # enforced inside authorize_mutation_probe before this path is written.
        args.probe_assets_dir = str(output.parent / "probe-assets" / args.sandbox_project)
    with tempfile.TemporaryDirectory(prefix="bai-resolve-probe-") as tmp:
        worker_output = Path(tmp) / output.name
        command = [
            sys.executable,
            "-m",
            "ai_video_production.resolve_probe_cli",
            "--worker",
            "--kind",
            args.kind,
            "--output",
            str(worker_output),
        ]
        if args.allow_mutation_probes:
            command.extend([
                "--allow-mutation-probes",
                "--sandbox-project",
                args.sandbox_project,
                "--probe-assets-dir",
                args.probe_assets_dir,
            ])
            if args.current_project_name:
                command.extend(["--current-project-name", args.current_project_name])
        try:
            result = subprocess.run(command, check=False, timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            _write_supervision_failure(
                output,
                kind=args.kind,
                timeout_seconds=args.timeout_seconds,
                timed_out=True,
                worker_exit_code=None,
            )
            print(f"probe timed out after {args.timeout_seconds}s", file=sys.stderr)
            return 124

        if worker_output.is_file():
            # Preserve a schema-valid worker report even when the worker returns
            # non-zero (for example, a fail-closed sandbox authorization refusal).
            # The caller still receives the non-zero exit code, but the exact
            # structured evidence is not replaced by a generic supervisor error.
            output.write_bytes(worker_output.read_bytes())
            return result.returncode

        _write_supervision_failure(
            output,
            kind=args.kind,
            timeout_seconds=args.timeout_seconds,
            timed_out=False,
            worker_exit_code=result.returncode,
        )
        return result.returncode if result.returncode != 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BAI AI Video Production Resolve capability spike")
    parser.add_argument("--kind", choices=("resolve", "ipc"), default="resolve")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--allow-mutation-probes", action="store_true")
    parser.add_argument("--sandbox-project", default="")
    parser.add_argument("--probe-assets-dir", default="")
    parser.add_argument("--current-project-name", default="")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout_seconds < 1 or args.timeout_seconds > 600:
        raise SystemExit("--timeout-seconds must be 1..600")
    if args.worker:
        return _run_worker(args)
    return _run_supervised(args)


if __name__ == "__main__":
    raise SystemExit(main())
