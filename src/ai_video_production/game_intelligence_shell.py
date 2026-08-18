"""TASK-049 R6B/R9B desktop-shell application boundary.

This module projects the already-canonical Game Intelligence stores into the
existing BVP desktop Shell.  It owns no detector/provider execution and never
mutates the BVP Production Timeline, Resolve, or publication state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical_game_event import (
    EventConfirmationState,
    GameEventType,
)
from .errors import ProductError, ProductErrorCategory
from .game_commentary import CommentaryCandidateStore, CommentaryPlanner
from .game_commentary_llm import CommentaryLlmService
from .dbd_commentary_knowledge import DbDTriviaStore, TriviaStatus
from .dbd_trivia_editor import default_trivia_database_path
from .dbd_perk_knowledge import DbDPerkKnowledgeStore
from .dbd_killer_knowledge import DbDKillerKnowledgeStore
from .game_event_store import GameIntelligenceStore
from .game_intelligence_export import GameIntelligenceAnalysisExporter
from .game_intelligence_review import GameIntelligenceReviewService
from .ids import IdKind, validate_id
from .serialization import sha256_bytes


class GameIntelligenceShellApplication:
    """Read/review/export boundary for the TASK-049 V6 UI integration."""

    def __init__(self, project_root: str | Path, *, connection_settings: Any | None = None, provider_execution_service: Any | None = None, trivia_database_path: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.state_root = self.project_root / ".bvp" / "game-intelligence"
        self.database_path = self.state_root / "analysis.sqlite3"
        self.commentary_database_path = self.state_root / "commentary.sqlite3"
        self.perk_database_path = self.state_root / "perk-knowledge.sqlite3"
        self.killer_database_path = self.state_root / "killer-power-knowledge.sqlite3"
        self.trivia_database_path = Path(trivia_database_path) if trivia_database_path is not None else default_trivia_database_path()
        self.connection_settings = connection_settings
        self.provider_execution_service = provider_execution_service

    def _ensure_state_root(self) -> None:
        if self.project_root.exists() and self.project_root.is_symlink():
            raise ProductError(
                "ERR_GAME_SHELL_PROJECT_ROOT_SYMLINK",
                "Game Intelligence project root must not be a symlink",
                ProductErrorCategory.SECURITY,
            )
        if self.state_root.exists() and self.state_root.is_symlink():
            raise ProductError(
                "ERR_GAME_SHELL_STATE_ROOT_SYMLINK",
                "Game Intelligence state root must not be a symlink",
                ProductErrorCategory.SECURITY,
            )
        self.state_root.mkdir(parents=True, exist_ok=True)

    def _stores(self) -> tuple[GameIntelligenceStore, CommentaryCandidateStore]:
        self._ensure_state_root()
        return GameIntelligenceStore(self.database_path), CommentaryCandidateStore(self.commentary_database_path)

    @staticmethod
    def _available_actions(event: Any) -> list[str]:
        actions = ["REJECT", "MARK_UNKNOWN"]
        if event.confirmation_state is EventConfirmationState.CONFIRMED:
            actions.insert(0, "APPROVE")
        elif event.confirmation_state is not EventConfirmationState.REJECTED:
            actions.insert(0, "CONFIRM")
        actions.append("CORRECT")
        return actions

    def snapshot(self, match_id: str | None = None) -> dict[str, Any]:
        store, commentary = self._stores()
        matches = store.list_matches()
        if match_id is not None:
            validate_id(match_id, IdKind.GAME_MATCH)
        selected = None
        if matches:
            selected = store.get_match(match_id) if match_id is not None else matches[0]
        elif match_id is not None:
            # Preserve normal canonical error semantics for an explicitly requested unknown match.
            selected = store.get_match(match_id)

        match_rows: list[dict[str, Any]] = []
        for match in matches:
            events = store.list_events(match.match_id, latest_only=True)
            pending = sum(
                1
                for event in events
                if event.review_status.value == "PENDING"
                or event.confirmation_state
                in {
                    EventConfirmationState.DETECTED,
                    EventConfirmationState.POSSIBLE,
                    EventConfirmationState.UNKNOWN,
                    EventConfirmationState.NEEDS_REVIEW,
                }
            )
            match_rows.append(
                {
                    **match.to_dict(),
                    "event_count": len(events),
                    "pending_review_count": pending,
                }
            )

        event_rows: list[dict[str, Any]] = []
        if selected is not None:
            review_service = GameIntelligenceReviewService(store)
            queue = {item.event.event_id: item for item in review_service.list_queue(selected.match_id)}
            for event in store.list_events(selected.match_id, latest_only=True):
                item = queue[event.event_id]
                validated_commentary = [
                    candidate
                    for candidate in commentary.list_for_event(event.event_id, validated_only=True)
                    if candidate.get("event_revision") == event.revision
                ]
                if len(validated_commentary) > 1:
                    raise ProductError(
                        "ERR_GAME_SHELL_COMMENTARY_SELECTION_REQUIRED",
                        "Multiple validated Commentary candidates require Human selection before Shell projection",
                        ProductErrorCategory.STATE,
                        details={"event_id": event.event_id, "event_revision": event.revision},
                    )
                event_rows.append(
                    {
                        **event.to_dict(),
                        "evidence": [value.to_dict() for value in item.evidence],
                        "reviews": [value.to_dict() for value in item.reviews],
                        "validated_commentary": validated_commentary[0] if validated_commentary else None,
                        "available_actions": self._available_actions(event),
                    }
                )

        trivia_rows = DbDTriviaStore(self.trivia_database_path).list_latest() if self.trivia_database_path.exists() else ()
        return {
            "available": True,
            "task_owner": "TASK-049",
            "llm_commentary_available": self.connection_settings is not None and self.provider_execution_service is not None,
            "llm_execution_requires_explicit_authorization": True,
            "trivia_database": str(self.trivia_database_path),
            "perk_knowledge_configured": self.perk_database_path.exists(),
            "killer_power_knowledge_configured": self.killer_database_path.exists(),
            "trivia_candidate_count": sum(1 for item in trivia_rows if item.status is TriviaStatus.CANDIDATE),
            "trivia_verified_count": sum(1 for item in trivia_rows if item.status is TriviaStatus.VERIFIED),
            "analysis_only": True,
            "standalone_product": False,
            "provider_execution_started": False,
            "paid_execution_authorized": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "external_publish_performed": False,
            "matches": match_rows,
            "selected_match_id": None if selected is None else selected.match_id,
            "selected_match": None if selected is None else selected.to_dict(),
            "events": event_rows,
            "event_type_options": [value.value for value in GameEventType],
            "confirmation_state_options": [value.value for value in EventConfirmationState],
            "native_analysis_baseline_implemented": True,
            "native_analysis_pipeline_connected": False,
            "native_analysis_unavailable_reason": "R10B_REFERENCE_DATA_AND_ROI_CALIBRATION_REQUIRED",
        }

    def review(self, *, event_id: str, action: str, corrected_event_type: str | None = None,
               corrected_confirmation_state: str | None = None, reason_code: str = "HUMAN_UI_REVIEW",
               notes: str = "") -> dict[str, Any]:
        store, _ = self._stores()
        service = GameIntelligenceReviewService(store)
        action = str(action).strip().upper()
        if action == "APPROVE":
            revised = service.approve_confirmed(event_id, reason_code=reason_code, notes=notes)
        elif action == "CONFIRM":
            revised = service.confirm_candidate(event_id, reason_code=reason_code, notes=notes)
        elif action == "REJECT":
            revised = service.reject(event_id, reason_code=reason_code, notes=notes)
        elif action == "MARK_UNKNOWN":
            revised = service.mark_unknown(event_id, reason_code=reason_code, notes=notes)
        elif action == "CORRECT":
            if corrected_event_type is None or corrected_confirmation_state is None:
                raise ProductError(
                    "ERR_GAME_SHELL_CORRECTION_FIELDS_REQUIRED",
                    "Human correction requires both event type and confirmation state",
                    ProductErrorCategory.VALIDATION,
                )
            revised = service.correct(
                event_id,
                corrected_event_type=GameEventType(corrected_event_type),
                corrected_confirmation_state=EventConfirmationState(corrected_confirmation_state),
                reason_code=reason_code,
                notes=notes,
            )
        else:
            raise ProductError(
                "ERR_GAME_SHELL_REVIEW_ACTION_INVALID",
                "Unsupported Game Intelligence review action",
                ProductErrorCategory.VALIDATION,
                details={"action": action},
            )
        return {
            "review_applied": True,
            "event": revised.to_dict(),
            "provider_execution_started": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
        }

    def generate_commentary(self, *, event_id: str, execution_authorized: bool) -> dict[str, Any]:
        if self.connection_settings is None or self.provider_execution_service is None:
            raise ProductError(
                "ERR_GAME_COMMENTARY_LLM_NOT_CONFIGURED",
                "Game Intelligence LLM commentary requires configured BVP AI Connection Settings",
                ProductErrorCategory.STATE,
            )
        if execution_authorized is not True:
            raise ProductError(
                "ERR_GAME_COMMENTARY_LLM_NOT_AUTHORIZED",
                "Provider execution requires an explicit Human authorization for this action",
                ProductErrorCategory.AUTHORIZATION,
            )
        store, commentary_store = self._stores()
        event = store.get_event(event_id)
        perk_store = DbDPerkKnowledgeStore(self.perk_database_path) if self.perk_database_path.exists() else None
        killer_store = DbDKillerKnowledgeStore(self.killer_database_path) if self.killer_database_path.exists() else None
        trivia_store = DbDTriviaStore(self.trivia_database_path)
        plan = CommentaryPlanner().plan(event, perk_store=perk_store, killer_store=killer_store, trivia_store=trivia_store)
        if plan.disposition.value != "PROPOSE":
            return {"generated": False, "reason_codes": list(plan.reason_codes), "provider_execution_started": False}
        candidate = CommentaryLlmService(self.provider_execution_service).draft_persist_and_capture_trivia(
            plan=plan, profile=self.connection_settings.profile, availability=self.connection_settings.availability,
            execution_authorized=True, candidate_store=commentary_store, trivia_store=trivia_store,
        )
        return {
            "generated": True,
            "candidate_id": candidate.candidate_id,
            "status": candidate.status.value,
            "text": candidate.draft.text,
            "validation_errors": list(candidate.validation.errors),
            "provider_execution_started": True,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
        }

    def export_analysis(self, *, match_id: str, destination: str | Path) -> dict[str, Any]:
        validate_id(match_id, IdKind.GAME_MATCH)
        store, commentary = self._stores()
        match = store.get_match(match_id)
        root = Path(destination) / f"BVP_Game_Intelligence_{match.match_id}_r{match.analysis_revision}"
        if root.exists():
            raise ProductError(
                "ERR_GAME_SHELL_EXPORT_EXISTS",
                "Analysis export destination already exists; choose another folder or preserve the existing export",
                ProductErrorCategory.STATE,
                details={"export_name": root.name},
            )
        files = GameIntelligenceAnalysisExporter.export(
            store=store,
            match_id=match_id,
            destination=root,
            commentary_store=commentary,
        )
        artifacts = []
        for kind, path in sorted(files.items()):
            data = path.read_bytes()
            artifacts.append({"kind": kind.upper(), "file_name": path.name, "sha256": sha256_bytes(data), "size_bytes": len(data)})
        return {
            "exported": True,
            "export_name": root.name,
            "artifacts": artifacts,
            "analysis_only": True,
            "host_path_persisted": False,
            "production_timeline_mutated": False,
            "resolve_write_performed": False,
            "external_publish_performed": False,
        }


__all__ = ["GameIntelligenceShellApplication"]
