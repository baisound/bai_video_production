from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path
import shutil
import uuid
from typing import Any

from .assets import AssetType, AudioRightsStatus, PermissionState, RightsStatus
from .comfyui import (
    ComfyResourcePolicy,
    ComfyUIClient,
    _admit_comfy_input_staging_disk,
    _history_entry,
    _image_descriptors,
    _load_workflow_json,
    _prepare_owned_comfy_subdir,
    _queue_or_resume_comfy_prompt,
    _mark_comfy_failure,
    _request_bound_command,
    _validate_license_authorization_ref,
    admit_comfy_resources,
    assert_workflow_inputs_available,
    assert_workflow_supported,
    render_workflow_placeholders,
    resolve_comfy_output,
    workflow_class_types,
)
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec, sha256_file
from .errors import ProductError, ProductErrorCategory
from .h3_single_frame import H3SingleFrameContract
from .media_probe import FFprobeMediaProbe
from .paths import LogicalPathResolver, SourcePathPolicy
from .serialization import canonical_json_bytes, sha256_bytes
from .store import OperationRecord, SQLiteProductStore
from .task004_manifest import Task004ManifestWriter


_RESERVED = {
    "PROMPT",
    "SEED",
    "FRAME_COUNT",
    "SELECT_FRAME",
    "ROPE_STRENGTH",
    "REFERENCE_1",
    "REFERENCE_2",
}


@dataclass(frozen=True, slots=True)
class H3SingleFrameRequest:
    production_job_id: str
    idempotency_key: str
    workflow_path: Path
    substitutions: dict[str, Any]
    prompt: str
    seed: int
    contract: H3SingleFrameContract
    reference_asset_ids: tuple[str, ...]
    authorize_execution: bool
    license_authorization_ref: str | None = None
    external_node_authorization_ref: str | None = None
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 1800


@dataclass(frozen=True, slots=True)
class H3SingleFrameResult:
    operation: OperationRecord
    asset_id: str
    manifest_uri: str
    evidence_uri: str
    prompt_id: str


