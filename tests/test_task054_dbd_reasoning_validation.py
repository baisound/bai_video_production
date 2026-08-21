"""Focused TASK-054 R2A strict raw-output parser tests."""

from __future__ import annotations

from dataclasses import replace
import json
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.dbd_reasoning_contracts import DbDReasoningProposal
from ai_video_production.dbd_reasoning_validation import (
    DbDReasoningProposalParser,
    MAX_RAW_OUTPUT_BYTES,
    PARSER_VERSION,
    StructuralParseResult,
    StructuralReasoningFact,
    StructuralReasoningProposal,
    StructuralStyleMetrics,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "dbd-reasoning-raw-output.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "dbd-reasoning-raw-output.schema.json"


def _payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "disposition": "PROPOSE",
        "observed_claims": [{"kind": "EVENT_OCCURRED", "key": "event.type", "value": "HOOK"}],
        "canonical_claims": [],
        "inferred_states": [],
        "tactical_interpretations": [],
        "commentary_outline": ["フックを確認"],
        "commentary_text": "フックに入りました。",
        "citations": [],
        "uncertainty_codes": [],
        "style_metrics": {"density_milli": 500, "emotion_milli": 400, "tempo_milli": 600},
    }


def _raw(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def test_valid_output_is_deterministic_quarantined_and_not_canonical() -> None:
    raw = _raw(_payload())
    first = DbDReasoningProposalParser().parse(raw)
    second = DbDReasoningProposalParser().parse(raw)
    assert first == second
    assert first.structurally_valid is True
    assert first.error_codes == ()
    assert first.parser_version == PARSER_VERSION
    assert first.quarantined_proposal is not None
    assert first.quarantined_proposal.state == "STRUCTURAL_ONLY_NOT_ADMITTED"
    assert first.quarantined_proposal.structural_body_sha256.startswith("sha256:")
    assert not isinstance(first.quarantined_proposal, DbDReasoningProposal)
    assert not hasattr(first.quarantined_proposal, "to_dict")
    assert "フック" not in repr(first.quarantined_proposal)
    assert first.raw_output_sha256 == "sha256:" + sha256(raw).hexdigest()


def test_raw_output_schema_and_resource_mirror_are_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(_payload()))
    extra = _payload()
    extra["proposal_sha256"] = "sha256:" + "a" * 64
    assert list(Draft202012Validator(schema).iter_errors(extra))
    empty_proposal = _payload()
    empty_proposal["commentary_text"] = ""
    assert list(Draft202012Validator(schema).iter_errors(empty_proposal))
    duplicate_citation = _payload()
    duplicate_citation["citations"] = ["evidence://event/1", "evidence://event/1"]
    assert list(Draft202012Validator(schema).iter_errors(duplicate_citation))
    for unsafe_ref in ("https://user@example.com/ref", "https://example.com/ref?x=1", "https://example.com/ref#part"):
        unsafe_citation = _payload()
        unsafe_citation["citations"] = [unsafe_ref]
        assert list(Draft202012Validator(schema).iter_errors(unsafe_citation))


def test_safe_canonical_references_and_japanese_explanation_are_accepted() -> None:
    payload = _payload()
    payload["commentary_text"] = "プロバイダーという言葉を通常の解説として説明します。オン/オフと段階1/2を比較します。"
    payload["citations"] = [
        "evidence://event/1",
        "https://example.com/reference",
        "knowledge://dbd/perk",
        "manual://operator/guide",
        "rag://chunk/1",
        "trivia://entry/1",
    ]
    payload["inferred_states"] = [{
        "statement": "次の行動は変化する可能性があります。",
        "qualifier": "POSSIBLE",
        "confidence_milli": 500,
        "supporting_refs": ["evidence://event/1"],
    }]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


def test_runtime_admission_always_conforms_to_the_raw_output_schema() -> None:
    payload = _payload()
    payload["citations"] = ["evidence://event/1", "https://example.com/reference"]
    raw = _raw(payload)
    result = DbDReasoningProposalParser().parse(raw)
    assert result.structurally_valid is True
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(json.loads(raw)))


