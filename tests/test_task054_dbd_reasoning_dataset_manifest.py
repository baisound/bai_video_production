from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision, DatasetRowDisposition, DatasetSplit, DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest, MANIFEST_STATE, RightsDecision,
    MAX_MANIFEST_ENTRIES, admit_dbd_reasoning_dataset_rights_manifest,
)

SHA = "sha256:" + "a" * 64
HEX = "a" * 64
CAND = "CAND-R2D" + "0" * 23
MATCH = "MATCH-" + "0" * 26
MANIFEST = "MAN-" + "0" * 26


def _entry(**changes: object) -> DbDReasoningDatasetRightsEntry:
    values = dict(candidate_id=CAND, candidate_sha256=SHA, lineage_sha256=SHA,
        human_review_sha256=SHA, human_review_ref=f"human-review://sha256/{HEX}", match_id=MATCH,
        source_group_id="source-group-1", source_ref=f"media://sha256/{HEX}", split=DatasetSplit.TRAIN,
        patch_version="9.1.0", locale="ja-JP", rights_decision=RightsDecision.ADMITTED_FOR_TRAINING,
        rights_ref=f"rights://sha256/{HEX}", consent_decision=ConsentDecision.EXPLICIT_TRAINING,
        consent_ref=f"consent://sha256/{HEX}", provenance_ref=f"provenance://sha256/{HEX}",
        disposition=DatasetRowDisposition.ELIGIBLE_CANDIDATE, reason_codes=())
    values.update(changes)
    return DbDReasoningDatasetRightsEntry(**values)


def _manifest(*entries: DbDReasoningDatasetRightsEntry) -> DbDReasoningDatasetRightsManifest:
    return DbDReasoningDatasetRightsManifest(MANIFEST, 1, entries or (_entry(),))


def test_manifest_is_exact_body_free_and_never_adopts() -> None:
    manifest = _manifest()
    assert manifest.to_dict()["manifest_state"] == MANIFEST_STATE
    assert admit_dbd_reasoning_dataset_rights_manifest(manifest.to_dict()) == manifest
    assert not hasattr(manifest, "adopt") and not hasattr(manifest, "training_eligible")
    assert all(word not in json.dumps(manifest.to_dict()) for word in ("transcript", "commentary_text", "credential"))


@pytest.mark.parametrize(("rights", "consent", "disposition", "reasons"), [
    (RightsDecision.UNKNOWN, ConsentDecision.EXPLICIT_TRAINING, DatasetRowDisposition.NEEDS_REVIEW, ("RIGHTS_UNKNOWN",)),
    (RightsDecision.REVOKED, ConsentDecision.EXPLICIT_TRAINING, DatasetRowDisposition.REJECTED, ("RIGHTS_REVOKED",)),
    (RightsDecision.ADMITTED_FOR_TRAINING, ConsentDecision.UNKNOWN, DatasetRowDisposition.NEEDS_REVIEW, ("CONSENT_UNKNOWN",)),
    (RightsDecision.ADMITTED_FOR_TRAINING, ConsentDecision.REJECTED, DatasetRowDisposition.REJECTED, ("CONSENT_REJECTED",)),
])
def test_rights_and_consent_fail_closed(rights, consent, disposition, reasons) -> None:
    assert _entry(rights_decision=rights, consent_decision=consent, disposition=disposition, reason_codes=reasons)
    with pytest.raises(ValueError, match="disposition"):
        _entry(rights_decision=rights, consent_decision=consent)


def test_public_secret_like_refs_and_non_r2d_identity_are_rejected() -> None:
    for name, value in (("source_ref", "https://example.com/public-video"),
                        ("rights_ref", "rights://owner/John-Doe"),
                        ("consent_ref", "credential://provider/key")):
        with pytest.raises(ValueError, match="body-free"):
            _entry(**{name: value})
    with pytest.raises(ValueError, match="CAND-R2D"):
        _entry(candidate_id="CAND-" + "0" * 26)


def test_reason_codes_and_source_group_split_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="require reason"):
        _entry(rights_decision=RightsDecision.UNKNOWN, disposition=DatasetRowDisposition.NEEDS_REVIEW)
    with pytest.raises(ValueError, match="cannot carry"):
        _entry(reason_codes=("UNEXPECTED",))
    second = replace(_entry(), candidate_id="CAND-R2D" + "1" * 23, split=DatasetSplit.TEST)
    with pytest.raises(ValueError, match="leakage"):
        _manifest(_entry(), second)
    with pytest.raises(ValueError, match="sorted"):
        _manifest(second, replace(_entry(), source_group_id="other"))
    with pytest.raises(ValueError, match="manifest ceiling"):
        _manifest(*((_entry(),) * (MAX_MANIFEST_ENTRIES + 1)))


def test_admission_rejects_rehashed_version_field_and_semantic_forges() -> None:
    for kind in ("version", "field", "semantic"):
        body = json.loads(json.dumps(_manifest().to_dict()))
        if kind == "version": body["schema_version"] = "9.9.9"
        elif kind == "field": body["extra"] = True
        else: body["entries"][0].update(disposition="REJECTED", reason_codes=["FORGED"])
        from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
        payload = {k: v for k, v in body.items() if k != "rights_manifest_sha256"}
        body["rights_manifest_sha256"] = sha256_bytes(canonical_json_bytes(payload))
        with pytest.raises((ValueError, TypeError)):
            admit_dbd_reasoning_dataset_rights_manifest(body)


def test_schema_mirror_and_runtime_output_conform() -> None:
    root = Path(__file__).parents[1]
    canonical = root / "schemas/dbd-reasoning-dataset-rights-manifest.schema.json"
    mirror = root / "src/ai_video_production/schema_resources/dbd-reasoning-dataset-rights-manifest.schema.json"
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(_manifest().to_dict())) == []
    wrong = _manifest().to_dict()
    wrong["entries"][0]["source_ref"] = f"rights://sha256/{HEX}"
    assert list(Draft202012Validator(schema).iter_errors(wrong))
