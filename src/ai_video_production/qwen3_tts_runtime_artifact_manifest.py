"""Pure contract for an unaccepted TASK-014 Windows runtime artifact manifest.

The contract binds public retained artifacts, installed-distribution metadata,
runtime files, native/tool ownership and explicit system exclusions.  It does
not inspect a filesystem, resolve packages, import a target runtime, or grant
reuse/load authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit
import re

from .serialization import canonical_json_bytes


SCHEMA_ID = "bai.task014.qwen3-tts-runtime-artifact-manifest.v1"
STATUS = "CONTRACT_ONLY_UNACCEPTED"
_DOMAIN = b"TASK014_RUNTIME_ARTIFACT_MANIFEST_V1\n"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DIST = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION = re.compile(r"^\d+(?:\.\d+)*(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,254}$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_REQUIREMENT = re.compile(r"^(?! )(?!.* $)[\x20-\x7e]{1,256}$")
_WHEEL_FILENAME = re.compile(
    r"^(?P<name>[A-Za-z0-9_.]+)-(?P<version>\d+(?:\.\d+)*(?:\+[a-z0-9]+(?:[._][a-z0-9]+)*)?)"
    r"(?:-[0-9][A-Za-z0-9_.]*)?-(?P<tag>py3-none-any|cp3(?:9|10|11|12)-abi3-win_amd64|cp312-cp312-win_amd64)\.whl$"
)
_COMPATIBLE_WHEEL_TAG = re.compile(r"^(?:py3-none-any|cp3(?:9|10|11|12)-abi3-win_amd64|cp312-cp312-win_amd64)$")
_MAX_ITEMS = 256
_MAX_FILES = 8192
_MAX_BYTES = 64 * 1024**3

_ARTIFACT_KINDS = {"PYTHON_RUNTIME_ARCHIVE", "DISTRIBUTION_WHEEL", "NATIVE_TOOL_ARCHIVE", "LOCAL_BUILD_WHEEL"}
_PROVIDERS = {"PYTHON_ORG", "PYPI", "PYTORCH_INDEX", "OFFICIAL_PROJECT_RELEASE", "OWNER_ACCEPTED_LOCAL_BUILD"}
_PROVENANCE = {"OFFICIAL_INDEX_DIGEST", "OFFICIAL_RELEASE_DIGEST", "LOCAL_BUILD_ATTESTATION"}
_LOAD_POLICIES = {"REQUIRED_RUNTIME", "REQUIRED_TOOL", "BUILD_ONLY_EXCLUDED"}
_FILE_ROLES = {"PYTHON_EXECUTABLE", "PYTHON_SUPPORT", "DISTRIBUTION_PAYLOAD", "NATIVE_LIBRARY", "TOOL_EXECUTABLE"}
_TOOL_KINDS = {"FFMPEG", "FFPROBE", "SOX"}
_SYSTEM_REASONS = {"HOST_OS", "HARDWARE_DRIVER"}
_PUBLIC_HOSTS = {
    "PYTHON_ORG": {"python.org", "www.python.org"},
    "PYPI": {"files.pythonhosted.org"},
    "PYTORCH_INDEX": {"download.pytorch.org"},
    "OFFICIAL_PROJECT_RELEASE": {"github.com", "objects.githubusercontent.com"},
    "OWNER_ACCEPTED_LOCAL_BUILD": {"github.com"},
}
_QWEN_CONTRACT_ID = "task014-qwen-tts-0.1.1-wheel-payload"
_QWEN_CONTRACT_SCHEMA = "bai.task014.qwen-tts-locked-wheel-session-observation.v1"
_QWEN_WHEEL_FILENAME = "qwen_tts-0.1.1-py3-none-any.whl"
_QWEN_WHEEL_BYTES = 113_529
_QWEN_WHEEL_SHA256 = "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d"
_QWEN_PAYLOAD_SHA256 = "sha256:0a0568dfbbf716135c911322c22dc44df1e279dfd52ab25de9a4edb6a8a11dd6"
_MARKER_ENVIRONMENT = {
    "extra": "",
    "implementation_name": "cpython",
    "implementation_version": "3.12.4",
    "os_name": "nt",
    "platform_machine": "AMD64",
    "platform_system": "Windows",
    "python_full_version": "3.12.4",
    "python_version": "3.12",
    "sys_platform": "win32",
}
MARKER_ENVIRONMENT_SHA256 = "sha256:" + sha256(
    b"TASK014_PEP508_MARKER_ENVIRONMENT_V1\n" + canonical_json_bytes(_MARKER_ENVIRONMENT)
).hexdigest()
_NO_EFFECT_FIELDS = (
    "filesystem_read", "filesystem_write", "network_accessed", "package_resolved",
    "package_downloaded", "package_installed", "target_python_executed",
    "target_package_imported", "model_loaded", "owner_audio_read",
    "inference_started", "native_tool_executed",
)


def _expect(mapping: Mapping[str, Any], fields: set[str], label: str) -> None:
    if not isinstance(mapping, Mapping) or set(mapping) != fields:
        raise ValueError(f"{label} fields invalid")


def _string(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} invalid")
    return value


def _choice(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} invalid")
    return value


def _integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} invalid")
    return value


def _relative_path(value: Any, label: str) -> str:
    value = _string(value, re.compile(r"^[\x21-\x7e]{1,512}$"), label)
    if "\\" in value or value.startswith("/") or ":" in value or "//" in value:
        raise ValueError(f"{label} invalid")
    parts = value.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(
        part in {"", ".", ".."}
        or part.endswith((".", " "))
        or any(ord(char) < 32 or char in '<>"|?*' for char in part)
        or part.split(".", 1)[0].upper() in reserved
        for part in parts
    ):
        raise ValueError(f"{label} invalid")
    if len({part.casefold() for part in parts}) != len(parts) and len(parts) > 1:
        # Repeated directory names are legal; this check is intentionally not
        # used for path identity.  Cross-record case folding is checked later.
        pass
    return value


def _url(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("source_url invalid")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("source_url invalid") from exc
    if parsed.scheme != "https" or not parsed.hostname or port is not None or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("source_url invalid")
    if parsed.path.endswith("/") or not parsed.path:
        raise ValueError("source_url invalid")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _semantic_digest(body: Mapping[str, Any]) -> str:
    projected = {key: value for key, value in body.items() if key != "semantic_manifest_sha256"}
    return "sha256:" + sha256(_DOMAIN + canonical_json_bytes(projected)).hexdigest()


def runtime_file_mapping_sha256(value: Mapping[str, Any]) -> str:
    if not isinstance(value, Mapping):
        raise ValueError("runtime file mapping invalid")
    projected = {key: item for key, item in value.items() if key != "mapping_sha256"}
    return "sha256:" + sha256(b"TASK014_RUNTIME_FILE_MAPPING_V1\n" + canonical_json_bytes(projected)).hexdigest()


def _requirement_name(value: str) -> str:
    left = value.split(";", 1)[0].strip()
    if "[" in left or "]" in left:
        raise ValueError("dependency extras unsupported")
    match = re.fullmatch(
        r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
        r"(?P<specifiers>.*)",
        left,
    )
    if not match:
        raise ValueError("requirement invalid")
    specifiers = match.group("specifiers").strip()
    if specifiers:
        for item in specifiers.split(","):
            parsed = re.fullmatch(r"\s*(?P<op>===|==|!=|~=|<=|>=|<|>)\s*(?P<version>\d+(?:\.\d+)*(?:\.\*)?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?)\s*", item)
            if not parsed or ("*" in parsed.group("version") and parsed.group("op") not in {"==", "!="}):
                raise ValueError("requirement specifier invalid")
            expected = parsed.group("version")
            if "*" in expected and "+" in expected:
                raise ValueError("requirement wildcard local invalid")
            if parsed.group("op") in {"<", "<=", ">", ">=", "~="} and "+" in expected:
                raise ValueError("ordered local specifier invalid")
            if parsed.group("op") == "~=" and len(expected.split("+", 1)[0].split(".")) < 2:
                raise ValueError("compatible-release specifier invalid")
    return re.sub(r"[-_.]+", "-", match.group("name")).casefold()


def _marker_tokens(value: str) -> list[str]:
    token = re.compile(r"\s*(not\s+in|and|or|in|===|==|!=|~=|<=|>=|<|>|\(|\)|[A-Za-z_][A-Za-z0-9_]*|'[^']*'|\"[^\"]*\")")
    tokens: list[str] = []
    offset = 0
    while offset < len(value):
        match = token.match(value, offset)
        if not match:
            raise ValueError("marker expression invalid")
        tokens.append("not in" if match.group(1).startswith("not") else match.group(1))
        offset = match.end()
    return tokens


def _version_parts(value: str) -> tuple[tuple[int, ...], str | None]:
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?", value)
    if not match:
        raise ValueError("version comparison unsupported")
    release = tuple(int(item) for item in match.group(1).split("."))
    if "+" in value:
        raw_local = value.split("+", 1)[1]
        local = ".".join(str(int(item)) if item.isdigit() else item.casefold() for item in re.split(r"[._-]", raw_local))
    else:
        local = None
    return release, local


def _version_release(value: str) -> tuple[int, ...]:
    return _version_parts(value)[0]


def _compare(left: str, operator: str, right: str, *, version: bool) -> bool:
    if version:
        if operator in {"in", "not in"}:
            raise ValueError("version membership comparison unsupported")
        left_release, left_local = _version_parts(left)
        right_release, right_local = _version_parts(right)
    if operator in {"in", "not in"}:
        result = left in right
        return not result if operator == "not in" else result
    if operator == "===":
        return left == right
    if operator in {"==", "!="}:
        if version:
            width = max(len(left_release), len(right_release))
            release_equal = left_release + (0,) * (width - len(left_release)) == right_release + (0,) * (width - len(right_release))
            result = release_equal and (right_local is None or left_local == right_local)
        else:
            result = left == right
        return not result if operator == "!=" else result
    if not version:
        pair = (left, right)
    else:
        first, second = _version_release(left), _version_release(right)
        width = max(len(first), len(second))
        pair = (first + (0,) * (width - len(first)), second + (0,) * (width - len(second)))
    if operator == "<":
        return pair[0] < pair[1]
    if operator == "<=":
        return pair[0] <= pair[1]
    if operator == ">":
        return pair[0] > pair[1]
    if operator == ">=":
        return pair[0] >= pair[1]
    if operator == "~=":
        left_release, right_release = _version_release(left), _version_release(right)
        if right_local is not None or len(right_release) < 2:
            raise ValueError("compatible-release specifier unsupported")
        return _compare(left, ">=", right, version=True) and left_release[: max(1, len(right_release) - 1)] == right_release[: max(1, len(right_release) - 1)]
    raise ValueError("comparison operator invalid")


def _evaluate_marker(value: str) -> bool:
    tokens = _marker_tokens(value)
    index = 0

    def operand() -> tuple[str, bool]:
        nonlocal index
        if index >= len(tokens):
            raise ValueError("marker operand missing")
        raw = tokens[index]
        index += 1
        if raw.startswith(("'", '"')):
            return raw[1:-1], False
        if raw not in _MARKER_ENVIRONMENT:
            raise ValueError("marker variable unsupported")
        return _MARKER_ENVIRONMENT[raw], raw.endswith("version")

    def atom() -> bool:
        nonlocal index
        if index < len(tokens) and tokens[index] == "(":
            index += 1
            result = expression()
            if index >= len(tokens) or tokens[index] != ")":
                raise ValueError("marker parenthesis invalid")
            index += 1
            return result
        left, left_version = operand()
        if index >= len(tokens) or tokens[index] not in {"in", "not in", "===", "==", "!=", "~=", "<=", ">=", "<", ">"}:
            raise ValueError("marker comparison missing")
        operator = tokens[index]
        index += 1
        right, right_version = operand()
        if (left_version or right_version) and ("+" in left or "+" in right):
            raise ValueError("marker local version unsupported")
        return _compare(left, operator, right, version=left_version or right_version)

    def conjunction() -> bool:
        nonlocal index
        result = atom()
        while index < len(tokens) and tokens[index] == "and":
            index += 1
            right = atom()
            result = result and right
        return result

    def expression() -> bool:
        nonlocal index
        result = conjunction()
        while index < len(tokens) and tokens[index] == "or":
            index += 1
            right = conjunction()
            result = result or right
        return result

    result = expression()
    if index != len(tokens):
        raise ValueError("marker expression trailing data")
    return result


def _specifier_satisfied(requirement: str, version: str) -> bool:
    left = requirement.split(";", 1)[0].strip()
    match = re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*(?P<specifiers>.*)", left)
    if not match:
        raise ValueError("requirement invalid")
    specifiers = match.group("specifiers").strip()
    if not specifiers:
        return True
    for item in specifiers.split(","):
        parsed = re.fullmatch(r"\s*(?P<op>===|==|!=|~=|<=|>=|<|>)\s*(?P<version>\d+(?:\.\d+)*(?:\.\*)?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?)\s*", item)
        if not parsed:
            raise ValueError("requirement specifier invalid")
        expected = parsed.group("version")
        if "*" in expected and parsed.group("op") not in {"==", "!="}:
            raise ValueError("requirement wildcard operator invalid")
        if "*" in expected and "+" in expected:
            raise ValueError("requirement wildcard local invalid")
        if parsed.group("op") in {"<", "<=", ">", ">=", "~="} and "+" in expected:
            raise ValueError("ordered local specifier invalid")
        if parsed.group("op") == "~=" and len(expected.split("+", 1)[0].split(".")) < 2:
            raise ValueError("compatible-release specifier invalid")
        if expected.endswith(".*") and parsed.group("op") in {"==", "!="}:
            prefix = tuple(int(item) for item in expected[:-2].split("."))
            candidate = _version_release(version)
            candidate = candidate + (0,) * max(0, len(prefix) - len(candidate))
            equals = candidate[: len(prefix)] == prefix
            if equals != (parsed.group("op") == "=="):
                return False
        elif not _compare(version, parsed.group("op"), expected, version=True):
            return False
    return True


def _wheel_identity(filename: str) -> tuple[str, str, str]:
    match = _WHEEL_FILENAME.fullmatch(filename)
    if not match:
        raise ValueError("wheel filename identity invalid")
    return re.sub(r"[-_.]+", "-", match.group("name")).casefold(), match.group("version"), match.group("tag")


def _validate_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {"artifact_id", "kind", "provider", "source_url", "filename", "bytes", "sha256", "provenance", "wheel_tags", "load_policy", "local_build_binding", "source_contract"}
    _expect(value, fields, "artifact")
    result = dict(value)
    result["artifact_id"] = _string(result["artifact_id"], _ID, "artifact_id")
    result["kind"] = _choice(result["kind"], _ARTIFACT_KINDS, "artifact kind")
    result["provider"] = _choice(result["provider"], _PROVIDERS, "artifact provider")
    result["source_url"] = _url(result["source_url"])
    if (urlsplit(result["source_url"]).hostname or "").casefold() not in _PUBLIC_HOSTS[result["provider"]]:
        raise ValueError("source host not admitted for provider")
    result["filename"] = _string(result["filename"], _FILENAME, "artifact filename")
    if result["provider"] != "OWNER_ACCEPTED_LOCAL_BUILD" and urlsplit(result["source_url"]).path.rsplit("/", 1)[-1] != result["filename"]:
        raise ValueError("source_url filename mismatch")
    result["bytes"] = _integer(result["bytes"], 1, _MAX_BYTES, "artifact bytes")
    result["sha256"] = _string(result["sha256"], _SHA, "artifact sha256")
    result["provenance"] = _choice(result["provenance"], _PROVENANCE, "artifact provenance")
    result["load_policy"] = _choice(result["load_policy"], _LOAD_POLICIES, "artifact load_policy")
    if not isinstance(result["wheel_tags"], list) or len(result["wheel_tags"]) > 1:
        raise ValueError("wheel_tags invalid")
    result["wheel_tags"] = [_string(item, _TAG, "wheel tag") for item in result["wheel_tags"]]
    if len(set(result["wheel_tags"])) != len(result["wheel_tags"]):
        raise ValueError("wheel_tags duplicate")
    is_wheel = result["kind"] in {"DISTRIBUTION_WHEEL", "LOCAL_BUILD_WHEEL"}
    if is_wheel != bool(result["wheel_tags"]):
        raise ValueError("wheel tag presence invalid")
    if is_wheel and any(not _COMPATIBLE_WHEEL_TAG.fullmatch(tag) for tag in result["wheel_tags"]):
        raise ValueError("wheel tag incompatible")
    if is_wheel:
        _, _, filename_tag = _wheel_identity(result["filename"])
        if result["wheel_tags"] != [filename_tag]:
            raise ValueError("wheel filename tag mismatch")
    binding = result["local_build_binding"]
    if result["provenance"] == "LOCAL_BUILD_ATTESTATION":
        _expect(binding, {"source_sha256", "build_matrix_sha256", "same_machine_only"}, "local_build_binding")
        binding = dict(binding)
        binding["source_sha256"] = _string(binding["source_sha256"], _SHA, "source_sha256")
        binding["build_matrix_sha256"] = _string(binding["build_matrix_sha256"], _SHA, "build_matrix_sha256")
        if binding["same_machine_only"] is not True:
            raise ValueError("local build must be same-machine only")
        if result["provider"] != "OWNER_ACCEPTED_LOCAL_BUILD" or result["kind"] not in {"LOCAL_BUILD_WHEEL", "NATIVE_TOOL_ARCHIVE"}:
            raise ValueError("local build coordinates invalid")
        result["local_build_binding"] = binding
    elif binding is not None:
        raise ValueError("unexpected local_build_binding")
    contract = result["source_contract"]
    if contract is not None:
        _expect(contract, {"contract_id", "schema", "semantic_sha256", "role"}, "source_contract")
        contract = dict(contract)
        contract["contract_id"] = _string(contract["contract_id"], _ID, "source contract id")
        contract["schema"] = _string(contract["schema"], _ID, "source contract schema")
        contract["semantic_sha256"] = _string(contract["semantic_sha256"], _SHA, "source contract digest")
        contract["role"] = _choice(contract["role"], {"QWEN_TTS_WHEEL_PAYLOAD"}, "source contract role")
        result["source_contract"] = contract
    kind = result["kind"]
    matrix_ok = (
        kind == "PYTHON_RUNTIME_ARCHIVE" and result["provider"] == "PYTHON_ORG" and result["provenance"] == "OFFICIAL_RELEASE_DIGEST" and result["load_policy"] == "REQUIRED_RUNTIME" and result["filename"].endswith((".zip", ".exe"))
        or kind == "DISTRIBUTION_WHEEL" and result["provider"] in {"PYPI", "PYTORCH_INDEX", "OFFICIAL_PROJECT_RELEASE"} and result["provenance"] in {"OFFICIAL_INDEX_DIGEST", "OFFICIAL_RELEASE_DIGEST"} and result["load_policy"] == "REQUIRED_RUNTIME" and result["filename"].endswith(".whl")
        or kind == "LOCAL_BUILD_WHEEL" and result["provider"] == "OWNER_ACCEPTED_LOCAL_BUILD" and result["provenance"] == "LOCAL_BUILD_ATTESTATION" and result["load_policy"] in {"REQUIRED_RUNTIME", "BUILD_ONLY_EXCLUDED"} and result["filename"].endswith(".whl")
        or kind == "NATIVE_TOOL_ARCHIVE" and result["provider"] in {"OFFICIAL_PROJECT_RELEASE", "OWNER_ACCEPTED_LOCAL_BUILD"} and result["provenance"] in {"OFFICIAL_RELEASE_DIGEST", "LOCAL_BUILD_ATTESTATION"} and ((result["provider"] == "OWNER_ACCEPTED_LOCAL_BUILD") == (result["provenance"] == "LOCAL_BUILD_ATTESTATION")) and result["load_policy"] == "REQUIRED_TOOL" and result["filename"].endswith((".zip", ".7z", ".tar.xz"))
    )
    if not matrix_ok:
        raise ValueError("artifact coordinate matrix invalid")
    return result


def _validate_manifest(mapping: Mapping[str, Any]) -> dict[str, Any]:
    fields = {"schema", "status", "manifest_id", "revision", "platform", "artifacts", "distributions", "root_distribution_ids", "runtime_files", "system_exclusions", "tools", "counts", "diagnostic_only", "persistent_manifest_is_capability", "runtime_reuse_authorized", "model_load_authorized", "consumer_execution_authorized", "post_return_state_guaranteed", "consumer_revalidation_required", "no_effect_flags", "semantic_manifest_sha256"}
    _expect(mapping, fields, "manifest")
    result = dict(mapping)
    if result["schema"] != SCHEMA_ID or result["status"] != STATUS:
        raise ValueError("schema or status invalid")
    result["manifest_id"] = _string(result["manifest_id"], _ID, "manifest_id")
    result["revision"] = _integer(result["revision"], 1, 2_147_483_647, "revision")
    platform = result["platform"]
    _expect(platform, {"os", "architecture", "python_abi", "python_version"}, "platform")
    if dict(platform) != {"os": "WINDOWS", "architecture": "win_amd64", "python_abi": "cp312", "python_version": "3.12.4"}:
        raise ValueError("platform mismatch")

    if not isinstance(result["artifacts"], list) or not 1 <= len(result["artifacts"]) <= _MAX_ITEMS:
        raise ValueError("artifacts invalid")
    artifacts = [_validate_artifact(item) for item in result["artifacts"]]
    artifact_ids = [item["artifact_id"] for item in artifacts]
    if len({item.casefold() for item in artifact_ids}) != len(artifact_ids):
        raise ValueError("artifact id collision")
    artifact_by_id = {item["artifact_id"]: item for item in artifacts}
    qwen_contract_artifacts = [item for item in artifacts if item["source_contract"] is not None]
    if len(qwen_contract_artifacts) != 1:
        raise ValueError("exact qwen source contract required")
    qwen_artifact = qwen_contract_artifacts[0]
    qwen_contract = qwen_artifact["source_contract"]
    if (
        qwen_artifact["filename"] != _QWEN_WHEEL_FILENAME
        or qwen_artifact["bytes"] != _QWEN_WHEEL_BYTES
        or qwen_artifact["sha256"] != _QWEN_WHEEL_SHA256
        or qwen_artifact["kind"] != "DISTRIBUTION_WHEEL"
        or qwen_artifact["provider"] != "PYPI"
        or qwen_artifact["provenance"] != "OFFICIAL_INDEX_DIGEST"
        or qwen_artifact["load_policy"] != "REQUIRED_RUNTIME"
        or qwen_artifact["wheel_tags"] != ["py3-none-any"]
        or qwen_contract != {
            "contract_id": _QWEN_CONTRACT_ID,
            "schema": _QWEN_CONTRACT_SCHEMA,
            "semantic_sha256": _QWEN_PAYLOAD_SHA256,
            "role": "QWEN_TTS_WHEEL_PAYLOAD",
        }
    ):
        raise ValueError("qwen source contract mismatch")
    result["artifacts"] = artifacts

    if not isinstance(result["distributions"], list) or not 1 <= len(result["distributions"]) <= _MAX_ITEMS:
        raise ValueError("distributions invalid")
    distributions: list[dict[str, Any]] = []
    for item in result["distributions"]:
        _expect(item, {"distribution_id", "version", "artifact_id", "dist_info_dir", "record_sha256", "payload_inventory_sha256", "dependencies"}, "distribution")
        dist = dict(item)
        dist["distribution_id"] = _string(dist["distribution_id"], _DIST, "distribution_id")
        dist["version"] = _string(dist["version"], _VERSION, "distribution version")
        dist["artifact_id"] = _string(dist["artifact_id"], _ID, "distribution artifact_id")
        if dist["artifact_id"] not in artifact_by_id or artifact_by_id[dist["artifact_id"]]["kind"] not in {"DISTRIBUTION_WHEEL", "LOCAL_BUILD_WHEEL"}:
            raise ValueError("distribution artifact missing")
        dist["dist_info_dir"] = _relative_path(dist["dist_info_dir"], "dist_info_dir")
        wheel_name, wheel_version, _ = _wheel_identity(artifact_by_id[dist["artifact_id"]]["filename"])
        expected_dist_info = artifact_by_id[dist["artifact_id"]]["filename"].split("-", 1)[0] + "-" + wheel_version + ".dist-info"
        if wheel_name != dist["distribution_id"] or wheel_version != dist["version"] or dist["dist_info_dir"].casefold() != ("Lib/site-packages/" + expected_dist_info).casefold():
            raise ValueError("distribution wheel identity mismatch")
        dist["record_sha256"] = _string(dist["record_sha256"], _SHA, "record_sha256")
        dist["payload_inventory_sha256"] = _string(dist["payload_inventory_sha256"], _SHA, "payload_inventory_sha256")
        if not isinstance(dist["dependencies"], list) or len(dist["dependencies"]) > _MAX_ITEMS:
            raise ValueError("dependencies invalid")
        deps = []
        for dep in dist["dependencies"]:
            _expect(dep, {"requirement_id", "distribution_id", "requirement", "marker_expression", "marker_environment_sha256", "marker_state"}, "dependency")
            dep = dict(dep)
            dep["requirement_id"] = _string(dep["requirement_id"], _ID, "requirement_id")
            dep["distribution_id"] = _string(dep["distribution_id"], _DIST, "dependency distribution_id")
            dep["requirement"] = _string(dep["requirement"], _REQUIREMENT, "requirement")
            if _requirement_name(dep["requirement"]) != dep["distribution_id"]:
                raise ValueError("requirement name mismatch")
            if dep["marker_expression"] is not None:
                dep["marker_expression"] = _string(dep["marker_expression"], _REQUIREMENT, "marker_expression")
            requirement_parts = dep["requirement"].split(";", 1)
            observed_marker = requirement_parts[1].strip() if len(requirement_parts) == 2 else None
            if observed_marker != dep["marker_expression"]:
                raise ValueError("requirement marker mismatch")
            dep["marker_environment_sha256"] = _string(dep["marker_environment_sha256"], _SHA, "marker_environment_sha256")
            if dep["marker_environment_sha256"] != MARKER_ENVIRONMENT_SHA256:
                raise ValueError("marker environment mismatch")
            dep["marker_state"] = _choice(dep["marker_state"], {"ACTIVE", "INACTIVE"}, "marker_state")
            expected_marker_state = "ACTIVE" if dep["marker_expression"] is None or _evaluate_marker(dep["marker_expression"]) else "INACTIVE"
            if dep["marker_state"] != expected_marker_state:
                raise ValueError("marker state mismatch")
            deps.append(dep)
        if len({dep["requirement_id"].casefold() for dep in deps}) != len(deps):
            raise ValueError("duplicate requirement identity")
        dist["dependencies"] = deps
        distributions.append(dist)
    dist_ids = [item["distribution_id"] for item in distributions]
    if len(set(dist_ids)) != len(dist_ids):
        raise ValueError("distribution collision")
    dist_by_id = {item["distribution_id"]: item for item in distributions}
    for dist in distributions:
        for dep in dist["dependencies"]:
            if dep["marker_state"] == "ACTIVE":
                if dep["distribution_id"] not in dist_by_id:
                    raise ValueError("active dependency missing")
                if not _specifier_satisfied(dep["requirement"], dist_by_id[dep["distribution_id"]]["version"]):
                    raise ValueError("active dependency version mismatch")
    result["distributions"] = distributions

    roots = result["root_distribution_ids"]
    if not isinstance(roots, list) or not roots:
        raise ValueError("root_distribution_ids invalid")
    roots = [_string(item, _DIST, "root_distribution_id") for item in roots]
    if len(set(roots)) != len(roots) or any(item not in dist_by_id for item in roots):
        raise ValueError("root_distribution_ids invalid")
    result["root_distribution_ids"] = roots
    qwen = dist_by_id.get("qwen-tts")
    if qwen is None or "qwen-tts" not in roots:
        raise ValueError("qwen-tts root distribution missing")
    qwen_artifact = artifact_by_id[qwen["artifact_id"]]
    if not qwen_artifact["source_contract"] or qwen_artifact["source_contract"]["role"] != "QWEN_TTS_WHEEL_PAYLOAD":
        raise ValueError("qwen external contract missing")
    visiting: set[str] = set()
    reached: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("active dependency cycle")
        if node in reached:
            return
        visiting.add(node)
        for dep in dist_by_id[node]["dependencies"]:
            if dep["marker_state"] == "ACTIVE":
                visit(dep["distribution_id"])
        visiting.remove(node)
        reached.add(node)
    for root in roots:
        visit(root)
    if reached != set(dist_by_id):
        raise ValueError("orphan or inactive-only distribution")

    exclusions = result["system_exclusions"]
    if not isinstance(exclusions, list) or len(exclusions) > 64:
        raise ValueError("system_exclusions invalid")
    normalized_exclusions = []
    for item in exclusions:
        _expect(item, {"exclusion_id", "name", "reason", "required_at_load_only"}, "system_exclusion")
        item = dict(item)
        item["exclusion_id"] = _string(item["exclusion_id"], _ID, "exclusion_id")
        item["name"] = _string(item["name"], _FILENAME, "system exclusion name")
        item["reason"] = _choice(item["reason"], _SYSTEM_REASONS, "system exclusion reason")
        if item["required_at_load_only"] is not True:
            raise ValueError("system exclusion must be load-only observed")
        normalized_exclusions.append(item)
    exclusion_ids = [item["exclusion_id"] for item in normalized_exclusions]
    if len({item.casefold() for item in exclusion_ids}) != len(exclusion_ids):
        raise ValueError("system exclusion collision")
    exclusion_by_id = {item["exclusion_id"]: item for item in normalized_exclusions}
    result["system_exclusions"] = normalized_exclusions

    files = result["runtime_files"]
    if not isinstance(files, list) or not 1 <= len(files) <= _MAX_FILES:
        raise ValueError("runtime_files invalid")
    normalized_files = []
    for item in files:
        _expect(item, {"logical_path", "artifact_member_path", "role", "owner_kind", "owner_id", "bytes", "sha256", "mapping_sha256"}, "runtime_file")
        item = dict(item)
        item["logical_path"] = _relative_path(item["logical_path"], "runtime logical_path")
        if item["artifact_member_path"] is not None:
            item["artifact_member_path"] = _relative_path(item["artifact_member_path"], "artifact member path")
        item["role"] = _choice(item["role"], _FILE_ROLES, "runtime file role")
        item["owner_kind"] = _choice(item["owner_kind"], {"ARTIFACT", "SYSTEM_PREREQUISITE"}, "owner_kind")
        item["owner_id"] = _string(item["owner_id"], _ID, "owner_id")
        item["bytes"] = _integer(item["bytes"], 0, _MAX_BYTES, "runtime file bytes")
        item["sha256"] = _string(item["sha256"], _SHA, "runtime file sha256")
        item["mapping_sha256"] = _string(item["mapping_sha256"], _SHA, "runtime file mapping_sha256")
        if item["mapping_sha256"] != runtime_file_mapping_sha256(item):
            raise ValueError("runtime file mapping digest mismatch")
        if item["owner_kind"] == "ARTIFACT":
            if item["owner_id"] not in artifact_by_id:
                raise ValueError("runtime artifact owner missing")
            if item["artifact_member_path"] is None:
                raise ValueError("artifact member path missing")
            artifact_kind = artifact_by_id[item["owner_id"]]["kind"]
            if item["role"] in {"PYTHON_EXECUTABLE", "PYTHON_SUPPORT"} and artifact_kind != "PYTHON_RUNTIME_ARCHIVE":
                raise ValueError("Python file owner invalid")
            if item["role"] in {"DISTRIBUTION_PAYLOAD", "NATIVE_LIBRARY"} and artifact_kind not in {"DISTRIBUTION_WHEEL", "LOCAL_BUILD_WHEEL"}:
                raise ValueError("distribution file owner invalid")
            if item["role"] == "TOOL_EXECUTABLE" and artifact_kind != "NATIVE_TOOL_ARCHIVE":
                raise ValueError("tool file owner invalid")
        else:
            if item["owner_id"] not in exclusion_by_id:
                raise ValueError("system prerequisite owner missing")
            if item["artifact_member_path"] is not None or item["role"] != "NATIVE_LIBRARY":
                raise ValueError("system prerequisite role invalid")
            if item["logical_path"].split("/")[-1].casefold() != exclusion_by_id[item["owner_id"]]["name"].casefold():
                raise ValueError("system prerequisite name mismatch")
        normalized_files.append(item)
    paths = [item["logical_path"] for item in normalized_files]
    if len({item.casefold() for item in paths}) != len(paths):
        raise ValueError("runtime path collision")
    result["runtime_files"] = normalized_files
    python_executables = [item for item in normalized_files if item["role"] == "PYTHON_EXECUTABLE"]
    if len(python_executables) != 1 or python_executables[0]["logical_path"] != "Scripts/python.exe":
        raise ValueError("exact Python executable missing")

    tools = result["tools"]
    if not isinstance(tools, list) or len(tools) > 8:
        raise ValueError("tools invalid")
    normalized_tools = []
    file_by_path = {item["logical_path"]: item for item in normalized_files}
    for item in tools:
        _expect(item, {"tool_id", "kind", "artifact_id", "logical_path"}, "tool")
        item = dict(item)
        item["tool_id"] = _string(item["tool_id"], _ID, "tool_id")
        item["kind"] = _choice(item["kind"], _TOOL_KINDS, "tool kind")
        item["artifact_id"] = _string(item["artifact_id"], _ID, "tool artifact_id")
        item["logical_path"] = _relative_path(item["logical_path"], "tool logical_path")
        runtime_file = file_by_path.get(item["logical_path"])
        if item["artifact_id"] not in artifact_by_id or artifact_by_id[item["artifact_id"]]["load_policy"] != "REQUIRED_TOOL":
            raise ValueError("tool artifact invalid")
        if not runtime_file or runtime_file["role"] != "TOOL_EXECUTABLE" or runtime_file["owner_kind"] != "ARTIFACT" or runtime_file["owner_id"] != item["artifact_id"]:
            raise ValueError("tool runtime file invalid")
        normalized_tools.append(item)
    if len({item["tool_id"].casefold() for item in normalized_tools}) != len(normalized_tools) or len({item["kind"] for item in normalized_tools}) != len(normalized_tools):
        raise ValueError("tool collision")
    if not {"FFMPEG", "FFPROBE"}.issubset({item["kind"] for item in normalized_tools}):
        raise ValueError("required tool pair missing")
    pair = {item["kind"]: item for item in normalized_tools}
    if pair["FFMPEG"]["artifact_id"] != pair["FFPROBE"]["artifact_id"]:
        raise ValueError("ffmpeg tool pair artifact mismatch")
    result["tools"] = normalized_tools

    distribution_artifact_ids = [item["artifact_id"] for item in distributions]
    if len(set(distribution_artifact_ids)) != len(distribution_artifact_ids):
        raise ValueError("distribution artifact reused")
    file_owner_ids = {item["owner_id"] for item in normalized_files if item["owner_kind"] == "ARTIFACT"}
    exclusion_owner_ids = {item["owner_id"] for item in normalized_files if item["owner_kind"] == "SYSTEM_PREREQUISITE"}
    tool_artifact_ids = {item["artifact_id"] for item in normalized_tools}
    if exclusion_owner_ids != set(exclusion_by_id):
        raise ValueError("unused system exclusion")
    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        if artifact["load_policy"] == "BUILD_ONLY_EXCLUDED":
            if artifact_id in file_owner_ids or artifact_id in distribution_artifact_ids or artifact_id in tool_artifact_ids:
                raise ValueError("build-only artifact used by runtime")
        elif artifact["load_policy"] == "REQUIRED_TOOL":
            if artifact_id not in tool_artifact_ids:
                raise ValueError("required tool artifact unused")
        elif artifact["kind"] in {"DISTRIBUTION_WHEEL", "LOCAL_BUILD_WHEEL"}:
            if artifact_id not in distribution_artifact_ids:
                raise ValueError("distribution artifact unbound")
        elif artifact_id not in file_owner_ids:
            raise ValueError("runtime artifact unused")
    for dist in distributions:
        owned = [item for item in normalized_files if item["owner_kind"] == "ARTIFACT" and item["owner_id"] == dist["artifact_id"]]
        if not owned or not any(item["role"] in {"DISTRIBUTION_PAYLOAD", "NATIVE_LIBRARY"} for item in owned):
            raise ValueError("distribution payload mapping missing")

    counts = result["counts"]
    _expect(counts, {"artifact_count", "distribution_count", "runtime_file_count", "system_exclusion_count", "tool_count", "total_artifact_bytes"}, "counts")
    expected_counts = {"artifact_count": len(artifacts), "distribution_count": len(distributions), "runtime_file_count": len(normalized_files), "system_exclusion_count": len(normalized_exclusions), "tool_count": len(normalized_tools), "total_artifact_bytes": sum(item["bytes"] for item in artifacts)}
    if dict(counts) != expected_counts:
        raise ValueError("counts mismatch")

    constants = {"diagnostic_only": True, "persistent_manifest_is_capability": False, "runtime_reuse_authorized": False, "model_load_authorized": False, "consumer_execution_authorized": False, "post_return_state_guaranteed": False, "consumer_revalidation_required": True}
    if any(result[key] is not value for key, value in constants.items()):
        raise ValueError("authority boundary invalid")
    flags = result["no_effect_flags"]
    _expect(flags, set(_NO_EFFECT_FIELDS), "no_effect_flags")
    if any(flags[key] is not False for key in _NO_EFFECT_FIELDS):
        raise ValueError("effect flag invalid")
    result["no_effect_flags"] = dict(flags)
    result["semantic_manifest_sha256"] = _string(result["semantic_manifest_sha256"], _SHA, "semantic_manifest_sha256")
    if result["semantic_manifest_sha256"] != _semantic_digest(result):
        raise ValueError("semantic manifest digest mismatch")
    return result


@dataclass(frozen=True, slots=True, init=False)
class RuntimeArtifactManifest:
    _value: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._value)


def _new_manifest(value: Mapping[str, Any]) -> RuntimeArtifactManifest:
    manifest = object.__new__(RuntimeArtifactManifest)
    object.__setattr__(manifest, "_value", _freeze(value))
    return manifest


def compile_runtime_artifact_manifest(body: Mapping[str, Any]) -> RuntimeArtifactManifest:
    if not isinstance(body, Mapping) or "semantic_manifest_sha256" in body:
        raise ValueError("manifest body invalid")
    candidate = dict(body)
    candidate["semantic_manifest_sha256"] = _semantic_digest(candidate)
    return _new_manifest(_validate_manifest(candidate))


def parse_runtime_artifact_manifest(mapping: Mapping[str, Any]) -> RuntimeArtifactManifest:
    return _new_manifest(_validate_manifest(mapping))


def assert_no_effect_surface() -> None:
    forbidden = {"open", "write", "download", "install", "resolve", "execute", "launch", "import_target", "load_model"}
    public = {name for name, value in globals().items() if callable(value) and not name.startswith("_")}
    if public & forbidden:
        raise AssertionError("forbidden effect surface exposed")
