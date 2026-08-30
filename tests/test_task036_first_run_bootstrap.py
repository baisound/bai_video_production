from __future__ import annotations

import json

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.task036_first_run_bootstrap import (
    ensure_first_run_launch_configuration,
)
from ai_video_production.task036_trusted_launcher import Task036LaunchConfiguration


def test_first_run_bootstrap_creates_one_valid_private_configuration(tmp_path) -> None:
    application_root = tmp_path / "local-app-data" / "BAISOUND" / "BAI Video Production"

    path = ensure_first_run_launch_configuration(application_root=application_root)
    first_bytes = path.read_bytes()
    configuration = Task036LaunchConfiguration.load(path)

    assert path == application_root / "control" / "task036-first-run-launch.json"
    assert configuration.project_id == "bvp-first-run-project"
    assert configuration.project_root == application_root / "projects" / "bvp-first-run-project"
    assert configuration.asr_config.allow_model_download is False
    assert configuration.analysis_source_path.is_file()
    assert configuration.analysis_audio_path.is_file()
    assert ensure_first_run_launch_configuration(application_root=application_root) == path
    assert path.read_bytes() == first_bytes


def test_first_run_bootstrap_rejects_malformed_existing_configuration(tmp_path) -> None:
    application_root = tmp_path / "local-app-data"
    config = application_root / "control" / "task036-first-run-launch.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"unexpected": True}), encoding="utf-8")

    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root=application_root)

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_CONFIG_INVALID"


def test_first_run_bootstrap_requires_an_absolute_application_root(tmp_path) -> None:
    with pytest.raises(ProductError) as rejected:
        ensure_first_run_launch_configuration(application_root="relative-root")

    assert rejected.value.code == "ERR_TASK036_FIRST_RUN_PATH_UNSAFE"