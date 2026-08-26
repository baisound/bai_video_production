from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any, Mapping, Protocol

from .ai_connections import (
    AiConnectionProfile, AiWorkload, ConnectionAvailability, CostClass,
    ModelRoute, ProviderFamily,
)
from .dbd_reasoning_contracts import (
    AuthorizationDecision, ContextFreshness, DbDReasoningContextEnvelope,
    DbDReasoningExecutionReceipt, HumanReviewResult, ReasoningDisposition,
    ReasoningSessionMode, TunedModelBindingStatus, admit_reasoning_contract_record,
)
from .dbd_reasoning_routing import (
    DbDReasoningRouteCapabilityResolver, DbDReasoningRouteDecision,
    ROUTE_CAPABILITY,
)
from .dbd_reasoning_validation import DbDReasoningProposalParser, StructuralParseResult
from .dbd_tuned_model_registry import DbDTunedModelRegistry
from .errors import ProductError, ProductErrorCategory
from .provider_execution import (
    AiProviderExecutionService, TextGenerationRequest, TextGenerationResult,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


AUTHORIZATION_SCHEMA_VERSION = "1.0.0"
AUTHORIZATION_RECORD_KIND = "DBD_REASONING_EXECUTION_AUTHORIZATION"
AUTHORIZATION_STATE = "ALLOWED_SINGLE_LOCAL_PREVIEW"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_AUTHORIZATION_FIELDS = frozenset({
    "schema_version", "record_kind", "authorization_id",
    "authority_evidence_sha256", "route_decision_sha256", "binding_id",
    "binding_revision", "binding_sha256", "session_mode", "not_before",
    "expires_at", "max_attempts", "cost_ceiling_milli", "max_output_tokens",
    "authorization_state", "authorization_sha256",
})


def _utc(value: str, *, name: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value,
    ):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class DbDReasoningExecutionAuthorization:
    authorization_id: str
    authority_evidence_sha256: str
    route_decision_sha256: str
    binding_id: str
    binding_revision: int
    binding_sha256: str
    not_before: str
    expires_at: str
    max_output_tokens: int
    session_mode: ReasoningSessionMode = ReasoningSessionMode.PREVIEW_NO_LEARNING
    max_attempts: int = 1
    cost_ceiling_milli: int = 0
    authorization_state: str = AUTHORIZATION_STATE

    def __post_init__(self) -> None:
        for name in ("authorization_id", "binding_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        for name in (
            "authority_evidence_sha256", "route_decision_sha256", "binding_sha256",
        ):
            validate_sha256(getattr(self, name), field_name=name)
        if (
            isinstance(self.binding_revision, bool)
            or not isinstance(self.binding_revision, int)
            or self.binding_revision < 1
        ):
            raise ValueError("binding_revision must be positive")
        if self.session_mode is not ReasoningSessionMode.PREVIEW_NO_LEARNING:
            raise ValueError("R3D local pilot authorizes preview without learning only")
        if self.max_attempts != 1 or self.cost_ceiling_milli != 0:
            raise ValueError("R3D local pilot requires one zero-cost attempt")
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or not 1 <= self.max_output_tokens <= 4096
        ):
            raise ValueError("max_output_tokens must be 1-4096")
        if self.authorization_state != AUTHORIZATION_STATE:
            raise ValueError("authorization_state is invalid")
        if _utc(self.not_before, name="not_before") >= _utc(self.expires_at, name="expires_at"):
            raise ValueError("authorization validity interval is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "schema_version": AUTHORIZATION_SCHEMA_VERSION,
            "record_kind": AUTHORIZATION_RECORD_KIND,
            "authorization_id": self.authorization_id,
            "authority_evidence_sha256": self.authority_evidence_sha256,
            "route_decision_sha256": self.route_decision_sha256,
            "binding_id": self.binding_id,
            "binding_revision": self.binding_revision,
            "binding_sha256": self.binding_sha256,
            "session_mode": self.session_mode.value,
            "not_before": self.not_before,
            "expires_at": self.expires_at,
            "max_attempts": self.max_attempts,
            "cost_ceiling_milli": self.cost_ceiling_milli,
            "max_output_tokens": self.max_output_tokens,
            "authorization_state": self.authorization_state,
        }

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        return {**body, "authorization_sha256": sha256_bytes(canonical_json_bytes(body))}

    def validate_for(self, decision: DbDReasoningRouteDecision, *, now: str) -> None:
        admitted = admit_dbd_reasoning_execution_authorization(self.to_dict())
        decision_document = decision.to_dict()
        expected = (
            decision_document["route_decision_sha256"], decision.binding_id,
            decision.binding_revision, decision.binding_sha256,
        )
        actual = (
            admitted.route_decision_sha256, admitted.binding_id,
            admitted.binding_revision, admitted.binding_sha256,
        )
        if actual != expected:
            raise ProductError(
                "ERR_DBD_R3D_AUTHORIZATION_CROSSED",
                "Execution authorization does not match the current route decision",
                ProductErrorCategory.AUTHORIZATION,
            )
        observed = _utc(now, name="now")
        if not _utc(admitted.not_before, name="not_before") <= observed < _utc(admitted.expires_at, name="expires_at"):
            raise ProductError(
                "ERR_DBD_R3D_AUTHORIZATION_INACTIVE",
                "Execution authorization is not active",
                ProductErrorCategory.AUTHORIZATION,
            )


