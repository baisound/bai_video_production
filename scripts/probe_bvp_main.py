from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import tomllib
from typing import Any


SCHEMA_VERSION = "1.0"
PROJECT_NAME = "ai-video-production"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PUBLIC_ENTRYPOINTS = {
    "normalize": (
        "ai-video-normalize",
        "ai_video_production.normalization_cli:main",
        "src/ai_video_production/normalization_cli.py",
    ),
    "transcribe": (
        "ai-video-transcribe",
        "ai_video_production.transcription_cli:main",
        "src/ai_video_production/transcription_cli.py",
    ),
    "cut_candidates": (
        "ai-video-cut-candidates",
        "ai_video_production.cut_candidate_cli:main",
        "src/ai_video_production/cut_candidate_cli.py",
    ),
    "subtitle_workspace": (
        "ai-video-subtitle-workspace",
        "ai_video_production.subtitle_workspace_web:main",
        "src/ai_video_production/subtitle_workspace_web.py",
    ),
    "resolve_subtitle_handoff": (
        "ai-video-resolve-subtitle-handoff",
        "ai_video_production.resolve_subtitle_handoff_cli:main",
        "src/ai_video_production/resolve_subtitle_handoff_cli.py",
    ),
}
SOURCE_ENTRYPOINTS = {
    "native_render_gate": "src/ai_video_production/task011_native_render_gate_cli.py",
    "native_editor_handoff_gate": "src/ai_video_production/task012_native_handoff_gate_cli.py",
}
PROBE_ROLE = "main_probe"
PROBE_PATH = "scripts/probe_bvp_main.py"
_GIT_REPOSITORY_ENV_OVERRIDES = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_WORK_TREE",
}


class GitProbeError(RuntimeError):
    pass


def _git(
    repo_root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    child_environment = os.environ.copy()
    for name in _GIT_REPOSITORY_ENV_OVERRIDES:
        child_environment.pop(name, None)
    child_environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                os.fspath(repo_root),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=child_environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitProbeError("GIT_COMMAND_FAILED") from exc
    if check and completed.returncode != 0:
        raise GitProbeError("GIT_COMMAND_FAILED")
    return completed


def _main_entry(repo_root: Path, relative_path: str) -> tuple[bool, str | None]:
    completed = _git(
        repo_root,
        "ls-tree",
        "refs/heads/main",
        "--",
        relative_path,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return False, None
    line = completed.stdout.strip()
    metadata, separator, observed_path = line.partition("\t")
    fields = metadata.split()
    if separator != "\t" or observed_path != relative_path or len(fields) != 3:
        return False, None
    mode, object_type, object_id = fields
    if mode not in {"100644", "100755"} or object_type != "blob":
        return False, None
    if not COMMIT_PATTERN.fullmatch(object_id):
        return False, None
    return True, object_id


def _is_link_or_reparse(path: Path) -> bool:
    metadata = path.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(file_attributes & reparse_flag)


def _checkout_entry(repo_root: Path, relative_path: str) -> bool:
    candidate = repo_root.joinpath(*relative_path.split("/"))
    try:
        current = repo_root
        for component in relative_path.split("/"):
            current = current / component
            if _is_link_or_reparse(current):
                return False
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError):
        return False
    return stat.S_ISREG(metadata.st_mode)


def _base_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project": PROJECT_NAME,
        "status": "BLOCKED",
        "audit_ready": False,
        "execution_ready": False,
        "branch": "UNKNOWN",
        "head_sha": None,
        "main_sha": None,
        "expected_main_sha": None,
        "currentness": "NOT_CONFIRMED",
        "tracked_change_count": 0,
        "untracked_entry_count": 0,
        "required_entry_count": 0,
        "main_entry_count": 0,
        "checkout_entry_count": 0,
        "entry_digests": {},
        "missing_roles": [],
        "reason_codes": [],
    }


