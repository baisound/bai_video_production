"""Pure P-UX-2A0 element/selection inventory for the TASK-036 shell.

The compiler compares already-supplied mock and runtime markup.  It never reads
files, launches a browser, calls a Provider, or treats visual state as Product
truth.  Its output is an immutable audit receipt that makes missing and
intent-only controls explicit before later P-UX-2 slices bind them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from html.parser import HTMLParser
import re
from typing import Any

from .serialization import canonical_json_bytes, sha256_bytes


MAX_MARKUP_BYTES = 2_000_000
MAX_ELEMENTS_PER_SURFACE = 2_000
SHELL_PAGE = "shell"
BROWSER_AUDIT_BASELINE = {
    "mock": {"pages": 14, "buttons": 253, "stable_ids": 205, "selects": 57, "inputs_and_textareas": 83},
    "runtime": {"pages": 14, "buttons": 126, "stable_ids": 109, "selects": 2, "inputs_and_textareas": 7},
}


class ElementKind(str, Enum):
    BUTTON = "BUTTON"
    INPUT = "INPUT"
    TEXTAREA = "TEXTAREA"
    SELECT = "SELECT"
    LABEL = "LABEL"
    CARD = "CARD"
    LIST = "LIST"
    TAB = "TAB"
    STATE = "STATE"
    RESULT = "RESULT"


class ElementContractState(str, Enum):
    BOUND = "BOUND"
    NAVIGATION = "NAVIGATION"
    DISABLED_WITH_REASON = "DISABLED_WITH_REASON"
    DYNAMIC_CONDITIONAL = "DYNAMIC_CONDITIONAL"
    INTENT_ONLY = "INTENT_ONLY"
    MISSING = "MISSING"


class SurfaceLifecycleState(str, Enum):
    LOADING = "LOADING"
    EMPTY = "EMPTY"
    READY = "READY"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class PageServiceContract:
    page_id: str
    owner_tasks: tuple[str, ...]
    source_contracts: tuple[str, ...]
    next_page_id: str | None
    next_identity_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "owner_tasks": list(self.owner_tasks),
            "source_contracts": list(self.source_contracts),
            "next_page_id": self.next_page_id,
            "next_identity_fields": list(self.next_identity_fields),
        }


PAGE_SERVICE_REGISTRY: tuple[PageServiceContract, ...] = (
    PageServiceContract(SHELL_PAGE, ("TASK-036",), ("Task036ShellBridge",), "home", ("project_id",)),
    PageServiceContract("home", ("TASK-043", "TASK-036"), ("ProductProjectApplication",), "planning", ("project_id", "project_revision")),
    PageServiceContract("planning", ("TASK-027",), ("Task027PlanningApplication",), "scenes", ("plan_id", "planning_snapshot_sha256")),
    PageServiceContract("scenes", ("TASK-027", "TASK-005"), ("ProductionBlueprint", "SceneBoundaryManifest"), "locks", ("scene_ids", "blueprint_sha256")),
    PageServiceContract("locks", ("TASK-037", "TASK-038", "TASK-039"), ("ProductionControlApplication", "AuditApplication"), "sceneDesign", ("slot_ids", "lock_receipt_sha256")),
    PageServiceContract("sceneDesign", ("TASK-005", "TASK-013", "TASK-039", "TASK-040"), ("SceneBoundaryManifest", "PromptEvidenceApplication"), "imageGen", ("scene_id", "prompt_id", "prompt_version")),
    PageServiceContract("imageGen", ("TASK-013", "TASK-027"), ("GenerationSafetyApplication",), "videoGen", ("scene_id", "start_candidate_id", "end_candidate_id")),
    PageServiceContract("videoGen", ("TASK-013", "TASK-027", "TASK-040"), ("GenerationQueueApplication", "GenerationExecutionApplication"), "assetReview", ("generation_job_id", "candidate_id")),
    PageServiceContract("audio", ("TASK-014", "TASK-026", "TASK-041", "TASK-046", "TASK-048"), ("AudioWorkspaceApplication", "AudioPlacementApplication"), "assetReview", ("asset_ids", "placement_plan_id")),
    PageServiceContract("assetReview", ("TASK-037", "TASK-038"), ("AuditApplication", "ProductionControlApplication"), "edit", ("candidate_id", "decision_receipt_sha256", "asset_id")),
    PageServiceContract("edit", ("TASK-007", "TASK-022", "TASK-044"), ("InteractiveTimelineApplication", "EditingReviewApplication"), "finalReview", ("timeline_revision_id", "timeline_sha256")),
    PageServiceContract("finalReview", ("TASK-011", "TASK-016", "TASK-036"), ("RenderQaApplication", "FinalReviewAggregateContract"), "export", ("final_approval_receipt_sha256", "timeline_sha256")),
    PageServiceContract("export", ("TASK-011", "TASK-044"), ("ExportQueueApplication", "RenderQaApplication"), None, ("export_job_id", "artifact_sha256", "qa_receipt_sha256")),
    PageServiceContract("assets", ("TASK-003", "TASK-037"), ("ProductionControlApplication",), "edit", ("asset_id", "target_coordinate_sha256")),
    PageServiceContract("quick", ("TASK-027", "TASK-040", "TASK-042"), ("QuickGenerationApplication", "PromptEvidenceApplication"), "assetReview", ("intent_id", "candidate_id")),
)

_PAGE_BY_ID = {item.page_id: item for item in PAGE_SERVICE_REGISTRY}
_EXPECTED_PAGES = tuple(item.page_id for item in PAGE_SERVICE_REGISTRY if item.page_id != SHELL_PAGE)
_INTERACTIVE_TAGS = {"button", "input", "select", "textarea"}
_VOID_TAGS = {"input"}
_LIST_CLASSES = {"content-list", "candgrid", "history", "asset-list", "registry-list"}
_RESULT_CLASSES = {"record", "proposal", "candidate", "frame-preview", "lock-image"}
_IDENTITY_ATTRS = (
    "data-nav", "data-route", "data-menu-button", "data-command",
    "data-settings-view", "data-lock-tab", "data-scene-tab", "data-asset-kind",
    "data-add-track", "aria-label", "name", "placeholder",
)
_SPACE_RE = re.compile(r"\s+")
_CONTRACT_EXTENSION_ATTR = "data-contract-extension"


@dataclass(frozen=True, slots=True)
class SurfaceElement:
    page_id: str
    coordinate: str
    kind: ElementKind
    tag: str
    element_id: str | None
    label: str
    attributes: tuple[tuple[str, str | None], ...]

    @property
    def attribute_map(self) -> dict[str, str | None]:
        return dict(self.attributes)


@dataclass(frozen=True, slots=True)
class SelectionLifecycleContract:
    required_choice_source: tuple[str, ...]
    selected_coordinate: str
    required_validation: tuple[str, ...]
    required_apply_receipt: str
    required_readback: str
    next_page_id: str | None
    next_identity_fields: tuple[str, ...]
    current_state: ElementContractState

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_choice_source": list(self.required_choice_source),
            "selected_coordinate": self.selected_coordinate,
            "required_validation": list(self.required_validation),
            "required_apply_receipt": self.required_apply_receipt,
            "required_readback": self.required_readback,
            "next_page_id": self.next_page_id,
            "next_identity_fields": list(self.next_identity_fields),
            "current_state": self.current_state.value,
        }


@dataclass(frozen=True, slots=True)
class ElementContract:
    page_id: str
    coordinate: str
    kind: ElementKind
    label: str
    mock_present: bool
    runtime_present: bool
    state: ElementContractState
    disabled_reason: str | None
    lifecycle: SelectionLifecycleContract | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "coordinate": self.coordinate,
            "kind": self.kind.value,
            "label": self.label,
            "mock_present": self.mock_present,
            "runtime_present": self.runtime_present,
            "state": self.state.value,
            "disabled_reason": self.disabled_reason,
            "lifecycle": None if self.lifecycle is None else self.lifecycle.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ElementSelectionInventory:
    contract_version: str
    mock_sha256: str
    runtime_sha256: str
    page_contracts: tuple[PageServiceContract, ...]
    elements: tuple[ElementContract, ...]
    supported_lifecycle_states: tuple[SurfaceLifecycleState, ...]
    external_effects_started: bool = False
    provider_execution_authorized: bool = False
    human_decision_inferred: bool = False

    @property
    def inventory_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.to_dict(include_digest=False)))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        state_counts = {state.value: 0 for state in ElementContractState}
        for item in self.elements:
            state_counts[item.state.value] += 1
        value: dict[str, Any] = {
            "contract_version": self.contract_version,
            "mock_sha256": self.mock_sha256,
            "runtime_sha256": self.runtime_sha256,
            "page_contracts": [item.to_dict() for item in self.page_contracts],
            "elements": [item.to_dict() for item in self.elements],
            "state_counts": state_counts,
            "supported_lifecycle_states": [item.value for item in self.supported_lifecycle_states],
            "external_effects_started": self.external_effects_started,
            "provider_execution_authorized": self.provider_execution_authorized,
            "human_decision_inferred": self.human_decision_inferred,
        }
        if include_digest:
            value["inventory_sha256"] = self.inventory_sha256
        return value


class _SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[SurfaceElement] = []
        self.pages: set[str] = set()
        self._page_stack: list[tuple[str, int]] = []
        self._depth = 0
        self._open: list[dict[str, Any]] = []
        self._ordinals: dict[str, int] = {}
        self._ignored_depth: int | None = None

    @property
    def page_id(self) -> str:
        return self._page_stack[-1][0] if self._page_stack else SHELL_PAGE

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        values = dict(attrs)
        if self._ignored_depth is not None:
            if tag in _VOID_TAGS:
                self._depth -= 1
            return
        if values.get(_CONTRACT_EXTENSION_ATTR):
            if tag in _VOID_TAGS:
                self._depth -= 1
            else:
                self._ignored_depth = self._depth
            return
        page = values.get("data-page")
        if tag == "section" and page:
            if page not in _PAGE_BY_ID or page == SHELL_PAGE:
                raise ValueError(f"unsupported page: {page}")
            self.pages.add(page)
            self._page_stack.append((page, self._depth))
        kind = _element_kind(tag, values)
        if kind is None:
            return
        builder = {"tag": tag, "attrs": tuple(sorted(attrs)), "kind": kind, "page": self.page_id, "text": []}
        if tag in _VOID_TAGS:
            self._finish(builder)
            self._depth -= 1
        else:
            builder["depth"] = self._depth
            self._open.append(builder)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._ignored_depth is not None:
            return
        for item in self._open:
            item["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth is not None:
            if self._depth == self._ignored_depth:
                self._ignored_depth = None
            self._depth -= 1
            return
        for index in range(len(self._open) - 1, -1, -1):
            item = self._open[index]
            if item["tag"] == tag and item["depth"] == self._depth:
                self._finish(item)
                del self._open[index]
                break
        if self._page_stack and self._page_stack[-1][1] == self._depth and tag == "section":
            self._page_stack.pop()
        self._depth -= 1

    def _finish(self, builder: dict[str, Any]) -> None:
        attrs = dict(builder["attrs"])
        label = _label("".join(builder["text"]), attrs)
        base = _coordinate_base(builder["page"], builder["kind"], attrs, label)
        ordinal = self._ordinals.get(base, 0) + 1
        self._ordinals[base] = ordinal
        coordinate = base if attrs.get("id") else f"{base}#{ordinal}"
        self.elements.append(SurfaceElement(
            page_id=builder["page"], coordinate=coordinate, kind=builder["kind"], tag=builder["tag"],
            element_id=attrs.get("id"), label=label, attributes=builder["attrs"],
        ))
        if len(self.elements) > MAX_ELEMENTS_PER_SURFACE:
            raise ValueError("surface element cap exceeded")


class _SourceCountParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: set[str] = set()
        self.ids: set[str] = set()
        self.buttons = 0
        self.selects = 0
        self.fields = 0
        self._depth = 0
        self._ignored_depth: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        values = dict(attrs)
        if self._ignored_depth is not None:
            if tag in _VOID_TAGS:
                self._depth -= 1
            return
        if values.get(_CONTRACT_EXTENSION_ATTR):
            if tag in _VOID_TAGS:
                self._depth -= 1
            else:
                self._ignored_depth = self._depth
            return
        if values.get("data-page"):
            self.pages.add(str(values["data-page"]))
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                raise ValueError(f"duplicate stable element id: {element_id}")
            self.ids.add(element_id)
        self.buttons += tag == "button"
        self.selects += tag == "select"
        self.fields += tag in {"input", "textarea"}
        if tag in _VOID_TAGS:
            self._depth -= 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth is not None and self._depth == self._ignored_depth:
            self._ignored_depth = None
        self._depth -= 1


def _element_kind(tag: str, attrs: dict[str, str | None]) -> ElementKind | None:
    classes = set((attrs.get("class") or "").split())
    if "tab" in classes or attrs.get("role") == "tab":
        return ElementKind.TAB
    if tag == "button":
        return ElementKind.BUTTON
    if tag == "input":
        return ElementKind.INPUT
    if tag == "textarea":
        return ElementKind.TEXTAREA
    if tag == "select":
        return ElementKind.SELECT
    if tag == "label":
        return ElementKind.LABEL
    if "card" in classes:
        return ElementKind.CARD
    if classes & _LIST_CLASSES or attrs.get("role") in {"list", "listbox"}:
        return ElementKind.LIST
    if "state" in classes or attrs.get("aria-live"):
        return ElementKind.STATE
    if classes & _RESULT_CLASSES:
        return ElementKind.RESULT
    return None


def _label(text: str, attrs: dict[str, str | None]) -> str:
    value = attrs.get("aria-label") or attrs.get("placeholder") or text
    return _SPACE_RE.sub(" ", value or "").strip()[:160]


def _coordinate_base(page: str, kind: ElementKind, attrs: dict[str, str | None], label: str) -> str:
    if attrs.get("id"):
        return f"{page}/id/{attrs['id']}"
    identity = next((f"{name}={attrs[name]}" for name in _IDENTITY_ATTRS if attrs.get(name)), None)
    if identity is None:
        identity = "label=" + sha256(label.encode("utf-8")).hexdigest()[:16]
    return f"{page}/{kind.value.lower()}/{identity}"


def _parse(markup: str, field_name: str) -> tuple[tuple[SurfaceElement, ...], set[str]]:
    if not isinstance(markup, str):
        raise ValueError(f"{field_name} must be text")
    size = len(markup.encode("utf-8"))
    if not 1 <= size <= MAX_MARKUP_BYTES:
        raise ValueError(f"{field_name} exceeds the bounded markup size")
    parser = _SurfaceParser()
    parser.feed(markup)
    parser.close()
    if tuple(sorted(parser.pages)) != tuple(sorted(_EXPECTED_PAGES)):
        raise ValueError(f"{field_name} page registry is incomplete")
    coordinates = [item.coordinate for item in parser.elements]
    if len(coordinates) != len(set(coordinates)):
        raise ValueError(f"{field_name} has duplicate element coordinates")
    return tuple(parser.elements), parser.pages


def _is_selectable(item: SurfaceElement) -> bool:
    return item.kind in {ElementKind.BUTTON, ElementKind.INPUT, ElementKind.TEXTAREA, ElementKind.SELECT, ElementKind.TAB, ElementKind.CARD}


def _runtime_state(item: SurfaceElement, runtime_markup: str) -> tuple[ElementContractState, str | None]:
    attrs = item.attribute_map
    reason = attrs.get("data-disabled-reason")
    if "disabled" in attrs:
        if reason:
            return ElementContractState.DISABLED_WITH_REASON, reason
        return ElementContractState.INTENT_ONLY, None
    if attrs.get("data-nav") or attrs.get("data-route") or attrs.get("data-menu-button") or attrs.get("data-command"):
        return ElementContractState.NAVIGATION, None
    if item.kind in {ElementKind.LIST, ElementKind.STATE, ElementKind.RESULT}:
        return ElementContractState.DYNAMIC_CONDITIONAL, None
    if not _is_selectable(item):
        return ElementContractState.BOUND, None
    if item.element_id and runtime_markup.count(item.element_id) > 1:
        return ElementContractState.BOUND, None
    for name in _IDENTITY_ATTRS:
        value = attrs.get(name)
        if value and runtime_markup.count(value) > 1:
            return ElementContractState.BOUND, None
    return ElementContractState.INTENT_ONLY, None


def _lifecycle(item: SurfaceElement, state: ElementContractState) -> SelectionLifecycleContract | None:
    if not _is_selectable(item):
        return None
    page = _PAGE_BY_ID[item.page_id]
    choice_source = ("Task036RouteRegistry",) if state is ElementContractState.NAVIGATION else page.source_contracts
    return SelectionLifecycleContract(
        required_choice_source=choice_source,
        selected_coordinate=item.coordinate,
        required_validation=("CURRENT_VALID", "RIGHTS_LICENSE", "CAPABILITY", "RESOURCE", "FRESHNESS"),
        required_apply_receipt="OWNING_SERVICE_TYPED_RECEIPT",
        required_readback="FRESH_SAME_SCREEN_CANONICAL_SNAPSHOT",
        next_page_id=page.next_page_id,
        next_identity_fields=page.next_identity_fields,
        current_state=state,
    )


def compile_element_selection_inventory(mock_markup: str, runtime_markup: str) -> ElementSelectionInventory:
    """Compile a deterministic no-effect union inventory from two markup values."""

    mock, _ = _parse(mock_markup, "mock_markup")
    runtime, _ = _parse(runtime_markup, "runtime_markup")
    mock_by_coordinate = {item.coordinate: item for item in mock}
    runtime_by_coordinate = {item.coordinate: item for item in runtime}
    records: list[ElementContract] = []
    for coordinate in sorted(set(mock_by_coordinate) | set(runtime_by_coordinate)):
        mock_item = mock_by_coordinate.get(coordinate)
        runtime_item = runtime_by_coordinate.get(coordinate)
        source = runtime_item or mock_item
        assert source is not None
        if runtime_item is None:
            state, reason = ElementContractState.MISSING, None
        else:
            state, reason = _runtime_state(runtime_item, runtime_markup)
        records.append(ElementContract(
            page_id=source.page_id,
            coordinate=coordinate,
            kind=source.kind,
            label=source.label,
            mock_present=mock_item is not None,
            runtime_present=runtime_item is not None,
            state=state,
            disabled_reason=reason,
            lifecycle=_lifecycle(source, state),
        ))
    return ElementSelectionInventory(
        contract_version="1.0.0",
        mock_sha256=sha256_bytes(mock_markup.encode("utf-8")),
        runtime_sha256=sha256_bytes(runtime_markup.encode("utf-8")),
        page_contracts=PAGE_SERVICE_REGISTRY,
        elements=tuple(records),
        supported_lifecycle_states=tuple(SurfaceLifecycleState),
    )


def count_source_controls(markup: str) -> dict[str, int]:
    """Return bounded source-markup counts without claiming live-DOM parity."""

    elements, _ = _parse(markup, "markup")
    parser = _SourceCountParser()
    parser.feed(markup)
    parser.close()
    return {
        "pages": len(parser.pages),
        "stable_ids": len(parser.ids),
        "buttons": parser.buttons,
        "selects": parser.selects,
        "inputs_and_textareas": parser.fields,
        "contract_elements": len(elements),
    }


def assert_effect_free_inventory(value: ElementSelectionInventory) -> None:
    if not isinstance(value, ElementSelectionInventory):
        raise ValueError("value must be an ElementSelectionInventory")
    if value.external_effects_started or value.provider_execution_authorized or value.human_decision_inferred:
        raise ValueError("element inventory cannot authorize or report an external effect")


__all__ = [
    "BROWSER_AUDIT_BASELINE", "ElementContract", "ElementContractState", "ElementKind", "ElementSelectionInventory",
    "MAX_ELEMENTS_PER_SURFACE", "MAX_MARKUP_BYTES", "PAGE_SERVICE_REGISTRY",
    "PageServiceContract", "SelectionLifecycleContract", "SurfaceLifecycleState",
    "assert_effect_free_inventory", "compile_element_selection_inventory", "count_source_controls",
]
