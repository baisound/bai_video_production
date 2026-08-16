"""Synthetic-only TASK-005 adapter for exercising the Scene Boundary contract.

This module deliberately accepts only immutable in-memory R0 values.  It has
no media path, byte stream, callback, runner, filesystem, subprocess, network,
provider, model, or native-runtime surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .scene_boundary import (
    DetectedSceneRange,
    DetectorProfile,
    SceneSourceBinding,
    build_scene_boundary_manifest,
)


@dataclass(frozen=True, slots=True, init=False)
class BoundedSyntheticSceneBoundaryDetectorAdapter:
    """Replay one exact, prevalidated in-memory detector proposal set.

    The adapter is a deterministic contract/test seam, not a detector runtime.
    Construction delegates range, coverage, count, and profile validation to
    the canonical R0 manifest compiler.  Detection succeeds only for the
    value-identical source and detector profile bound at construction.
    """

    bound_source: SceneSourceBinding
    bound_profile: DetectorProfile
    proposals: tuple[DetectedSceneRange, ...]

    synthetic_only: ClassVar[bool] = True
    media_read_performed: ClassVar[bool] = False
    external_effect_performed: ClassVar[bool] = False

    def __init__(
        self,
        source: SceneSourceBinding,
        profile: DetectorProfile,
        proposals: tuple[DetectedSceneRange, ...],
    ) -> None:
        if type(source) is not SceneSourceBinding:
            raise TypeError("source must be an exact SceneSourceBinding")
        if type(profile) is not DetectorProfile:
            raise TypeError("profile must be an exact DetectorProfile")
        if type(proposals) is not tuple:
            raise TypeError("proposals must be an exact tuple of DetectedSceneRange")

        if any(type(item) is not DetectedSceneRange for item in proposals):
            raise TypeError("every proposal must be an exact DetectedSceneRange")

        # Canonical R0 is the sole authority for count/range/coverage checks.
        build_scene_boundary_manifest(source, profile, proposals)

        object.__setattr__(self, "bound_source", source)
        object.__setattr__(self, "bound_profile", profile)
        object.__setattr__(self, "proposals", proposals)

    def detect(
        self,
        source: SceneSourceBinding,
        profile: DetectorProfile,
    ) -> tuple[DetectedSceneRange, ...]:
        if source != self.bound_source:
            raise ValueError("ERR_SYNTHETIC_SCENE_SOURCE_MISMATCH")
        if profile != self.bound_profile:
            raise ValueError("ERR_SYNTHETIC_DETECTOR_PROFILE_MISMATCH")
        return self.proposals
