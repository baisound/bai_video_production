from __future__ import annotations

import argparse
import getpass
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable


FEATURE_TERMS = {
    "NOISE_SUPPRESSION": (("openvino", "noise", "suppression"),),
    "MUSIC_SEPARATION": (("openvino", "music", "separation"),),
    "WHISPER_TRANSCRIPTION": (("openvino", "whisper"), ("openvino", "transcription")),
    "MUSIC_GENERATION": (("openvino", "music", "generation"), ("openvino", "musicgen")),
    "AUDIO_SUPER_RESOLUTION": (("openvino", "super", "resolution"),),
}

# Audacity exposes effect commands by squashing the effect's internal symbol to
# CamelCase.  Intel's OpenVINO effects use the symbols below, so capability
# discovery can query only the five relevant commands instead of enumerating the
# user's entire effect/plugin inventory with GetInfo Type=Commands.
OPENVINO_FEATURE_COMMAND_IDS = {
    "NOISE_SUPPRESSION": ("OpenvinoNoiseSuppression",),
    "MUSIC_SEPARATION": ("OpenvinoMusicSeparation",),
    "WHISPER_TRANSCRIPTION": ("OpenvinoWhisperTranscription",),
    "MUSIC_GENERATION": ("OpenvinoMusicGeneration",),
    "AUDIO_SUPER_RESOLUTION": ("OpenvinoSuperResolution",),
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _descriptor_text(value: Any) -> str:
    parts: list[str] = []
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if str(key).lower() in {"id", "name", "label", "action", "command", "displayname", "display_name"} and isinstance(child, str):
                    parts.append(child)
                elif isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)
    return _normalize(" ".join(parts))