@pytest.mark.parametrize(("raw", "code"), [
    (b"", "RAW_OUTPUT_SIZE_INVALID"),
    (b"\xef\xbb\xbf{}", "RAW_OUTPUT_BOM_FORBIDDEN"),
    (b"\xff", "RAW_OUTPUT_UTF8_INVALID"),
    (b'{"schema_version":"1.0.0","schema_version":"1.0.0"}', "JSON_DUPLICATE_KEY"),
    (b'{"x":NaN}', "JSON_SYNTAX_INVALID"),
    (b'{"x":Infinity}', "JSON_SYNTAX_INVALID"),
    (b"```json\n{}\n```", "JSON_SYNTAX_INVALID"),
    (b"{} trailing prose", "JSON_SYNTAX_INVALID"),
    (b"[]", "JSON_ROOT_OBJECT_REQUIRED"),
])
def test_malformed_raw_output_fails_closed(raw: bytes, code: str) -> None:
    result = DbDReasoningProposalParser().parse(raw)
    assert result.structurally_valid is False
    assert result.quarantined_proposal is None
    assert result.error_codes == (code,)


def test_oversized_and_deep_json_fail_closed_without_body_retention() -> None:
    oversized = b"{" + b" " * MAX_RAW_OUTPUT_BYTES + b"}"
    oversized_result = DbDReasoningProposalParser().parse(oversized)
    assert oversized_result.error_codes == ("RAW_OUTPUT_SIZE_INVALID",)
    another_oversized_result = DbDReasoningProposalParser().parse(b"[" + b"0," * MAX_RAW_OUTPUT_BYTES + b"]")
    assert oversized_result.raw_output_sha256 == another_oversized_result.raw_output_sha256
    assert oversized_result.raw_output_sha256 != "sha256:" + sha256(oversized).hexdigest()
    deeply_nested = b'{"x":' + b"[" * 10_000 + b"0" + b"]" * 10_000 + b"}"
    result = DbDReasoningProposalParser().parse(deeply_nested)
    assert result.error_codes == ("JSON_DEPTH_EXCEEDED",)
    assert not hasattr(result, "raw_output")


@pytest.mark.parametrize("field", ["provider_ref", "route_ref", "model_ref", "tool_calls", "hidden_chain_of_thought"])
def test_extra_hidden_execution_fields_and_fabricated_checksum_are_rejected(field: str) -> None:
    payload = _payload()
    payload[field] = "x"
    result = DbDReasoningProposalParser().parse(_raw(payload))
    assert result.error_codes == ("PROPOSAL_SHAPE_INVALID",)


@pytest.mark.parametrize("value", [
    "api_key=do-not-store",
    "credential://owner",
    r"C:\\models\\raw",
    "/home/user/private",
    "/opt/model",
    "/root/.ssh",
    "/mnt/c/raw",
    "/srv/private",
    "/usr/local/bin",
    "/arbitrary/path",
    "//server/share",
    r"\\server\share",
    r"D:\\recordings\\match",
    "D:/recordings/match",
    "Bearer abcdef",
    "Basic YWJjZGVm",
    "sk-proj-abcdef",
    "sk-live-abcdef",
    "ghp_abcdef",
    "github_pat_abcdef",
    "-----BEGIN PRIVATE KEY-----",
    "https://user:pass@example.com/path",
    "https://example.com/path?api_key=value",
    "https://example.com/path#section",
])
def test_secret_like_and_raw_path_semantics_are_quarantined_for_r2c(value: str) -> None:
    payload = _payload()
    payload["commentary_text"] = value
    result = DbDReasoningProposalParser().parse(_raw(payload))
    assert result.structurally_valid is True


@pytest.mark.parametrize("value", [
    "<think>hidden</think>",
    "<analysis>hidden</analysis>",
    "chain of thought",
    "reasoning_trace",
    "reasoning content",
    "tool_use",
    "tool_calls",
    "function-call",
    "provider_ref",
    "model ref",
    "credential-ref",
    "route_id",
    "auth-ref",
    "TOKEN_ID",
    "secret ref",
])
def test_hidden_execution_or_chain_of_thought_semantics_are_quarantined_for_r2c(value: str) -> None:
    payload = _payload()
    payload["commentary_text"] = value
    result = DbDReasoningProposalParser().parse(_raw(payload))
    assert result.structurally_valid is True


