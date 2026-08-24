"""Trusted Product integration for TASK-056 semantic speech cues."""

from __future__ import annotations

from importlib import resources
import json
from pathlib import Path
import re
from typing import Any

from .errors import ProductError, ProductErrorCategory
from .semantic_audio_cues import (
    CueReviewState,
    KeywordProfile,
    SpeechCueManifest,
    SpeechCuePublicationService,
)
from .speech_cue_application import SpeechCueApplicationService
from .subtitles import TranscriptManifest
from .task056_human_review import (
    Clock,
    SpeechCueHumanReviewService,
    SpeechCueHumanReviewStore,
    TokenFactory,
)
from .timebase import FrameRate


_DEFAULT_PROFILE_ID = "dbd-chase-call-ja-v1"
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def _default_profile() -> KeywordProfile:
    resource = resources.files("ai_video_production").joinpath(
        "profile_resources", f"{_DEFAULT_PROFILE_ID}.json"
    )
    value = json.loads(resource.read_text(encoding="utf-8"))
    return KeywordProfile.from_dict(value)


class Task056SpeechCueProductApplication:
    """Generate and read one Project-bound, text-free cue publication."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        project_id: str,
        output_directory: str | Path,
        source_frame_rate: FrameRate,
        keyword_profile: KeywordProfile | None = None,
        token_factory: TokenFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        root = Path(project_root)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_TASK056_PROJECT_ROOT_INVALID",
                "TASK-056 project root must be an existing regular directory",
                ProductErrorCategory.VALIDATION,
            )
        resolved_root = root.resolve(strict=True)
        output = Path(output_directory)
        resolved_output = output.resolve(strict=False)
        try:
            resolved_output.relative_to(resolved_root)
        except ValueError as exc:
            raise ProductError(
                "ERR_TASK056_OUTPUT_SCOPE_INVALID",
                "TASK-056 output must remain inside the Product Project",
                ProductErrorCategory.SECURITY,
            ) from exc
        if output.is_symlink() or (output.exists() and not output.is_dir()):
            raise ProductError(
                "ERR_TASK056_OUTPUT_SCOPE_INVALID",
                "TASK-056 output must be a regular directory",
                ProductErrorCategory.SECURITY,
            )
        if (
            not isinstance(project_id, str)
            or not project_id.strip()
            or len(project_id) > 256
            or "\x00" in project_id
        ):
            raise ProductError(
                "ERR_TASK056_PROJECT_ID_INVALID",
                "TASK-056 project identity is invalid",
                ProductErrorCategory.VALIDATION,
            )
        self.project_root = resolved_root
        self.project_id = project_id
        self.output_directory = resolved_output
        self.source_frame_rate = source_frame_rate
        self.keyword_profile = keyword_profile or _default_profile()
        self.human_review = SpeechCueHumanReviewService(
            SpeechCueHumanReviewStore(
                output_directory=self.output_directory,
                project_id=self.project_id,
            ),
            token_factory=token_factory,
            clock=clock,
        )

    def _empty_snapshot(self, *, available: bool, can_generate: bool) -> dict[str, Any]:
        return {
            "available": available,
            "task_owner": "TASK-056",
            "generated": False,
            "can_generate": can_generate,
            "keyword_profile_id": self.keyword_profile.profile_id,
            "confirmed_count": 0,
            "review_count": 0,
            "rejected_count": 0,
            "review_items": [],
            "human_accepted_count": 0,
            "human_rejected_count": 0,
            "pending_review_count": 0,
            "review_revision": 0,
            "human_decisions": {},
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def snapshot(self, transcript: TranscriptManifest | None) -> dict[str, Any]:
        if transcript is None:
            return self._empty_snapshot(available=True, can_generate=False)
        report_path = self.output_directory / "speech-cue-report.json"
        if not report_path.exists():
            return self._empty_snapshot(available=True, can_generate=True)
        publication = SpeechCuePublicationService.read_verified(self.output_directory)
        try:
            publication.manifest.assert_bound_to(
                transcript=transcript,
                keyword_profile=self.keyword_profile,
            )
            projection = json.loads(
                publication.projection_path.read_text(encoding="utf-8")
            )
            manifest_sha = publication.manifest.to_dict()["manifest_sha256"]
            projection_sha = projection["projection_sha256"]
            if not _SHA256.fullmatch(manifest_sha) or not _SHA256.fullmatch(projection_sha):
                raise ValueError("publication digest is invalid")
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ProductError(
                "ERR_TASK056_PUBLICATION_BINDING_INVALID",
                "Speech cue publication differs from the bound Product Transcript",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        human_review = self.human_review.snapshot(publication.manifest)
        human_decisions = human_review.pop("decisions")
        review_items = [
            {
                "cue_id": cue.cue_id,
                "keyword_id": cue.keyword_id,
                "source_start_frame": cue.source_start_frame,
                "source_end_frame_exclusive": cue.source_end_frame_exclusive,
                "confidence": cue.confidence,
                "timing_granularity": cue.timing_granularity.value,
                "review_state": cue.review_state.value,
            }
            for cue in publication.manifest.cues
            if (
                cue.review_state is CueReviewState.REVIEW
                and cue.cue_id not in human_decisions
            )
        ]
        counts = publication.manifest.counts
        return {
            "available": True,
            "task_owner": "TASK-056",
            "generated": True,
            "can_generate": True,
            "source_asset_id": publication.manifest.source_asset_id,
            "keyword_profile_id": publication.manifest.keyword_profile_id,
            "manifest_sha256": manifest_sha,
            "projection_sha256": projection_sha,
            "confirmed_count": counts["confirmed"],
            "review_count": counts["review"],
            "rejected_count": counts["rejected"],
            "review_items": review_items,
            "human_decisions": human_decisions,
            **human_review,
            "transcript_text_exposed": False,
            "host_path_exposed": False,
            "canonical_timeline": False,
            "auto_apply_authorized": False,
        }

    def _bound_manifest(self, transcript: TranscriptManifest) -> SpeechCueManifest:
        publication = SpeechCuePublicationService.read_verified(self.output_directory)
        try:
            publication.manifest.assert_bound_to(
                transcript=transcript,
                keyword_profile=self.keyword_profile,
            )
        except ValueError as exc:
            raise ProductError(
                "ERR_TASK056_PUBLICATION_BINDING_INVALID",
                "Speech cue publication differs from the bound Product Transcript",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        return publication.manifest

    def prepare_human_decision(
        self,
        *,
        transcript: TranscriptManifest,
        cue_id: str,
        decision: str,
    ) -> dict[str, Any]:
        manifest = self._bound_manifest(transcript)
        return self.human_review.prepare(
            manifest,
            cue_id=cue_id,
            decision=decision,
        )

    def cancel_human_decision(self, *, confirmation_id: str) -> dict[str, Any]:
        return self.human_review.cancel(confirmation_id=confirmation_id)

    def apply_human_decision(
        self,
        *,
        transcript: TranscriptManifest,
        confirmation_id: str,
    ) -> dict[str, Any]:
        manifest = self._bound_manifest(transcript)
        return self.human_review.apply(
            manifest,
            confirmation_id=confirmation_id,
            actor_id="desktop-owner",
        )

    def generate(
        self,
        *,
        project_id: str,
        transcript: TranscriptManifest,
    ) -> dict[str, Any]:
        if project_id != self.project_id:
            raise ProductError(
                "ERR_TASK056_PROJECT_SCOPE_MISMATCH",
                "Speech cue request belongs to a different Product Project",
                ProductErrorCategory.SECURITY,
            )
        result = SpeechCueApplicationService.detect_from_transcript(
            transcript,
            source_frame_rate=self.source_frame_rate,
            keyword_profile=self.keyword_profile,
            output_directory=self.output_directory,
            include_review_in_projection=False,
        )
        if result.transcription_publication is not None:
            raise ProductError(
                "ERR_TASK056_PROVIDER_REUSE_VIOLATION",
                "Product cue generation must not start a second transcription",
                ProductErrorCategory.INTERNAL,
            )
        return self.snapshot(transcript)
