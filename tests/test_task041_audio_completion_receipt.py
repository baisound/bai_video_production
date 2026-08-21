from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import pickle

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.audio_completion_receipt as contract
from ai_video_production.audio_completion_receipt import (
    AudioCompletionAdmissionCandidate,
    AudioCompletionRole,
    CanonicalState,
    CandidateState,
    EvidenceBinding,
    EvidenceState,
    FinishingRequirement,
    RoleDeclaration,
    RolePresence,
    RoleRequirement,
    ScopeBinding,
    make_closed_receipt_ref,
    parse_audio_completion_admission_candidate,
    validate_audio_completion_transition,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "audio-completion-receipt.schema.json"
MIRROR_PATH = ROOT / "src" / "ai_video_production" / "schema_resources" / "audio-completion-receipt.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
D = "sha256:" + "a" * 64
ROLE_ORDER = tuple(AudioCompletionRole)


def scope(tag: str = "a") -> ScopeBinding:
    return ScopeBinding.create(
        project_id="project-1", project_revision=3, project_manifest_sha256="sha256:" + tag * 64,
        timeline_id="timeline-1", timeline_revision=7, timeline_sha256="sha256:" + "b" * 64,
        workspace_snapshot_sha256="sha256:" + "c" * 64, source_truth_receipt_id="audio-source-1",
        source_truth_receipt_sha256="sha256:" + "d" * 64,
        role_policy_receipt_id="audio-role-policy-1",
        role_policy_receipt_sha256="sha256:" + "9" * 64,
    )


def ref(kind: str, suffix: str):
    return make_closed_receipt_ref(kind, record_id=f"{kind}-{suffix}", record_sha256=D)


def binding(role: AudioCompletionRole, item_id: str, *, state=EvidenceState.PASS,
            finishing=False) -> EvidenceBinding:
    return EvidenceBinding.create(
        item_id=item_id, role=role, item_source_sha256="sha256:" + "e" * 64,
        review_receipt=ref("review_receipt", item_id),
        external_review_receipt=ref("external_review_receipt", item_id),
        placement_receipt=ref("placement_receipt", item_id),
        narration_publication_receipt=(
            ref("narration_publication_receipt", item_id)
            if role is AudioCompletionRole.NARRATION else None
        ),
        finishing_receipt=ref("finishing_receipt", item_id) if finishing else None,
        evidence_state=state,
        evidence_current_at_evaluation=state in {EvidenceState.PASS, EvidenceState.FAIL, EvidenceState.UNKNOWN},
        evidence_invalidation_epoch=1 if state in {EvidenceState.STALE, EvidenceState.REVOKED} else 0,
    )


def declarations(items=(), *, unknown_role=None, finishing_required=()):
    by_role = {role: [] for role in ROLE_ORDER}
    for item in items:
        by_role[AudioCompletionRole(item.to_dict()["role"])].append(item)
    result = []
    for role in ROLE_ORDER:
        role_items = sorted(by_role[role], key=lambda item: item.to_dict()["item_id"].casefold())
        requirement = RoleRequirement.REQUIRED if role is AudioCompletionRole.SOURCE else RoleRequirement.OPTIONAL
        if role_items:
            presence = RolePresence.UNKNOWN if role is unknown_role else RolePresence.PRESENT
        else:
            presence = RolePresence.UNKNOWN if role is unknown_role else RolePresence.ABSENT_CONFIRMED
        finish = (
            FinishingRequirement.REQUIRED if role in finishing_required
            else FinishingRequirement.OPTIONAL if role in {AudioCompletionRole.NARRATION, AudioCompletionRole.MIX_STEM}
            else FinishingRequirement.NOT_APPLICABLE
        )
        result.append(RoleDeclaration(
            role, requirement, presence, finish,
            tuple(item.to_dict()["item_id"] for item in role_items),
            tuple(item.to_dict()["evidence_binding_sha256"] for item in role_items),
        ))
    return tuple(result)


def candidate(items=None, *, roles=None, previous=None, at="2026-08-21T01:00:00Z"):
    if items is None:
        items = (binding(AudioCompletionRole.SOURCE, "source-main"),)
    ordered = tuple(sorted(items, key=lambda item: (
        ROLE_ORDER.index(AudioCompletionRole(item.to_dict()["role"])),
        item.to_dict()["item_id"].casefold(),
    )))
    return AudioCompletionAdmissionCandidate.create(
        receipt_id="audio-completion-1", scope=scope(),
        role_declarations=roles or declarations(ordered), evidence_bindings=ordered,
        evaluated_at=at, previous=previous,
    )


def assert_contract(value):
    VALIDATOR.validate(value)
    assert parse_audio_completion_admission_candidate(value).to_dict() == value


def resign(value):
    value["receipt_sha256"] = sha256_bytes(
        contract._PRIVATE_DOMAIN + canonical_json_bytes(
            {key: item for key, item in value.items() if key != "receipt_sha256"}
        )
    )


def observed_candidate(items, roles):
    """Synthetic diagnostic fixture; production create cannot emit non-READY."""
    ordered = tuple(sorted(items, key=lambda item: (
        ROLE_ORDER.index(AudioCompletionRole(item.to_dict()["role"])),
        item.to_dict()["item_id"].casefold(),
    )))
    value = candidate().to_dict()
    value["role_declarations"] = [item.to_dict() for item in roles]
    value["evidence_bindings"] = [item.to_dict() for item in ordered]
    state, reasons = contract._classify(roles, ordered)
    value["candidate_state"] = state.value
    value["reason_codes"] = list(reasons)
    resign(value)
    return parse_audio_completion_admission_candidate(value)


def test_ready_candidate_has_exact_scope_six_roles_and_schema_parity():
    record = candidate().to_dict()
    assert record["candidate_state"] == CandidateState.SOURCE_REVALIDATION_REQUIRED.value
    assert record["canonical_state"] == CanonicalState.NOT_MINTED.value
    assert [item["role"] for item in record["role_declarations"]] == [role.value for role in ROLE_ORDER]
    assert record["scope_binding"]["project_revision"] == 3
    assert record["scope_binding"]["timeline_revision"] == 7
    assert_contract(record)


def test_multi_item_role_order_and_full_item_closure():
    items = (
        binding(AudioCompletionRole.SOURCE, "source-main"),
        binding(AudioCompletionRole.BGM, "bgm-a"),
        binding(AudioCompletionRole.BGM, "bgm-b"),
        binding(AudioCompletionRole.NARRATION, "narration-a"),
        binding(AudioCompletionRole.MIX_STEM, "mix-a", finishing=True),
    )
    record = candidate(items, roles=declarations(items, finishing_required={AudioCompletionRole.MIX_STEM})).to_dict()
    assert record["candidate_state"] == "SOURCE_REVALIDATION_REQUIRED"
    assert len(record["evidence_bindings"]) == 5
    assert_contract(record)


def test_required_and_optional_absence_matrix_is_fail_closed():
    with pytest.raises(ValueError):
        RoleDeclaration(AudioCompletionRole.SOURCE, RoleRequirement.REQUIRED,
            RolePresence.ABSENT_CONFIRMED, FinishingRequirement.NOT_APPLICABLE, (), ())
    with pytest.raises(ValueError):
        RoleDeclaration(AudioCompletionRole.SE, RoleRequirement.OPTIONAL,
            RolePresence.PRESENT, FinishingRequirement.NOT_APPLICABLE, (), ())
    optional_absent = declarations((binding(AudioCompletionRole.SOURCE, "source-main"),))[1]
    assert optional_absent.presence is RolePresence.ABSENT_CONFIRMED
    assert optional_absent.expected_item_ids == ()


def test_unknown_presence_and_evidence_states_classify_without_minting():
    source = binding(AudioCompletionRole.SOURCE, "source-main")
    se = binding(AudioCompletionRole.SE, "se-expected")
    unknown_roles = declarations((source, se), unknown_role=AudioCompletionRole.SE)
    assert observed_candidate((source,), unknown_roles).to_dict()["candidate_state"] == "SOURCE_REVALIDATION_REQUIRED"
    with pytest.raises(ValueError, match="unknown role cannot carry"):
        observed_candidate((source, se), unknown_roles)
    unknown = binding(AudioCompletionRole.SOURCE, "source-main", state=EvidenceState.UNKNOWN)
    assert observed_candidate((unknown,), declarations((unknown,))).to_dict()["reason_codes"] == ["SOURCE_RECORDS_REQUIRE_OWNER_API_REVALIDATION"]
    failed = binding(AudioCompletionRole.SOURCE, "source-main", state=EvidenceState.FAIL)
    assert observed_candidate((failed,), declarations((failed,))).to_dict()["candidate_state"] == "SOURCE_REVALIDATION_REQUIRED"
    stale = binding(AudioCompletionRole.SOURCE, "source-main", state=EvidenceState.STALE)
    assert observed_candidate((stale,), declarations((stale,))).to_dict()["reason_codes"] == ["SOURCE_RECORDS_REQUIRE_OWNER_API_REVALIDATION"]


def test_unknown_role_duplicate_expected_hashes_fail_closed_locally_and_in_schema():
    with pytest.raises(ValueError, match="unique within a role"):
        RoleDeclaration(
            AudioCompletionRole.SE, RoleRequirement.OPTIONAL, RolePresence.UNKNOWN,
            FinishingRequirement.NOT_APPLICABLE, ("se-a", "se-b"), (D, D),
        )
    record = candidate().to_dict()
    role = record["role_declarations"][1]
    role["presence"] = "UNKNOWN"
    role["expected_item_ids"] = ["se-a", "se-b"]
    role["expected_item_binding_sha256s"] = [D, D]
    assert list(VALIDATOR.iter_errors(record))
    with pytest.raises(ValueError, match="unique within a role"):
        parse_audio_completion_admission_candidate(record)


def test_unknown_roles_cannot_reuse_an_expected_hash_across_roles():
    source = binding(AudioCompletionRole.SOURCE, "source-main")
    roles = list(declarations((source,)))
    roles[1] = RoleDeclaration(
        AudioCompletionRole.SE, RoleRequirement.OPTIONAL, RolePresence.UNKNOWN,
        FinishingRequirement.NOT_APPLICABLE, ("se-a",), (D,),
    )
    roles[2] = RoleDeclaration(
        AudioCompletionRole.BGM, RoleRequirement.OPTIONAL, RolePresence.UNKNOWN,
        FinishingRequirement.NOT_APPLICABLE, ("bgm-a",), (D,),
    )
    with pytest.raises(ValueError, match="duplicated or undeclared"):
        candidate((source,), roles=tuple(roles))


def test_present_requires_full_closure_and_extra_undeclared_rejects():
    item = binding(AudioCompletionRole.SOURCE, "source-main")
    roles = declarations((item,))
    with pytest.raises(ValueError, match="exact item evidence closure"):
        observed_candidate((), roles)
    extra = binding(AudioCompletionRole.SE, "se-extra")
    with pytest.raises(ValueError):
        candidate((item, extra), roles=roles)


def test_closed_receipt_matrix_rejects_plan_candidate_preflight_and_wrong_owner():
    for wrong in ("AudioPlacementPlan", "AudioPlacementCandidate", "AudioPlacementPreflight", "SyntheticPlan"):
        value = ref("placement_receipt", "x").to_dict()
        value["record_type"] = wrong
        with pytest.raises(ValueError):
            contract.ClosedReceiptRef.from_dict(value, "placement_receipt")
    value = ref("review_receipt", "x").to_dict()
    value["authority_owner"] = "TASK-026"
    with pytest.raises(ValueError):
        contract.ClosedReceiptRef.from_dict(value, "review_receipt")


def test_narration_publication_is_required_only_for_narration():
    narration = binding(AudioCompletionRole.NARRATION, "narration-a").to_dict()
    narration["narration_publication_receipt"] = None
    with pytest.raises(ValueError):
        EvidenceBinding.from_dict(narration)
    source = binding(AudioCompletionRole.SOURCE, "source-main").to_dict()
    source["narration_publication_receipt"] = ref("narration_publication_receipt", "x").to_dict()
    with pytest.raises(ValueError):
        EvidenceBinding.from_dict(source)


def test_finishing_policy_is_conditional_and_exact():
    source = binding(AudioCompletionRole.SOURCE, "source-main")
    mix = binding(AudioCompletionRole.MIX_STEM, "mix-a")
    roles = declarations((source, mix), finishing_required={AudioCompletionRole.MIX_STEM})
    with pytest.raises(ValueError, match="required finishing"):
        observed_candidate((source, mix), roles)

    finished = binding(AudioCompletionRole.MIX_STEM, "mix-a", finishing=True)
    result = candidate((source, finished), roles=declarations(
        (source, finished), finishing_required={AudioCompletionRole.MIX_STEM})).to_dict()
    assert result["candidate_state"] == "SOURCE_REVALIDATION_REQUIRED"

    source_finished = binding(AudioCompletionRole.SOURCE, "source-main", finishing=True)
    with pytest.raises(ValueError, match="not-applicable"):
        observed_candidate((source_finished,), declarations((source_finished,)))


def test_item_order_casefold_duplicates_and_undeclared_hashes_reject():
    a = binding(AudioCompletionRole.BGM, "Bgm")
    b = binding(AudioCompletionRole.BGM, "bgm")
    with pytest.raises(ValueError):
        declarations((binding(AudioCompletionRole.SOURCE, "source-main"), a, b))
    record = candidate().to_dict()
    record["evidence_bindings"][0]["evidence_binding_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError):
        parse_audio_completion_admission_candidate(record)


def test_create_can_only_emit_not_minted_noncurrent_no_authority_no_effect():
    record = candidate().to_dict()
    assert record["canonical_state"] == "NOT_MINTED"
    assert record["current_valid"] is False and record["invalidation_epoch"] == 0
    assert set(record["authority_flags"].values()) == {False}
    assert set(record["effect_flags"].values()) == {False}
    assert not {"latest_receipt_sha256", "is_latest", "latest_revision"} & set(record)
    assert record["inputs_origin_authenticated"] is False
    assert record["source_records_semantically_revalidated"] is False


@pytest.mark.parametrize("state", ["PASS", "FAIL", "UNKNOWN", "STALE", "REVOKED"])
def test_all_canonical_state_tamper_rejected_by_schema_runtime_and_public(state):
    observed = candidate().to_dict()
    observed["canonical_state"] = state
    observed["current_valid"] = state in {"PASS", "FAIL", "UNKNOWN"}
    observed["invalidation_epoch"] = 1 if state in {"STALE", "REVOKED"} else 0
    resign(observed)
    assert list(VALIDATOR.iter_errors(observed))
    with pytest.raises(ValueError):
        parse_audio_completion_admission_candidate(observed)
    with pytest.raises((TypeError, ValueError)):
        AudioCompletionAdmissionCandidate(observed).to_public_dict()


def test_append_chain_exact_scope_parent_revision_and_diagnostic_only_validator():
    first = candidate()
    second = candidate(previous=first, at="2026-08-21T01:00:01Z")
    assert second.to_dict()["revision"] == 2
    assert second.to_dict()["parent_receipt_sha256"] == first.to_dict()["receipt_sha256"]
    validate_audio_completion_transition(first.to_dict(), second.to_dict())

    changed = second.to_dict(); changed["revision"] = 3; resign(changed)
    with pytest.raises(ValueError):
        validate_audio_completion_transition(first.to_dict(), changed)
    with pytest.raises(ValueError):
        AudioCompletionAdmissionCandidate.create(
            receipt_id="audio-completion-1", scope=scope("f"),
            role_declarations=declarations((binding(AudioCompletionRole.SOURCE, "source-main"),)),
            evidence_bindings=(binding(AudioCompletionRole.SOURCE, "source-main"),),
            evaluated_at="2026-08-21T01:00:02Z", previous=first)

    with pytest.raises(ValueError, match="time must advance"):
        candidate(previous=candidate(at="2026-08-21T01:00:00.900Z"), at="2026-08-21T01:00:00Z")

    class FakePrevious:
        def to_dict(self):
            return first.to_dict()

    with pytest.raises(TypeError, match="exact AudioCompletionAdmissionCandidate"):
        candidate(previous=FakePrevious())

    forged_value = first.to_dict()
    forged_value["reason_codes"] = ["FORGED"]
    resign(forged_value)
    forged = AudioCompletionAdmissionCandidate(
        contract._freeze(forged_value), _token=contract._CANDIDATE_CONSTRUCTION_TOKEN
    )
    with pytest.raises(ValueError):
        candidate(previous=forged)


def test_private_and_public_digests_are_domain_separated_and_public_is_redacted():
    private = candidate().to_dict()
    public = candidate().to_public_dict()
    assert private["receipt_sha256"] != public["public_projection_sha256"]
    forbidden = ["project-1", "timeline-1", "TASK-014", "TASK-026", "TASK-035",
                 private["receipt_sha256"], private["evaluated_at"], "source-main"]
    rendered = json.dumps(public, sort_keys=True)
    assert all(value not in rendered for value in forbidden)
    assert set(public) == {"schema_version", "record_type", "candidate_state", "canonical_state",
        "reason_codes", "role_count", "required_role_count", "present_role_count",
        "item_count", "inputs_origin_authenticated", "source_records_semantically_revalidated",
        "canonical_admission_authorized", "public_projection_sha256"}
    assert public["inputs_origin_authenticated"] is False
    assert public["source_records_semantically_revalidated"] is False
    assert public["canonical_admission_authorized"] is False


def test_candidate_constructor_pickle_alias_and_public_forgery_are_sealed():
    value = candidate().to_dict()
    with pytest.raises(TypeError):
        AudioCompletionAdmissionCandidate(value)
    typed = candidate()
    with pytest.raises(TypeError):
        pickle.dumps(typed)
    alias = typed.to_dict()
    alias["reason_codes"].append("C:/private/audio.wav")
    assert "C:/private/audio.wav" not in json.dumps(typed.to_public_dict())
    forged_value = typed.to_dict()
    forged_value["reason_codes"] = ["C:/private/audio.wav"]
    resign(forged_value)
    forged = AudioCompletionAdmissionCandidate(
        contract._freeze(forged_value), _token=contract._CANDIDATE_CONSTRUCTION_TOKEN
    )
    with pytest.raises(ValueError):
        forged.to_public_dict()


@pytest.mark.parametrize("field,value", [
    ("source_truth_record_type", "SyntheticSourceTruth"),
    ("role_policy_owner", "TASK-026"),
    ("role_policy_record_type", "AudioPlacementPlan"),
    ("requirements_authority_verified", True),
    ("source_origin_authenticated", True),
])
def test_scope_typed_policy_and_unverified_authority_flags_are_closed(field, value):
    record = candidate().to_dict()
    record["scope_binding"][field] = value
    assert list(VALIDATOR.iter_errors(record))
    with pytest.raises(ValueError):
        parse_audio_completion_admission_candidate(record)


@pytest.mark.parametrize("field", ["scope_binding_sha256", "receipt_sha256"])
def test_digest_tamper_rejects(field):
    record = candidate().to_dict()
    record[field] = "sha256:" + "0" * 64
    with pytest.raises(ValueError):
        parse_audio_completion_admission_candidate(record)


def test_schema_rejects_authority_effect_and_state_invariant_tamper():
    record = candidate().to_dict()
    VALIDATOR.validate(record)
    for mutation in (
        ("authority_flags", "canonical_receipt_minted", True),
        ("effect_flags", "audio_written", True),
        (None, "inputs_origin_authenticated", True),
        (None, "source_records_semantically_revalidated", True),
        ("chain_diagnostic", "parent_link_checked_in_memory", True),
        ("chain_diagnostic", "latest_state_verified", True),
    ):
        changed = copy.deepcopy(record)
        if mutation[0] is None:
            changed[mutation[1]] = mutation[2]
        else:
            changed[mutation[0]][mutation[1]] = mutation[2]
        assert list(VALIDATOR.iter_errors(changed))
        with pytest.raises(ValueError):
            parse_audio_completion_admission_candidate(changed)
    changed = copy.deepcopy(record); changed["canonical_state"] = "PASS"
    assert list(VALIDATOR.iter_errors(changed))


def test_schema_mirror_draft_and_static_no_effect_surface():
    assert SCHEMA_PATH.read_bytes() == MIRROR_PATH.read_bytes()
    Draft202012Validator.check_schema(SCHEMA)
    source = (ROOT / "src" / "ai_video_production" / "audio_completion_receipt.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported & {"pathlib", "os", "subprocess", "socket", "requests", "urllib",
        "httpx", "torch", "soundfile", "ai_video_production.final_review_gate"}
    forbidden_calls = {"open", "exec", "eval", "compile", "__import__"}
    assert not {node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)} & forbidden_calls
    assert "AudioPlacementPlan" not in source
    assert "AudioPlacementCompilationRecord" in source