def admit_dbd_reasoning_execution_authorization(
    record: Mapping[str, Any],
) -> DbDReasoningExecutionAuthorization:
    if not isinstance(record, Mapping) or set(record) != _AUTHORIZATION_FIELDS:
        raise ValueError("execution authorization has unknown or missing fields")
    if record["schema_version"] != AUTHORIZATION_SCHEMA_VERSION or record["record_kind"] != AUTHORIZATION_RECORD_KIND:
        raise ValueError("execution authorization type is unsupported")
    from importlib.resources import files
    from jsonschema import Draft202012Validator

    schema = json.loads(
        files("ai_video_production.schema_resources")
        .joinpath("dbd-reasoning-execution-authorization.schema.json")
        .read_text(encoding="utf-8")
    )
    if list(Draft202012Validator(schema).iter_errors(dict(record))):
        raise ValueError("execution authorization does not satisfy JSON Schema")
    body = {key: record[key] for key in record if key != "authorization_sha256"}
    if record["authorization_sha256"] != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("execution authorization checksum mismatch")
    try:
        value = DbDReasoningExecutionAuthorization(
            authorization_id=record["authorization_id"],
            authority_evidence_sha256=record["authority_evidence_sha256"],
            route_decision_sha256=record["route_decision_sha256"],
            binding_id=record["binding_id"], binding_revision=record["binding_revision"],
            binding_sha256=record["binding_sha256"],
            session_mode=ReasoningSessionMode(record["session_mode"]),
            not_before=record["not_before"], expires_at=record["expires_at"],
            max_attempts=record["max_attempts"],
            cost_ceiling_milli=record["cost_ceiling_milli"],
            max_output_tokens=record["max_output_tokens"],
            authorization_state=record["authorization_state"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("execution authorization is not canonical") from exc
    if value.to_dict() != dict(record):
        raise ValueError("execution authorization is not exact canonical form")
    return value


@dataclass(frozen=True, slots=True)
class LocalDbDGeneration:
    text: str
    base_model_sha256: str
    adapter_sha256: str
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text or "\x00" in self.text:
            raise ValueError("local runtime text is invalid")
        for name in ("base_model_sha256", "adapter_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")


class LocalDbDTextRuntime(Protocol):
    def generate(self, model_id: str, request: TextGenerationRequest) -> LocalDbDGeneration: ...

class ExecutionAuthorityVerifier(Protocol):
    def verify(self, authority_evidence_sha256: str) -> bool: ...


class ExecutionAuthorizationUseStore(Protocol):
    def claim_once(self, authorization_sha256: str) -> bool: ...



class LocalDbDReasoningTextAdapter:
    family = ProviderFamily.LOCAL_OPEN_SOURCE

    def __init__(self, runtime: LocalDbDTextRuntime) -> None:
        if runtime is None or not callable(getattr(runtime, "generate", None)):
            raise ValueError("runtime must implement LocalDbDTextRuntime")
        self.runtime = runtime

    def generate(
        self, route: ModelRoute, request: TextGenerationRequest, credential: str | None,
    ) -> TextGenerationResult:
        if (
            route.workload is not AiWorkload.PLANNING
            or route.provider_family is not self.family
            or route.provider_id != "local-runtime"
            or route.cost_class is not CostClass.LOCAL_FREE_AI
            or ROUTE_CAPABILITY not in route.capabilities
            or route.credential_ref is not None
            or route.endpoint_ref is not None
            or credential is not None
        ):
            raise ProductError(
                "ERR_DBD_R3D_LOCAL_ROUTE_INELIGIBLE",
                "Selected route is not eligible for local DbD execution",
                ProductErrorCategory.AUTHORIZATION,
            )
        base_sha = route.settings.get("dbd_base_model_sha256")
        adapter_sha = route.settings.get("dbd_adapter_sha256")
        validate_sha256(base_sha, field_name="dbd_base_model_sha256")
        validate_sha256(adapter_sha, field_name="dbd_adapter_sha256")
        generated = self.runtime.generate(route.model_id, request)
        if (generated.base_model_sha256, generated.adapter_sha256) != (base_sha, adapter_sha):
            raise ProductError(
                "ERR_DBD_R3D_ARTIFACT_ATTESTATION_MISMATCH",
                "Local runtime loaded different model artifacts",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return TextGenerationResult(
            route.route_id, route.provider_id, route.model_id, generated.text,
            input_tokens=generated.input_tokens, output_tokens=generated.output_tokens,
        )


@dataclass(frozen=True, slots=True)
class DbDPreviewStateSnapshot:
    dataset_sha256: str
    dataset_revision: int
    training_job_count: int

    def __post_init__(self) -> None:
        validate_sha256(self.dataset_sha256, field_name="dataset_sha256")
        for name in ("dataset_revision", "training_job_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class DbDReasoningExecutionResult:
    receipt: DbDReasoningExecutionReceipt
    parser_result: StructuralParseResult


class DbDReasoningExecutionService:
    def __init__(
        self, provider: AiProviderExecutionService,
        authority_verifier: ExecutionAuthorityVerifier,
        authorization_uses: ExecutionAuthorizationUseStore,
        parser: DbDReasoningProposalParser | None = None,
    ) -> None:
        if not isinstance(provider, AiProviderExecutionService):
            raise ValueError("provider must be AiProviderExecutionService")
        if authority_verifier is None or not callable(getattr(authority_verifier, "verify", None)):
            raise ValueError("authority_verifier must implement ExecutionAuthorityVerifier")
        if authorization_uses is None or not callable(getattr(authorization_uses, "claim_once", None)):
            raise ValueError("authorization_uses must implement ExecutionAuthorizationUseStore")
        self.provider = provider
        self.parser = parser or DbDReasoningProposalParser()
        self.authorization_uses = authorization_uses
        self.authority_verifier = authority_verifier
        if type(self.parser) is not DbDReasoningProposalParser:
            raise ValueError("parser must be the canonical strict parser")

    def execute_local_preview(
        self,
        *,
        attempt_id: str,
        authorization: DbDReasoningExecutionAuthorization,
        decision: DbDReasoningRouteDecision,
        registry: DbDTunedModelRegistry,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        locale: str,
        context: DbDReasoningContextEnvelope,
        prompt: str,
        prompt_template_sha256: str,
        output_schema_sha256: str,
        state_before: DbDPreviewStateSnapshot,
        state_after: DbDPreviewStateSnapshot,
        now: str,
        started_at: str,
        ended_at: str,
    ) -> DbDReasoningExecutionResult:
        if not isinstance(attempt_id, str) or not _SAFE_ID.fullmatch(attempt_id):
            raise ValueError("attempt_id is invalid")
        for name, value in (
            ("prompt_template_sha256", prompt_template_sha256),
            ("output_schema_sha256", output_schema_sha256),
        ):
            validate_sha256(value, field_name=name)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > 128 * 1024 or "\x00" in prompt:
            raise ValueError("prompt is invalid")
        admit_reasoning_contract_record(context.to_dict())
        current = DbDReasoningRouteCapabilityResolver.validate_current(
            decision, registry, profile, availability, locale=locale,
            binding_id=decision.binding_id,
        )
        authorization.validate_for(current, now=now)
        resolution = registry.resolve(locale=locale, binding_id=current.binding_id)
        if not self.authority_verifier.verify(authorization.authority_evidence_sha256):
            raise ProductError(
                "ERR_DBD_R3D_AUTHORITY_EVIDENCE_UNTRUSTED",
                "Execution authority Evidence is not trusted",
                ProductErrorCategory.AUTHORIZATION,
            )

        binding = resolution.binding
        if binding.status is not TunedModelBindingStatus.APPROVED:
            raise ProductError(
                "ERR_DBD_R3D_BINDING_NOT_APPROVED", "Binding is not approved",
                ProductErrorCategory.AUTHORIZATION,
            )
        route = next((item for item in profile.routes if item.route_id == current.route_id), None)
        if route is None or (
            route.settings.get("dbd_base_model_sha256"),
            route.settings.get("dbd_adapter_sha256"),
        ) != (binding.base_model_sha256, binding.adapter_sha256):
            raise ProductError(
                "ERR_DBD_R3D_ROUTE_ARTIFACT_PIN_MISMATCH",
                "Route artifact pins do not match the approved binding",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        temperature = route.settings.get("temperature")
        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2
        ):
            raise ProductError(
                "ERR_DBD_R3D_ROUTE_TEMPERATURE_INVALID",
                "Route temperature is not canonical",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        authorization_sha256 = authorization.to_dict()["authorization_sha256"]
        if not self.authorization_uses.claim_once(authorization_sha256):
            raise ProductError(
                "ERR_DBD_R3D_AUTHORIZATION_ALREADY_USED",
                "Execution authorization has already been consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        request = TextGenerationRequest(
            prompt=prompt, max_output_tokens=authorization.max_output_tokens,
            temperature=temperature, timeout_seconds=120,
        )
        generated = self.provider.generate_planning_text_for_capabilities(
            profile, availability, request, required_capabilities=(ROUTE_CAPABILITY,),
        )
        if (generated.route_id, generated.provider_id, generated.model_id) != (
            current.route_id, current.provider_id, current.model_id,
        ):
            raise ProductError(
                "ERR_DBD_R3D_PROVIDER_RESULT_CROSSED",
                "Provider result coordinates do not match the current route",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        raw_output = generated.text.encode("utf-8", errors="strict")
        if (
            generated.output_tokens is not None
            and generated.output_tokens > authorization.max_output_tokens
        ):
            raise ProductError(
                "ERR_DBD_R3D_OUTPUT_TOKEN_LIMIT_EXCEEDED",
                "Local runtime exceeded the authorized output-token ceiling",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        parsed = self.parser.parse(raw_output)
        if state_before != state_after:
            raise ProductError(
                "ERR_DBD_R3D_PREVIEW_STATE_CHANGED",
                "Preview execution changed Dataset or training state",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        start = _utc(started_at, name="started_at")
        end = _utc(ended_at, name="ended_at")
        elapsed_ms = int((end - start).total_seconds() * 1000)
        if elapsed_ms < 0:
            raise ValueError("execution timestamps are reversed")
        binding_document = binding.to_dict()
        receipt = DbDReasoningExecutionReceipt(
            receipt_id=f"receipt-{attempt_id}", attempt_id=attempt_id,
            session_mode=ReasoningSessionMode.PREVIEW_NO_LEARNING,
            context_sha256=context.to_dict()["context_sha256"],
            binding_revision=binding.revision, binding_status=binding.status,
            binding_sha256=binding_document["binding_sha256"],
            prompt_sha256=sha256_bytes(prompt.encode("utf-8")),
            output_sha256=parsed.raw_output_sha256,
            prompt_template_sha256=prompt_template_sha256,
            output_schema_sha256=output_schema_sha256,
            route_ref=f"route://{current.route_id}",
            provider_ref=f"provider://{current.provider_id}",
            base_model_ref=binding.base_model_ref, adapter_ref=binding.adapter_ref,
            authorization_ref=f"authorization://task054/{authorization.authorization_id}",
            authorization_decision=AuthorizationDecision.ALLOWED,
            cost_milli=0, cost_ceiling_milli=authorization.cost_ceiling_milli,
            started_at=started_at, ended_at=ended_at, elapsed_ms=elapsed_ms,
            input_tokens=generated.input_tokens or 0,
            output_tokens=generated.output_tokens or 0,
            parser_passed=parsed.structurally_valid,
            fact_validation_passed=False, policy_validation_passed=False,
            stale_result=ContextFreshness.CURRENT,
            human_review_result=(
                HumanReviewResult.PENDING if parsed.structurally_valid
                else HumanReviewResult.NOT_REQUIRED
            ),
            final_disposition=(
                ReasoningDisposition.REVIEW_REQUIRED if parsed.structurally_valid
                else ReasoningDisposition.ABSTAIN
            ),
            fallback_reason_code=None, retry_reason_code=None, retry_count=0,
            dataset_before_sha256=state_before.dataset_sha256,
            dataset_after_sha256=state_after.dataset_sha256,
            dataset_before_revision=state_before.dataset_revision,
            dataset_after_revision=state_after.dataset_revision,
            binding_before_revision=binding.revision,
            binding_after_revision=binding.revision,
            binding_before_status=binding.status, binding_after_status=binding.status,
            binding_before_sha256=binding_document["binding_sha256"],
            binding_after_sha256=binding_document["binding_sha256"],
            training_job_count_before=state_before.training_job_count,
            training_job_count_after=state_after.training_job_count,
        )
        admit_reasoning_contract_record(receipt.to_dict())
        return DbDReasoningExecutionResult(receipt, parsed)


__all__ = [
    "AUTHORIZATION_RECORD_KIND", "AUTHORIZATION_SCHEMA_VERSION",
    "AUTHORIZATION_STATE", "DbDPreviewStateSnapshot",
    "DbDReasoningExecutionAuthorization", "DbDReasoningExecutionResult",
    "DbDReasoningExecutionService", "LocalDbDGeneration",
    "ExecutionAuthorityVerifier",
    "ExecutionAuthorizationUseStore", "LocalDbDReasoningTextAdapter",
    "LocalDbDTextRuntime",
    "admit_dbd_reasoning_execution_authorization",
]