class H3SingleFrameService:
    """Optional MiniMax H3 still-image transform provider through ComfyUI.

    The external custom node remains an independently installed runtime plugin.
    Product Core owns only the workflow contract, canonical reference staging,
    output containment, Asset publication and Evidence.
    """

    def __init__(
        self,
        *,
        store: SQLiteProductStore,
        resolver: LogicalPathResolver,
        client: ComfyUIClient,
        workflow_policy: SourcePathPolicy,
        comfy_output_root: Path,
        comfy_input_root: Path,
        staging_root: Path,
        resource_policy: ComfyResourcePolicy | None = None,
        media_probe: FFprobeMediaProbe | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver
        self.client = client
        self.workflow_policy = workflow_policy
        self.comfy_output_root = comfy_output_root.resolve(strict=True)
        self.comfy_input_root = comfy_input_root.resolve(strict=True)
        self.staging_root = staging_root.resolve(strict=False)
        self.resource_policy = resource_policy or ComfyResourcePolicy()
        self.media_probe = media_probe or FFprobeMediaProbe()
        self.publisher = DerivedAssetPublisher(store=store, resolver=resolver)
        self.manifests = Task004ManifestWriter(store=store, resolver=resolver)

    def capability_report(self) -> dict[str, Any]:
        info = self.client.object_info()
        required = {
            "MiniMaxH3SingleFrameEdit",
            "MiniMaxH3StartEndFrameInterpolate",
            "MiniMaxH3SelectFrame",
        }
        optional = {"MiniMaxH3TemporalRoPEPatch", "EmptyMiniMaxH3SingleFrameLatent"}
        return {
            "provider": "MINIMAX_H3_SINGLE_FRAME_EXTERNAL_NODE",
            "source_license_state": "NO_LICENSE_DECLARED_AT_REVIEW_TIME",
            "core_code_incorporated": False,
            "required_nodes_present": sorted(required.intersection(info)),
            "required_nodes_missing": sorted(required.difference(info)),
            "optional_nodes_present": sorted(optional.intersection(info)),
            "frame_count_rule": "min=5 and frame_count % 17 == 5",
        }

    def _completed(self, request: H3SingleFrameRequest, operation: OperationRecord) -> H3SingleFrameResult:
        manifest = self.store.find_manifest_by_operation(operation.operation_id, "h3-single-frame-manifest")
        if manifest is None:
            raise ProductError("ERR_INTEGRITY_H3_SINGLE_FRAME_MANIFEST_MISSING", "completed H3 single-frame manifest is missing", ProductErrorCategory.DATA_INTEGRITY)
        doc = self.manifests.load_verified(manifest)
        ids = [a["asset_id"] for a in doc["payload"]["output_assets"]]
        if len(ids) != 1:
            raise ProductError("ERR_INTEGRITY_H3_SINGLE_FRAME_RESULT", "H3 single-frame manifest must contain one output Asset", ProductErrorCategory.DATA_INTEGRITY)
        return H3SingleFrameResult(operation, ids[0], manifest.uri, f"job://{request.production_job_id}/evidence/task004.jsonl", doc["payload"]["details"].get("prompt_id", ""))

    def _stage_references(self, request: H3SingleFrameRequest, operation: OperationRecord) -> tuple[tuple[str, ...], tuple[str, ...], Path, dict[str, str]]:
        request.contract.validate_reference_count(len(request.reference_asset_ids))
        request.contract.validate_selected_frame()
        assets = []
        total_bytes = 0
        for asset_id in request.reference_asset_ids:
            asset = self.store.get_asset(asset_id)
            if asset.production_job_id != request.production_job_id:
                raise ProductError("ERR_SECURITY_H3_SINGLE_FRAME_REFERENCE_SCOPE", "H3 single-frame reference belongs to another Job", ProductErrorCategory.SECURITY)
            if asset.asset_type is not AssetType.IMAGE:
                raise ProductError("ERR_INPUT_H3_SINGLE_FRAME_REFERENCE_TYPE", "H3 single-frame references must be IMAGE Assets", ProductErrorCategory.VALIDATION)
            if not asset.derivative_use_allowed:
                raise ProductError("ERR_AUTH_H3_SINGLE_FRAME_REFERENCE_RIGHTS", "H3 single-frame reference is not authorized for derivative generation", ProductErrorCategory.AUTHORIZATION)
            source = self.resolver.resolve(asset.logical_uri)
            if not isinstance(source, Path) or not source.exists() or source.is_symlink() or sha256_file(source) != asset.checksum:
                raise ProductError("ERR_INTEGRITY_H3_SINGLE_FRAME_REFERENCE", "H3 single-frame reference is missing, symlinked or tampered", ProductErrorCategory.DATA_INTEGRITY)
            total_bytes += source.stat().st_size
            assets.append((asset, source))
        _admit_comfy_input_staging_disk(self.comfy_input_root, total_bytes, self.resource_policy)
        relative_dir = Path("bai-task004-h3-single-frame") / request.production_job_id / operation.operation_id
        target_dir = _prepare_owned_comfy_subdir(self.comfy_input_root, relative_dir)
        refs: list[str] = []
        checksums: list[str] = []
        substitutions: dict[str, str] = {}
        try:
            for index, (asset, source) in enumerate(assets, 1):
                suffix = source.suffix.lower() or ".png"
                target = target_dir / f"reference-{index:02d}{suffix}"
                shutil.copyfile(source, target)
                if sha256_file(target) != asset.checksum:
                    raise ProductError("ERR_INTEGRITY_H3_SINGLE_FRAME_REFERENCE_COPY", "H3 single-frame reference copy checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
                refs.append(asset.logical_uri)
                checksums.append(asset.checksum)
                substitutions[f"REFERENCE_{index}"] = (relative_dir / target.name).as_posix()
            return tuple(refs), tuple(checksums), target_dir, substitutions
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

    def generate(self, request: H3SingleFrameRequest) -> H3SingleFrameResult:
        if not request.authorize_execution:
            raise ProductError("ERR_AUTH_H3_SINGLE_FRAME_EXECUTION_REQUIRED", "H3 single-frame generation requires explicit execution authorization", ProductErrorCategory.AUTHORIZATION)
        license_ref = _validate_license_authorization_ref(request.license_authorization_ref)
        if not license_ref:
            raise ProductError("ERR_AUTH_H3_SINGLE_FRAME_MODEL_LICENSE", "MiniMax H3 single-frame execution requires explicit model-license acknowledgement", ProductErrorCategory.AUTHORIZATION)
        external_node_ref = _validate_license_authorization_ref(request.external_node_authorization_ref)
        if not external_node_ref:
            raise ProductError("ERR_AUTH_H3_SINGLE_FRAME_EXTERNAL_NODE_LICENSE", "the reviewed external H3 SingleFrame node had no declared license; execution requires explicit local-use authorization/acknowledgement", ProductErrorCategory.AUTHORIZATION)
        if not request.prompt.strip() or len(request.prompt) > 20_000 or "\x00" in request.prompt:
            raise ProductError("ERR_INPUT_H3_SINGLE_FRAME_PROMPT", "H3 single-frame prompt must be non-empty bounded text", ProductErrorCategory.VALIDATION)
        if request.seed < 0 or request.seed > 2**63 - 1:
            raise ProductError("ERR_INPUT_H3_SINGLE_FRAME_SEED", "H3 single-frame seed is out of range", ProductErrorCategory.VALIDATION)
        if _RESERVED.intersection(request.substitutions):
            raise ProductError("ERR_INPUT_H3_SINGLE_FRAME_RESERVED_SUBSTITUTION", "caller substitutions must not override managed H3 single-frame fields", ProductErrorCategory.VALIDATION)
        if not 0.1 <= request.poll_interval_seconds <= 30 or not 1 <= request.completion_timeout_seconds <= 86400:
            raise ValueError("invalid H3 single-frame polling configuration")

        workflow_path = self.workflow_policy.authorize_file(request.workflow_path)
        workflow_raw = _load_workflow_json(workflow_path)
        request_command = _request_bound_command("LOCAL_H3_SINGLE_FRAME", {
            "workflow_checksum": sha256_bytes(canonical_json_bytes(workflow_raw)),
            "substitutions": request.substitutions,
            "prompt_checksum": sha256_bytes(request.prompt.encode("utf-8")),
            "seed": request.seed,
            "contract": request.contract.evidence_fields(),
            "reference_asset_ids": list(request.reference_asset_ids),
            "license_authorization_ref_checksum": sha256_bytes(license_ref.encode("utf-8")),
            "external_node_authorization_ref_checksum": sha256_bytes(external_node_ref.encode("utf-8")),
        })
        operation, _ = self.store.reserve_operation(request.production_job_id, request_command, request.idempotency_key)
        if operation.status == "COMPLETED":
            return self._completed(request, operation)
        source_refs: tuple[str, ...] = ()
        source_checksums: tuple[str, ...] = ()
        reference_root: Path | None = None
        prompt_id = ""
        dispatched = bool(operation.result_ref)
        try:
            source_refs, source_checksums, reference_root, reference_substitutions = self._stage_references(request, operation)
            substitutions = dict(request.substitutions)
            substitutions.update(reference_substitutions)
            substitutions.update({
                "PROMPT": request.prompt,
                "SEED": request.seed,
                "FRAME_COUNT": request.contract.actual_frame_count,
                "SELECT_FRAME": request.contract.selected_frame_index,
                "ROPE_STRENGTH": request.contract.temporal_rope_strength,
            })
            workflow = render_workflow_placeholders(workflow_raw, substitutions)
            classes = workflow_class_types(workflow)
            request.contract.validate_workflow_classes(tuple(sorted(classes)))
            object_info = self.client.object_info()
            assert_workflow_supported(workflow, object_info)
            assert_workflow_inputs_available(workflow, object_info)
            stats = self.client.system_stats()
            resource = admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
            operation, prompt_id, _resumed = _queue_or_resume_comfy_prompt(
                store=self.store, operation=operation, client=self.client, workflow=workflow
            )
            dispatched = True
            deadline = time.monotonic() + request.completion_timeout_seconds
            entry: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                entry = _history_entry(self.client.history(prompt_id), prompt_id)
                if entry is not None:
                    status = entry.get("status")
                    if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                        raise ProductError("ERR_PROVIDER_H3_SINGLE_FRAME_FAILED", "ComfyUI H3 single-frame workflow reported failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                    if _image_descriptors(entry):
                        break
                time.sleep(request.poll_interval_seconds)
            else:
                raise ProductError("ERR_PROVIDER_H3_SINGLE_FRAME_TIMEOUT", "H3 single-frame generation timed out", ProductErrorCategory.TIMEOUT, retryable=True)
            assert entry is not None
            images = _image_descriptors(entry)
            if len(images) != 1:
                raise ProductError("ERR_PROVIDER_H3_SINGLE_FRAME_AMBIGUOUS", "H3 single-frame workflow must expose exactly one canonical image output", ProductErrorCategory.HUMAN_REVIEW_REQUIRED, details={"image_count": len(images)})
            output = resolve_comfy_output(self.comfy_output_root, images[0])
            probe = self.media_probe.probe(output)
            if not probe.has_video:
                raise ProductError("ERR_INTEGRITY_H3_SINGLE_FRAME_OUTPUT", "H3 single-frame output is not a visual stream", ProductErrorCategory.DATA_INTEGRITY)
            raw_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow_raw))
            rendered_workflow_checksum = sha256_bytes(canonical_json_bytes(workflow))
            prompt_checksum = sha256_bytes(request.prompt.encode("utf-8"))
            provenance = {
                "provider": "COMFYUI_H3_SINGLE_FRAME_EXTERNAL_NODE",
                "model_family": "MiniMax-H3",
                "model_license_id": "MiniMax-H3-Community-License-Agreement",
                "external_node_license_state": "NO_LICENSE_DECLARED_AT_REVIEW_TIME",
                "external_node_code_incorporated": False,
                "license_authorization_ref_checksum": sha256_bytes(license_ref.encode("utf-8")),
                "external_node_authorization_ref_checksum": sha256_bytes(external_node_ref.encode("utf-8")),
                "prompt_checksum": prompt_checksum,
                "workflow_checksum": raw_workflow_checksum,
                "rendered_workflow_checksum": rendered_workflow_checksum,
                "seed": request.seed,
                "contract": request.contract.evidence_fields(),
                "reference_asset_ids": list(request.reference_asset_ids),
            }
            asset = self.publisher.publish(
                output,
                DerivedAssetSpec(
                    production_job_id=request.production_job_id,
                    namespace="h3-single-frame",
                    asset_type=AssetType.IMAGE,
                    owner="LOCAL_AI_OUTPUT",
                    rights_status=RightsStatus.UNKNOWN,
                    commercial_use=PermissionState.UNKNOWN,
                    derivative_allowed=PermissionState.UNKNOWN,
                    reuse_allowed=PermissionState.UNKNOWN,
                    audio_rights_status=AudioRightsStatus.NOT_APPLICABLE,
                    generation_provenance=provenance,
                    source_ref=request.reference_asset_ids[0] if request.reference_asset_ids else None,
                    media_metadata=probe.to_dict(),
                    publication_restrictions=("MODEL_LICENSE_REVIEW_REQUIRED", "EXTERNAL_NODE_LICENSE_REVIEW_REQUIRED", "HUMAN_IDENTITY_QA_REQUIRED"),
                ),
                operation_id=operation.operation_id,
            )
            details = dict(provenance)
            details.update({
                "prompt_id": prompt_id,
                "resource_admission": resource,
                "source_refs": list(source_refs),
                "output_binding": {"asset_id": asset.asset_id, "checksum": asset.checksum},
            })
            manifest = self.manifests.write(
                job_id=request.production_job_id,
                operation_id=operation.operation_id,
                manifest_type="h3-single-frame-manifest",
                schema_id="ai-video.h3-single-frame-manifest",
                lane="LOCAL_IMAGE_AI",
                operation_kind=request.contract.mode.value,
                source_refs=source_refs,
                input_checksums=(raw_workflow_checksum, rendered_workflow_checksum, prompt_checksum, *source_checksums),
                output_assets=(asset,),
                details=details,
                evidence_category="H3_SINGLE_FRAME_GENERATION",
                producer_component="h3-single-frame-external-node-adapter",
            )
            operation = self.store.update_operation_status(operation.operation_id, "COMPLETED", result_ref=asset.asset_id)
            return H3SingleFrameResult(operation, asset.asset_id, manifest.manifest.uri, manifest.evidence_uri, prompt_id)
        except Exception as exc:
            _mark_comfy_failure(self.store, operation, exc, dispatched=dispatched)
            if isinstance(exc, ProductError):
                raise
            raise ProductError("ERR_INTERNAL_H3_SINGLE_FRAME_FAILED", "H3 single-frame generation failed unexpectedly", ProductErrorCategory.INTERNAL, operation_id=operation.operation_id) from exc
        finally:
            if reference_root is not None:
                shutil.rmtree(reference_root, ignore_errors=True)