def _probe_repository(
    repo_root: Path, expected_main_sha: str | None = None
) -> dict[str, Any]:
    result = _base_result()
    reasons: set[str] = set()
    missing_roles: set[str] = set()
    entry_digests: dict[str, str] = {}

    if expected_main_sha is not None:
        normalized_expected = expected_main_sha.strip().lower()
        if not COMMIT_PATTERN.fullmatch(normalized_expected):
            reasons.add("EXPECTED_MAIN_SHA_INVALID")
        else:
            result["expected_main_sha"] = normalized_expected
    else:
        normalized_expected = None

    try:
        requested_root = repo_root.resolve(strict=True)
    except OSError:
        result["reason_codes"] = ["NOT_GIT_REPOSITORY"]
        return result
    top_level_result = _git(
        requested_root,
        "rev-parse",
        "--show-toplevel",
        check=False,
    )
    if top_level_result.returncode != 0:
        reason = (
            "GIT_COMMAND_FAILED"
            if (requested_root / ".git").exists()
            else "NOT_GIT_REPOSITORY"
        )
        result["reason_codes"] = [reason]
        return result
    top_level_text = top_level_result.stdout.strip()
    try:
        top_level = Path(top_level_text).resolve(strict=True)
    except OSError:
        result["reason_codes"] = ["NOT_GIT_REPOSITORY"]
        return result

    if requested_root != top_level:
        reasons.add("REPOSITORY_ROOT_MISMATCH")

    head_result = _git(requested_root, "rev-parse", "HEAD", check=False)
    main_result = _git(
        requested_root, "rev-parse", "refs/heads/main", check=False
    )
    branch_result = _git(
        requested_root, "symbolic-ref", "--short", "-q", "HEAD", check=False
    )
    if head_result.returncode == 0 and COMMIT_PATTERN.fullmatch(head_result.stdout.strip()):
        result["head_sha"] = head_result.stdout.strip()
    else:
        reasons.add("HEAD_UNAVAILABLE")
    if main_result.returncode == 0 and COMMIT_PATTERN.fullmatch(main_result.stdout.strip()):
        result["main_sha"] = main_result.stdout.strip()
    else:
        reasons.add("MAIN_REF_UNAVAILABLE")
    if branch_result.returncode == 0 and branch_result.stdout.strip():
        branch_name = branch_result.stdout.strip()
        result["branch"] = "MAIN" if branch_name == "main" else "OTHER"
    else:
        result["branch"] = "DETACHED"
        reasons.add("DETACHED_HEAD")

    if result["branch"] != "MAIN":
        reasons.add("BRANCH_NOT_MAIN")
    if result["head_sha"] is not None and result["main_sha"] is not None:
        if result["head_sha"] != result["main_sha"]:
            reasons.add("HEAD_MAIN_MISMATCH")

    if normalized_expected is None:
        result["currentness"] = "LOCAL_MAIN_ONLY"
        reasons.add("EXPECTED_MAIN_SHA_REQUIRED")
    elif COMMIT_PATTERN.fullmatch(normalized_expected):
        if result["main_sha"] == normalized_expected:
            result["currentness"] = "EXPECTED_MAIN_MATCH"
        else:
            result["currentness"] = "EXPECTED_MAIN_MISMATCH"
            reasons.add("EXPECTED_MAIN_MISMATCH")

    status_result = _git(
        requested_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        check=False,
    )
    if status_result.returncode != 0:
        reasons.add("STATUS_UNAVAILABLE")
    else:
        status_lines = [line for line in status_result.stdout.splitlines() if line]
        result["untracked_entry_count"] = sum(
            line.startswith("??") for line in status_lines
        )
        result["tracked_change_count"] = len(status_lines) - result[
            "untracked_entry_count"
        ]
        if result["tracked_change_count"]:
            reasons.add("TRACKED_CHANGES_PRESENT")
        if result["untracked_entry_count"]:
            reasons.add("UNTRACKED_ENTRIES_PRESENT")

    required_paths: dict[str, str] = {
        role: path for role, (_, _, path) in PUBLIC_ENTRYPOINTS.items()
    }
    required_paths.update(SOURCE_ENTRYPOINTS)
    required_paths[PROBE_ROLE] = PROBE_PATH
    required_paths["project_metadata"] = "pyproject.toml"
    result["required_entry_count"] = len(required_paths)

    for role, relative_path in required_paths.items():
        present, object_id = _main_entry(requested_root, relative_path)
        if present and object_id is not None:
            entry_digests[role] = "git-sha1:" + object_id
            result["main_entry_count"] += 1
        else:
            missing_roles.add(role + ":MAIN")
        if _checkout_entry(requested_root, relative_path):
            result["checkout_entry_count"] += 1
        else:
            missing_roles.add(role + ":CHECKOUT")

    project_identity_ok = False
    console_scripts_ok = False
    pyproject_result = _git(
        requested_root,
        "show",
        "refs/heads/main:pyproject.toml",
        check=False,
    )
    if pyproject_result.returncode == 0:
        try:
            metadata = tomllib.loads(pyproject_result.stdout)
            project = metadata["project"]
            project_identity_ok = project.get("name") == PROJECT_NAME
            scripts = project.get("scripts", {})
            console_scripts_ok = all(
                scripts.get(command) == target
                for command, target, _ in PUBLIC_ENTRYPOINTS.values()
            )
        except (KeyError, TypeError, tomllib.TOMLDecodeError):
            reasons.add("PROJECT_METADATA_INVALID")
    else:
        reasons.add("PROJECT_METADATA_UNAVAILABLE")
    if not project_identity_ok:
        reasons.add("PROJECT_IDENTITY_MISMATCH")
    if not console_scripts_ok:
        reasons.add("PUBLIC_ENTRYPOINT_BINDING_MISMATCH")

    result["entry_digests"] = dict(sorted(entry_digests.items()))
    result["missing_roles"] = sorted(missing_roles)
    if missing_roles:
        reasons.add("REQUIRED_ENTRY_MISSING")

    audit_blockers = {
        "NOT_GIT_REPOSITORY",
        "REPOSITORY_ROOT_MISMATCH",
        "MAIN_REF_UNAVAILABLE",
        "EXPECTED_MAIN_SHA_INVALID",
        "EXPECTED_MAIN_MISMATCH",
        "PROJECT_METADATA_INVALID",
        "PROJECT_METADATA_UNAVAILABLE",
        "PROJECT_IDENTITY_MISMATCH",
        "PUBLIC_ENTRYPOINT_BINDING_MISMATCH",
        "REQUIRED_ENTRY_MISSING",
    }
    result["audit_ready"] = not bool(reasons & audit_blockers)
    result["execution_ready"] = result["audit_ready"] and not bool(reasons)
    result["status"] = "READY" if result["execution_ready"] else "BLOCKED"
    result["reason_codes"] = sorted(reasons)
    return result


def probe_repository(
    repo_root: Path, expected_main_sha: str | None = None
) -> dict[str, Any]:
    try:
        return _probe_repository(repo_root, expected_main_sha)
    except GitProbeError:
        result = _base_result()
        if expected_main_sha is not None:
            normalized_expected = expected_main_sha.strip().lower()
            if COMMIT_PATTERN.fullmatch(normalized_expected):
                result["expected_main_sha"] = normalized_expected
        result["reason_codes"] = ["GIT_COMMAND_FAILED"]
        return result


def _write_result(output: Path, result: dict[str, Any]) -> None:
    output = output.resolve()
    if not output.parent.is_dir():
        raise ValueError("OUTPUT_PARENT_UNAVAILABLE")
    payload = (json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    handle, temporary_name = tempfile.mkstemp(
        prefix=output.name + ".", suffix=".tmp", dir=output.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only BAI VIDEO PRODUCTION main checkout probe"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Expected BAI VIDEO PRODUCTION Git top-level",
    )
    parser.add_argument("--expected-main-sha")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = probe_repository(arguments.repo_root, arguments.expected_main_sha)
    try:
        _write_result(arguments.output, result)
    except (OSError, ValueError):
        return 2
    return 0 if result["execution_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