@pytest.mark.parametrize("value", [
    "<metadata id=\"x\">",
    "<解析>内部</解析>",
    "ｐｒｏｖｉｄｅｒ＿ｒｅｆ",
    "ｔｏｏｌ－ｃａｌｌ",
    "認証情報: AbcDefGhiJklMnoPqrStuVwxYz01234",
    "token=AbcDefGhiJklMnoPqrStuVwxYz01234",
    "/ユーザー/動画",
    "／tmp/recording",
    "C:\\recordings\\match",
    "\\\\server\\share",
])
def test_free_text_semantics_are_quarantined_for_r2c(value: str) -> None:
    payload = _payload()
    payload["commentary_text"] = value
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


@pytest.mark.parametrize("value", ["制御\x00文字", "不可視\u200b文字", "stable\u200btoken"])
def test_control_format_and_surrogate_categories_fail_closed_in_all_roles(value: str) -> None:
    payload = _payload()
    payload["commentary_text"] = value
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("OUTPUT_STRING_INVALID",)
    payload = _payload()
    payload["uncertainty_codes"] = [value]
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("OUTPUT_STRING_INVALID",)


@pytest.mark.parametrize("reference", [
    "https://example.com/ref?token=x",
    "https://user@example.com/ref",
    "https://example.com/ref#part",
    "rag://chunk\\one",
    "missing-scheme",
    "custom://",
    "ｅｖｉｄｅｎｃｅ://event/1",
])
def test_reference_role_requires_exact_safe_reference_grammar(reference: str) -> None:
    payload = _payload()
    payload["citations"] = [reference]
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("OUTPUT_STRING_INVALID",)


@pytest.mark.parametrize("reference", [
    "provider://internal/route",
    "credential://synthetic/value",
    "evidence://event//1",
    "evidence://event/./1",
    "evidence://event/../1",
    "evidence://event/%2f",
    "HTTPS://example.com/ref",
])
def test_reference_semantics_are_deferred_to_r2c(reference: str) -> None:
    payload = _payload()
    payload["citations"] = [reference]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


@pytest.mark.parametrize("value", [
    "route.id", "route/id", "tool.invocation", "chain.of.thought", "path=/tmp/recording", "path=//server/share", "path=C:/recording",
    "AKIA" + "ABCDEFGHIJKLMNOP", "AIza" + "abcdefghijklmnopqrstuvwxyz123456",
    "xoxb" + "-1234567890-abcdefghijklmnop", "npm" + "_abcdefghijklmnop",
    "pypi" + "-abcdefghijklmnop",
    "eyJhbGciOiJIUzI1NiJ9" + ".eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturevalue",
    "AbcDefGhiJklMnoPqrStuVwxYz" + "01234",
])
def test_execution_paths_and_provider_secret_semantics_are_quarantined_for_r2c(value: str) -> None:
    payload = _payload()
    payload["observed_claims"][0]["key"] = value  # type: ignore[index]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


def test_canonical_refs_ids_and_japanese_slash_prose_remain_admitted() -> None:
    payload = _payload()
    payload["commentary_text"] = "オン/オフを切り替え、通常の解説を続けます。"
    payload["observed_claims"][0]["key"] = "event.type"  # type: ignore[index]
    payload["citations"] = ["evidence://event/sha256-abc123", "https://example.com/reference", "knowledge://dbd/perk", "manual://operator/guide", "rag://chunk/42", "trivia://entry/1"]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


@pytest.mark.parametrize("reference", [
    "evidence://route/id",
    "evidence://model/ref",
    "knowledge://provider/id",
])
def test_reference_execution_metadata_is_quarantined_for_r2c(reference: str) -> None:
    payload = _payload()
    payload["citations"] = [reference]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


