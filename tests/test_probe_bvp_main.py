from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "probe_bvp_main.py"
SPEC = importlib.util.spec_from_file_location("probe_bvp_main", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
probe_bvp_main = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe_bvp_main
SPEC.loader.exec_module(probe_bvp_main)


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _project_toml() -> str:
    scripts = {
        command: target
        for command, target, _ in probe_bvp_main.PUBLIC_ENTRYPOINTS.values()
    }
    rows = [
        "[project]",
        'name = "ai-video-production"',
        'version = "0.0.0"',
        "[project.scripts]",
    ]
    rows.extend(f'{command} = "{target}"' for command, target in scripts.items())
    return "\n".join(rows) + "\n"


def _create_repository(root: Path, missing_role: str | None = None) -> str:
    root.mkdir()
    _git(root, "init")
    _git(root, "branch", "-M", "main")
    created_paths: list[str] = []
    required_paths = {
        role: path
        for role, (_, _, path) in probe_bvp_main.PUBLIC_ENTRYPOINTS.items()
    }
    required_paths.update(probe_bvp_main.SOURCE_ENTRYPOINTS)
    required_paths[probe_bvp_main.PROBE_ROLE] = probe_bvp_main.PROBE_PATH
    for role, relative_path in required_paths.items():
        if role == missing_role:
            continue
        path = root.joinpath(*relative_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
        created_paths.append(relative_path)
    (root / "pyproject.toml").write_text(_project_toml(), encoding="utf-8")
    created_paths.append("pyproject.toml")
    _git(root, "add", "--", *created_paths)
    _git(
        root,
        "-c",
        "user.name=BVP Probe Test",
        "-c",
        "user.email=probe-test@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    return _git(root, "rev-parse", "HEAD")


class ProbeBvpMainTests(unittest.TestCase):
    def test_clean_exact_main_is_ready_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            main_sha = _create_repository(repo)

            first = probe_bvp_main.probe_repository(repo, main_sha)
            second = probe_bvp_main.probe_repository(repo, main_sha)

            self.assertEqual(first, second)
            self.assertTrue(first["audit_ready"])
            self.assertTrue(first["execution_ready"])
            self.assertEqual(first["status"], "READY")
            self.assertEqual(first["currentness"], "EXPECTED_MAIN_MATCH")
            self.assertEqual(first["reason_codes"], [])
            self.assertNotIn(str(repo), json.dumps(first, sort_keys=True))
            self.assertEqual(_git(repo, "status", "--porcelain"), "")

    def test_expected_main_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            _create_repository(repo)

            result = probe_bvp_main.probe_repository(repo, "0" * 40)

            self.assertFalse(result["audit_ready"])
            self.assertFalse(result["execution_ready"])
            self.assertIn("EXPECTED_MAIN_MISMATCH", result["reason_codes"])

    def test_invalid_expected_main_is_not_echoed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            _create_repository(repo)
            private_input = "not-a-sha-private-input"

            result = probe_bvp_main.probe_repository(repo, private_input)
            payload = json.dumps(result, sort_keys=True)

            self.assertFalse(result["audit_ready"])
            self.assertIn("EXPECTED_MAIN_SHA_INVALID", result["reason_codes"])
            self.assertIsNone(result["expected_main_sha"])
            self.assertNotIn(private_input, payload)

    def test_wrong_and_detached_branch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            main_sha = _create_repository(repo)
            _git(repo, "checkout", "-b", "feature")
            wrong_branch = probe_bvp_main.probe_repository(repo, main_sha)
            _git(repo, "checkout", "--detach", main_sha)
            detached = probe_bvp_main.probe_repository(repo, main_sha)

            self.assertFalse(wrong_branch["execution_ready"])
            self.assertIn("BRANCH_NOT_MAIN", wrong_branch["reason_codes"])
            self.assertEqual(wrong_branch["branch"], "OTHER")
            self.assertFalse(detached["execution_ready"])
            self.assertIn("DETACHED_HEAD", detached["reason_codes"])
            self.assertEqual(detached["branch"], "DETACHED")

    def test_tracked_and_untracked_changes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            main_sha = _create_repository(repo)
            (repo / "pyproject.toml").write_text(_project_toml() + "# dirty\n")
            tracked = probe_bvp_main.probe_repository(repo, main_sha)
            _git(repo, "checkout", "--", "pyproject.toml")
            (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            untracked = probe_bvp_main.probe_repository(repo, main_sha)

            self.assertFalse(tracked["execution_ready"])
            self.assertEqual(tracked["tracked_change_count"], 1)
            self.assertIn("TRACKED_CHANGES_PRESENT", tracked["reason_codes"])
            self.assertFalse(untracked["execution_ready"])
            self.assertEqual(untracked["untracked_entry_count"], 1)
            self.assertIn("UNTRACKED_ENTRIES_PRESENT", untracked["reason_codes"])

    def test_missing_each_required_entry_fails_closed(self) -> None:
        roles = [*probe_bvp_main.PUBLIC_ENTRYPOINTS, *probe_bvp_main.SOURCE_ENTRYPOINTS]
        roles.append(probe_bvp_main.PROBE_ROLE)
        for role in roles:
            with self.subTest(role=role):
                with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
                    repo = Path(raw) / "repo"
                    main_sha = _create_repository(repo, missing_role=role)
                    result = probe_bvp_main.probe_repository(repo, main_sha)

                    self.assertFalse(result["audit_ready"])
                    self.assertFalse(result["execution_ready"])
                    self.assertIn(role + ":MAIN", result["missing_roles"])
                    self.assertIn("REQUIRED_ENTRY_MISSING", result["reason_codes"])

    def test_invalid_project_identity_and_script_binding_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            _create_repository(repo)
            (repo / "pyproject.toml").write_text(
                _project_toml().replace("ai-video-production", "wrong-project", 1),
                encoding="utf-8",
            )
            _git(repo, "add", "--", "pyproject.toml")
            _git(
                repo,
                "-c",
                "user.name=BVP Probe Test",
                "-c",
                "user.email=probe-test@example.invalid",
                "commit",
                "-m",
                "wrong identity",
            )
            identity = probe_bvp_main.probe_repository(
                repo, _git(repo, "rev-parse", "HEAD")
            )

            self.assertFalse(identity["audit_ready"])
            self.assertIn("PROJECT_IDENTITY_MISMATCH", identity["reason_codes"])

            corrected = _project_toml().replace(
                "ai_video_production.normalization_cli:main",
                "ai_video_production.wrong:main",
            )
            (repo / "pyproject.toml").write_text(corrected, encoding="utf-8")
            _git(repo, "add", "--", "pyproject.toml")
            _git(
                repo,
                "-c",
                "user.name=BVP Probe Test",
                "-c",
                "user.email=probe-test@example.invalid",
                "commit",
                "-m",
                "wrong script binding",
            )
            binding = probe_bvp_main.probe_repository(
                repo, _git(repo, "rev-parse", "HEAD")
            )

            self.assertFalse(binding["audit_ready"])
            self.assertIn(
                "PUBLIC_ENTRYPOINT_BINDING_MISMATCH", binding["reason_codes"]
            )

    def test_non_git_and_subdirectory_are_rejected_without_path_echo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            root = Path(raw)
            non_git = root / "not-git"
            non_git.mkdir()
            non_git_result = probe_bvp_main.probe_repository(non_git)
            repo = root / "repo"
            _create_repository(repo)
            child = repo / "child"
            child.mkdir()
            child_result = probe_bvp_main.probe_repository(child)

            self.assertEqual(non_git_result["reason_codes"], ["NOT_GIT_REPOSITORY"])
            self.assertFalse(non_git_result["execution_ready"])
            self.assertIn("REPOSITORY_ROOT_MISMATCH", child_result["reason_codes"])
            self.assertNotIn(str(root), json.dumps(child_result, sort_keys=True))

    def test_git_command_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            _create_repository(repo)
            with mock.patch.object(
                probe_bvp_main, "_git", side_effect=probe_bvp_main.GitProbeError
            ):
                result = probe_bvp_main.probe_repository(repo)

            self.assertFalse(result["audit_ready"])
            self.assertFalse(result["execution_ready"])
            self.assertEqual(result["reason_codes"], ["NOT_GIT_REPOSITORY"])

    def test_git_failure_after_root_resolution_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            repo = Path(raw) / "repo"
            _create_repository(repo)
            original_git = probe_bvp_main._git

            def _fail_after_root(repo_root, *arguments, **kwargs):
                if arguments == ("rev-parse", "HEAD"):
                    raise probe_bvp_main.GitProbeError("GIT_COMMAND_FAILED")
                return original_git(repo_root, *arguments, **kwargs)

            with mock.patch.object(probe_bvp_main, "_git", _fail_after_root):
                result = probe_bvp_main.probe_repository(repo)

            self.assertFalse(result["audit_ready"])
            self.assertFalse(result["execution_ready"])
            self.assertEqual(result["reason_codes"], ["GIT_COMMAND_FAILED"])

    def test_main_writes_public_safe_result_and_uses_nonzero_for_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bvp-probe-test-") as raw:
            root = Path(raw)
            repo = root / "repo"
            main_sha = _create_repository(repo)
            output = root / "probe.json"

            ready_code = probe_bvp_main.main(
                [
                    "--repo-root",
                    str(repo),
                    "--expected-main-sha",
                    main_sha,
                    "--output",
                    str(output),
                ]
            )
            ready_payload = output.read_text(encoding="utf-8")
            (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            blocked_code = probe_bvp_main.main(
                ["--repo-root", str(repo), "--output", str(output)]
            )
            blocked = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(ready_code, 0)
            self.assertEqual(blocked_code, 2)
            self.assertTrue(ready_payload.endswith("\n"))
            self.assertNotIn(str(repo), ready_payload)
            self.assertFalse(blocked["execution_ready"])


if __name__ == "__main__":
    unittest.main()