def discover_features(commands: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for feature, alternatives in FEATURE_TERMS.items():
        matched = None
        for descriptor in commands:
            text = _descriptor_text(descriptor)
            if any(all(term in text for term in terms) for terms in alternatives):
                matched = descriptor
                break
        result[feature] = matched
    return result


def _command_id(descriptor: dict[str, Any]) -> str | None:
    for key in ("id", "command", "action", "name"):
        value = descriptor.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parameter_descriptors(descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            looks_like_param = any(k in node for k in ("default", "choices", "enum", "values")) and any(k in node for k in ("id", "name", "key", "label"))
            if looks_like_param:
                found.append(node)
            for k, v in node.items():
                if k.lower() in {"params", "parameters", "arguments", "args"} or isinstance(v, (dict, list)):
                    walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
    walk(descriptor)
    # de-duplicate identity-ish entries
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in found:
        name = _param_name(item)
        if name and name not in seen:
            seen.add(name); unique.append(item)
    return unique


def _param_name(param: dict[str, Any]) -> str | None:
    for key in ("id", "key", "name", "label"):
        value = param.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _choices(param: dict[str, Any]) -> list[Any]:
    for key in ("choices", "enum", "values"):
        value = param.get(key)
        if isinstance(value, list):
            return value
    return []


def validate_effect_parameters(descriptor: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
    params = _parameter_descriptors(descriptor)
    allowed = {name for p in params if (name := _param_name(p))}
    unknown = sorted(set(supplied) - allowed)
    if unknown:
        raise ValueError("unknown effect parameters: " + ", ".join(unknown))
    result: dict[str, Any] = {}
    # Stabilize available defaults where the runtime exposes them.
    for param in params:
        name = _param_name(param)
        if name and "default" in param and isinstance(param["default"], (str, int, float, bool)):
            result[name] = param["default"]
    result.update(supplied)
    return result


def separation_parameters(descriptor: dict[str, Any], mode: str, supplied: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Resolve scriptable separation parameters without pretending UI-only state is scriptable.

    Intel's Audacity OpenVINO Music Separation effect currently exposes no
    automatable parameters through Audacity Help/GetCommandDefinition, while
    its implementation initializes the separation-mode selector to index 0 and
    defines index 0 as the 2-stem Instrumental/Vocals mode.  Therefore the
    no-parameter command is a provable 2-stem default for the exact Intel
    effect, but 4-stem is not safely selectable through mod-script-pipe on this
    runtime contract.
    """
    result = validate_effect_parameters(descriptor, supplied)
    if supplied:
        return result, "EXPLICIT_DISCOVERED_PARAMETERS"
    wanted = "2" if mode == "2_STEM" else "4"
    params = _parameter_descriptors(descriptor)
    for param in params:
        name = _param_name(param)
        if not name:
            continue
        label = _normalize(name + " " + str(param.get("label", "")))
        if not any(term in label for term in ("stem", "separation", "mode")):
            continue
        for choice in _choices(param):
            text = _normalize(str(choice))
            if wanted in text and "stem" in text:
                result[name] = choice
                return result, "DISCOVERED_MODE_PARAMETER"

    command_id = (_command_id(descriptor) or "").casefold()
    effect_name = str(descriptor.get("name") or "").casefold()
    exact_intel_effect = command_id == "openvinomusicseparation" and effect_name == "openvino music separation"
    if exact_intel_effect and not params and mode == "2_STEM":
        return {}, "INTEL_RUNTIME_DEFAULT_2_STEM"
    if exact_intel_effect and not params and mode == "4_STEM":
        raise RuntimeError("OpenVINO Music Separation 4-stem mode is UI-only on this Audacity runtime and is not safely script-selectable")
    raise ValueError("runtime did not expose a provable 2-stem/4-stem parameter; supply explicit discovered parameters")


_SAFE_PARAM_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9 _.-]{0,127}$")


def _safe_arg(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Audacity command numeric argument must be finite")
        return str(value)
    text = str(value)
    if len(text) > 4096 or any(ch in text for ch in ("\r", "\n", '"')):
        raise ValueError("Audacity command argument contains forbidden or excessive text")
    return f'"{text}"'


def build_command(command_id: str, params: dict[str, Any] | None = None) -> str:
    if any(ch in command_id for ch in ("\r", "\n", ":")) or not command_id.strip() or len(command_id) > 256:
        raise ValueError("invalid Audacity command id")
    safe_params = params or {}
    for key in safe_params:
        if not isinstance(key, str) or not _SAFE_PARAM_KEY.fullmatch(key) or any(ch in key for ch in (":", "=", '"')):
            raise ValueError("invalid Audacity command parameter name")
    suffix = " ".join(f"{key}={_safe_arg(value)}" for key, value in safe_params.items())
    return f"{command_id}:" + (" " + suffix if suffix else "")




def _command_eol_for_os_name(name: str) -> str:
    """Return the exact mod-script-pipe command terminator for the host OS."""
    return "\r\n\0" if name == "nt" else "\n"

def _extract_json(reply: str) -> Any:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(reply):
        if ch not in "[{":
            continue
        try:
            value, _end = decoder.raw_decode(reply[i:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("Audacity response did not contain JSON")


def _extract_json_of_type(reply: str, expected_type: type) -> Any:
    """Extract the first complete JSON value of the requested top-level type.

    Audacity appends a textual BatchCommand status after command output.  Some
    third-party effects can also emit unrelated JSON-ish text while loading.
    Callers that know the contract (array for GetInfo, object for Help) must not
    accept the wrong JSON value merely because it appeared first in the reply.
    """
    decoder = json.JSONDecoder()
    for i, ch in enumerate(reply):
        if ch not in "[{":
            continue
        try:
            value, _end = decoder.raw_decode(reply[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, expected_type):
            return value
    expected = "array" if expected_type is list else "object" if expected_type is dict else expected_type.__name__
    raise ValueError(f"Audacity response did not contain a JSON {expected}")


class AudacityPipe:
    def __init__(self, *, max_reply_bytes: int = 16 * 1024 * 1024, max_reply_lines: int = 200000) -> None:
        if not 1024 <= max_reply_bytes <= 64 * 1024 * 1024:
            raise ValueError("max_reply_bytes must be 1 KiB-64 MiB")
        if not 1 <= max_reply_lines <= 1000000:
            raise ValueError("max_reply_lines must be 1-1000000")
        self.max_reply_bytes = max_reply_bytes
        self.max_reply_lines = max_reply_lines
        if os.name == "nt":
            self.to_path = r"\\.\pipe\ToSrvPipe"
            self.from_path = r"\\.\pipe\FromSrvPipe"
            # Audacity's Windows mod-script-pipe protocol requires CRLF + NUL.
            # A plain LF can be accepted inconsistently and may yield a status-only
            # response instead of the command payload (for example GetInfo JSON).
            self._command_eol = _command_eol_for_os_name(os.name)
        else:
            uid = os.getuid()
            self.to_path = f"/tmp/audacity_script_pipe.to.{uid}"
            self.from_path = f"/tmp/audacity_script_pipe.from.{uid}"
            self._command_eol = _command_eol_for_os_name(os.name)
        self._to = None
        self._from = None

    def __enter__(self) -> "AudacityPipe":
        # A parent supervisor enforces the hard timeout so this worker may block safely.
        # newline="" preserves the exact protocol terminator, including the
        # Windows NUL byte required by mod-script-pipe.
        self._to = open(self.to_path, "w", encoding="utf-8", newline="", buffering=1)
        self._from = open(self.from_path, "r", encoding="utf-8", errors="replace", newline="")
        return self

    def __exit__(self, *_exc: Any) -> None:
        if self._to:
            self._to.close()
        if self._from:
            self._from.close()

    def command(self, command: str) -> str:
        assert self._to is not None and self._from is not None
        self._to.write(command + self._command_eol)
        self._to.flush()
        lines: list[str] = []
        reply_bytes = 0
        content_seen = False
        while True:
            line = self._from.readline()
            if line == "":
                break
            if line in {"\n", "\r\n"}:
                # Audacity may prefix a mod-script-pipe response with one or more
                # blank lines. Its own pipe_test.py only treats a blank line as
                # the response delimiter after payload/status content has been
                # observed. Do the same so GetInfo JSON is not discarded before
                # it is read.
                if content_seen:
                    break
                continue
            content_seen = True
            reply_bytes += len(line.encode("utf-8", errors="replace"))
            if reply_bytes > self.max_reply_bytes or len(lines) >= self.max_reply_lines:
                raise RuntimeError("Audacity response exceeded the configured safety limit")
            lines.append(line)
        reply = "".join(lines)
        low = reply.lower()
        if "batchcommand finished: failed" in low or "error:" in low:
            raise RuntimeError("Audacity command reported failure")
        return reply


def _commands(pipe: AudacityPipe) -> list[dict[str, Any]]:
    # Retained as a diagnostic/fallback helper.  The live OpenVINO capability
    # path intentionally avoids this unbounded inventory query.
    value = _extract_json_of_type(pipe.command("GetInfo: Type=Commands Format=JSON"), list)
    return [x for x in value if isinstance(x, dict)]


def _help_descriptor(pipe: AudacityPipe, command_id: str) -> dict[str, Any] | None:
    reply = pipe.command(build_command("Help", {"Command": command_id, "Format": "JSON"}))
    if "command not found" in reply.lower():
        return None
    try:
        descriptor = _extract_json_of_type(reply, dict)
    except ValueError as exc:
        raise ValueError(f"Help for {command_id} did not return a JSON object") from exc
    actual = _command_id(descriptor)
    if not actual or actual.casefold() != command_id.casefold():
        raise ValueError(f"Help descriptor id mismatch for {command_id}")
    return descriptor


def discover_openvino_features(pipe: AudacityPipe) -> dict[str, dict[str, Any] | None]:
    """Discover only the bounded OpenVINO effects TASK-004 understands.

    This deliberately uses Audacity's side-effect-free Help command instead of
    GetInfo Type=Commands.  The latter instantiates/enumerates every installed
    effect and was unreliable on a plugin-heavy target while also doing far more
    work than the Product needs for capability evidence.
    """
    found: dict[str, dict[str, Any] | None] = {}
    for feature, candidate_ids in OPENVINO_FEATURE_COMMAND_IDS.items():
        descriptor = None
        for command_id in candidate_ids:
            descriptor = _help_descriptor(pipe, command_id)
            if descriptor is not None:
                break
        found[feature] = descriptor
    return found


def _tracks(pipe: AudacityPipe) -> list[dict[str, Any]]:
    value = _extract_json_of_type(pipe.command("GetInfo: Type=Tracks Format=JSON"), list)
    return [x for x in value if isinstance(x, dict)]


def _track_name(track: dict[str, Any]) -> str:
    for key in ("name", "Name", "track_name"):
        if isinstance(track.get(key), str):
            return track[key]
    return ""


def _find_stems(tracks: list[dict[str, Any]], mode: str) -> dict[str, int]:
    wanted = ["vocals", "instrumental"] if mode == "2_STEM" else ["drums", "bass", "other", "vocals"]
    result: dict[str, int] = {}
    for index, track in enumerate(tracks):
        normalized = _normalize(_track_name(track))
        for role in wanted:
            if role in normalized and role not in result:
                result[role] = index
    missing = sorted(set(wanted) - set(result))
    if missing:
        raise ValueError("cannot prove expected stem roles: " + ", ".join(missing))
    return result


def _ensure_empty_project(pipe: AudacityPipe) -> None:
    tracks = _tracks(pipe)
    if tracks:
        raise PermissionError("current Audacity project has existing tracks")


def _remove_all_tracks(pipe: AudacityPipe) -> None:
    try:
        pipe.command("SelectAll:")
        pipe.command("RemoveTracks:")
    except Exception:
        pass


def _import(pipe: AudacityPipe, path: Path) -> None:
    pipe.command(build_command("Import2", {"Filename": str(path)}))
    pipe.command("SelectAll:")


def _export(pipe: AudacityPipe, path: Path) -> None:
    pipe.command(build_command("Export2", {"Filename": str(path), "NumChannels": 2}))


def _report_capabilities(features: dict[str, dict[str, Any] | None], tracks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "connected": True,
        "current_track_count": len(tracks),
        "features": {
            key: {
                "available": descriptor is not None,
                "command_id": _command_id(descriptor) if descriptor else None,
                "descriptor": descriptor,
            }
            for key, descriptor in features.items()
        },
    }


def execute(
    request: dict[str, Any],
    *,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    operation = request.get("operation")
    mark = progress or (lambda _phase: None)
    mark("OPENING_PIPE")
    with AudacityPipe() as pipe:
        mark("PIPE_CONNECTED")
        mark("DISCOVERING_OPENVINO_COMMANDS")
        features = discover_openvino_features(pipe)
        mark("OPENVINO_COMMANDS_DISCOVERED")
        mark("DISCOVERING_TRACKS")
        tracks_before = _tracks(pipe)
        mark("TRACKS_DISCOVERED")
        capabilities = _report_capabilities(features, tracks_before)
        if operation == "CAPABILITY":
            return capabilities
        if tracks_before:
            return {"ok": False, "error_code": "ERR_AUDIO_RUNTIME_EXISTING_PROJECT_PROTECTED", "category": "SECURITY", "capabilities": capabilities}
        if operation == "NOISE_SUPPRESSION":
            descriptor = features["NOISE_SUPPRESSION"]
            if descriptor is None or not (command_id := _command_id(descriptor)):
                return {"ok": False, "error_code": "ERR_PROVIDER_OPENVINO_EFFECT_UNAVAILABLE", "category": "NOT_SUPPORTED", "feature": "NOISE_SUPPRESSION", "capabilities": capabilities}
            params = validate_effect_parameters(descriptor, dict(request.get("effect_parameters") or {}))
            parameter_strategy = "EXPLICIT_DISCOVERED_PARAMETERS" if params else "RUNTIME_DEFAULTS"
            mode = None
        elif operation == "MUSIC_SEPARATION":
            descriptor = features["MUSIC_SEPARATION"]
            if descriptor is None or not (command_id := _command_id(descriptor)):
                return {"ok": False, "error_code": "ERR_PROVIDER_OPENVINO_EFFECT_UNAVAILABLE", "category": "NOT_SUPPORTED", "feature": "MUSIC_SEPARATION", "capabilities": capabilities}
            mode = request.get("separation_mode")
            if mode not in {"2_STEM", "4_STEM"}:
                raise ValueError("separation_mode must be 2_STEM or 4_STEM")
            try:
                params, parameter_strategy = separation_parameters(descriptor, mode, dict(request.get("effect_parameters") or {}))
            except RuntimeError as exc:
                return {
                    "ok": False,
                    "error_code": "ERR_PROVIDER_OPENVINO_4_STEM_NOT_SCRIPTABLE",
                    "category": "NOT_SUPPORTED",
                    "message": str(exc),
                    "feature": "MUSIC_SEPARATION",
                    "capabilities": capabilities,
                }
        else:
            raise ValueError("unsupported worker operation")

        # Only after all side-effect-free capability/parameter validation passes
        # may the worker touch the empty Audacity project.
        source = Path(request["source_path"])
        output_dir = Path(request["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        if not source.is_file():
            raise FileNotFoundError("source_path is missing")
        try:
            mark("PREFLIGHT_VALIDATED")
            mark("IMPORTING_SOURCE")
            _import(pipe, source)
            mark("SOURCE_IMPORTED")
            if operation == "NOISE_SUPPRESSION":
                mark("APPLYING_NOISE_SUPPRESSION")
                pipe.command(build_command(command_id, params))
                mark("NOISE_SUPPRESSION_APPLIED")
                output = output_dir / "noise-suppressed.wav"
                mark("EXPORTING_NOISE_SUPPRESSION")
                _export(pipe, output)
                mark("NOISE_SUPPRESSION_EXPORTED")
                return {
                    "ok": True,
                    "operation": operation,
                    "outputs": [{"role": "noise_suppressed", "path": str(output)}],
                    "effect": {
                        "command_id": command_id,
                        "parameters": params,
                        "parameter_strategy": parameter_strategy,
                    },
                    "capabilities": capabilities,
                }

            assert operation == "MUSIC_SEPARATION" and mode in {"2_STEM", "4_STEM"}
            mark("APPLYING_MUSIC_SEPARATION")
            pipe.command(build_command(command_id, params))
            mark("MUSIC_SEPARATION_APPLIED")
            tracks_after = _tracks(pipe)
            mark("MUSIC_SEPARATION_TRACKS_DISCOVERED")
            stems = _find_stems(tracks_after, mode)
            outputs: list[dict[str, str]] = []
            for role, index in stems.items():
                pipe.command(build_command("SelectTracks", {"Track": index, "TrackCount": 1, "Mode": "Set"}))
                output = output_dir / f"stem-{role}.wav"
                mark("EXPORTING_MUSIC_SEPARATION_STEM")
                _export(pipe, output)
                outputs.append({"role": role, "path": str(output)})
            mark("MUSIC_SEPARATION_EXPORTED")
            return {
                "ok": True,
                "operation": operation,
                "outputs": outputs,
                "effect": {
                    "command_id": command_id,
                    "parameters": params,
                    "parameter_strategy": parameter_strategy,
                },
                "capabilities": capabilities,
                "stems": stems,
            }
        finally:
            mark("CLEANING_AUDACITY_PROJECT")
            _remove_all_tracks(pipe)
            mark("AUDACITY_PROJECT_CLEANED")



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--progress")
    args = parser.parse_args(argv)
    request_path = Path(args.request)
    report_path = Path(args.report)
    progress_path = Path(args.progress) if args.progress else None

    def mark(phase: str) -> None:
        if progress_path is None:
            return
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text(
            json.dumps({"phase": phase}, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        mark("REQUEST_LOADED")
        report = execute(request, progress=mark)
        mark("EXECUTION_COMPLETE")
        rc = 0 if report.get("ok", True) else 2
    except PermissionError as exc:
        report = {"ok": False, "error_code": "ERR_AUDIO_RUNTIME_EXISTING_PROJECT_PROTECTED", "category": "SECURITY", "message": str(exc)}
        rc = 2
    except FileNotFoundError as exc:
        report = {"ok": False, "error_code": "ERR_PROVIDER_AUDACITY_PIPE_UNAVAILABLE", "category": "EXTERNAL_DEPENDENCY", "message": str(exc)}
        rc = 3
    except Exception as exc:
        report = {"ok": False, "error_code": "ERR_PROVIDER_AUDACITY_OPENVINO_WORKER_FAILED", "category": "EXTERNAL_DEPENDENCY", "message": str(exc)}
        rc = 4
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