@pytest.mark.parametrize("value", [
    "GEVT-00000000000000000000000000",
    "GEVD-00000000000000000000000000",
    "TRIV-00000000000000000000000000",
    "trivia.TRIV-00000000000000000000000000",
    "123e4567-e89b-12d3-a456-426614174000",
])
def test_canonical_product_ids_uuid_and_trivia_fact_key_are_not_secret_false_positives(value: str) -> None:
    payload = _payload()
    payload["observed_claims"][0]["key"] = value  # type: ignore[index]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


def test_safe_https_in_free_text_is_not_misclassified_as_unc_path() -> None:
    payload = _payload()
    payload["commentary_text"] = "詳細は https://example.com/reference を参照してください。"
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is True


def test_unpaired_surrogate_is_rejected_without_digest_serialization_failure() -> None:
    payload = _payload()
    payload["commentary_text"] = chr(0xD800)
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    result = DbDReasoningProposalParser().parse(raw)
    assert result.error_codes == ("OUTPUT_STRING_INVALID",)


def test_abstain_cannot_carry_speakable_content_or_coercions() -> None:
    payload = _payload()
    payload.update({
        "disposition": "ABSTAIN",
        "observed_claims": [],
        "commentary_outline": [],
        "commentary_text": "still speaking",
    })
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("PROPOSAL_VALUE_INVALID",)
    payload = _payload()
    payload["style_metrics"] = {"density_milli": "500", "emotion_milli": 1, "tempo_milli": 1}
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("PROPOSAL_VALUE_INVALID",)


def test_missing_or_extra_nested_fields_are_rejected_without_defaults() -> None:
    payload = _payload()
    payload.pop("citations")
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("PROPOSAL_SHAPE_INVALID",)
    payload = _payload()
    payload["style_metrics"] = {"density_milli": 1, "emotion_milli": 1, "tempo_milli": 1, "provider": "x"}
    assert DbDReasoningProposalParser().parse(_raw(payload)).error_codes == ("STYLE_METRICS_SHAPE_INVALID",)


def test_parser_has_no_io_store_provider_or_canonical_proposal_construction() -> None:
    source = (ROOT / "src" / "ai_video_production" / "dbd_reasoning_validation.py").read_text(encoding="utf-8")
    assert "DbDReasoningProposal(" not in source
    assert "CommentaryCandidate" not in source
    assert "CandidateStore" not in source
    assert "open(" not in source
    imports = "\n".join(line for line in source.splitlines() if line.startswith(("from ", "import ")))
    assert "provider" not in imports.casefold()
    assert "sqlite" not in imports.casefold()


def test_reference_runtime_bound_matches_schema_for_citations_and_supports() -> None:
    oversized_ref = "custom://" + "a" * 513
    payload = _payload()
    payload["citations"] = [oversized_ref]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is False
    payload = _payload()
    payload["inferred_states"] = [{
        "statement": "synthetic",
        "qualifier": "POSSIBLE",
        "confidence_milli": 1,
        "supporting_refs": [oversized_ref],
    }]
    assert DbDReasoningProposalParser().parse(_raw(payload)).structurally_valid is False


def test_exported_quarantine_contract_cannot_be_forged() -> None:
    result = DbDReasoningProposalParser().parse(_raw(_payload()))
    quarantine = result.quarantined_proposal
    assert quarantine is not None
    for mutation in (
        {"state": "ADMITTED"},
        {"schema_version": "999.0.0"},
        {"disposition": "CONFIRMED"},
        {"structural_body_sha256": "sha256:" + "0" * 64},
        {"style_metrics": StructuralStyleMetrics(0, 0, 0)},
    ):
        with pytest.raises(ValueError):
            replace(quarantine, **mutation)
    with pytest.raises(ValueError):
        StructuralStyleMetrics(-1, 0, 0)
    with pytest.raises(ValueError):
        StructuralReasoningFact("BAD_KIND", "key", "value")
    with pytest.raises(ValueError):
        StructuralParseResult(True, replace(quarantine, structural_body_sha256="sha256:" + "0" * 64), result.raw_output_sha256, PARSER_VERSION, ())
