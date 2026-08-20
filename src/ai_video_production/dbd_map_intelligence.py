"""DbD Map Intelligence canonical-orientation and training-readiness contracts."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

from .serialization import utc_now_iso


def _bounded(value: str, name: str, maximum: int = 256) -> str:
    value = str(value).strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{name} must be bounded non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class MapFloor:
    floor_id: str
    name: str
    level_index: int
    image_path: str = ""

    def __post_init__(self) -> None:
        _bounded(self.floor_id, "floor_id")
        _bounded(self.name, "floor name")
        if not isinstance(self.level_index, int):
            raise ValueError("level_index must be int")


@dataclass(frozen=True, slots=True)
class MapRegion:
    region_id: str
    name: str
    polygon_uv: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.region_id, "region_id")
        _bounded(self.name, "region name")
        for u, v in self.polygon_uv:
            if not 0.0 <= float(u) <= 1.0 or not 0.0 <= float(v) <= 1.0:
                raise ValueError("region points must be normalized 0..1")


@dataclass(frozen=True, slots=True)
class MapLandmark:
    landmark_id: str
    name: str
    floor_id: str
    u: float
    v: float
    landmark_type: str = "OTHER"
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.landmark_id, "landmark_id")
        _bounded(self.name, "landmark name")
        _bounded(self.floor_id, "floor_id")
        if not 0.0 <= float(self.u) <= 1.0 or not 0.0 <= float(self.v) <= 1.0:
            raise ValueError("landmark coordinate must be normalized 0..1")


@dataclass(frozen=True, slots=True)
class MapRecord:
    map_id: str
    map_name: str
    image_path: str = ""
    realm_name: str = ""
    offering_name: str = ""
    features: str = ""
    unique_objects: str = ""
    favorability: str = ""
    pallet_text: str = ""
    area_m2: int | None = None
    size_class: str = ""
    enabled: bool = True
    rotation_deg: int = 0
    orientation_locked: bool = False
    orientation_basis: str = "USER_CANONICAL"
    orientation_note: str = ""
    floors: tuple[MapFloor, ...] = ()
    regions: tuple[MapRegion, ...] = ()
    landmarks: tuple[MapLandmark, ...] = ()
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _bounded(self.map_id, "map_id")
        _bounded(self.map_name, "map_name")
        if self.rotation_deg not in {0, 90, 180, 270}:
            raise ValueError("rotation_deg must be 0/90/180/270")
        if self.area_m2 is not None and self.area_m2 < 0:
            raise ValueError("area_m2 must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id,
            "map_name": self.map_name,
            "image_path": self.image_path,
            "realm_name": self.realm_name,
            "offering_name": self.offering_name,
            "features": self.features,
            "unique_objects": self.unique_objects,
            "favorability": self.favorability,
            "pallet_text": self.pallet_text,
            "area_m2": self.area_m2,
            "size_class": self.size_class,
            "enabled": self.enabled,
            "orientation": {
                "rotation_deg": self.rotation_deg,
                "locked": self.orientation_locked,
                "basis": self.orientation_basis,
                "note": self.orientation_note,
            },
            "floors": [vars_no_slots(x) for x in self.floors],
            "regions": [
                {"region_id": x.region_id, "name": x.name, "polygon_uv": [list(point) for point in x.polygon_uv]}
                for x in self.regions
            ],
            "landmarks": [vars_no_slots(x) for x in self.landmarks],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MapRecord":
        orientation = dict(payload.get("orientation", {}))
        return cls(
            map_id=str(payload["map_id"]),
            map_name=str(payload["map_name"]),
            image_path=str(payload.get("image_path", "")),
            realm_name=str(payload.get("realm_name", "")),
            offering_name=str(payload.get("offering_name", "")),
            features=str(payload.get("features", "")),
            unique_objects=str(payload.get("unique_objects", "")),
            favorability=str(payload.get("favorability", "")),
            pallet_text=str(payload.get("pallet_text", "")),
            area_m2=(None if payload.get("area_m2") in {None, ""} else int(payload["area_m2"])),
            size_class=str(payload.get("size_class", "")),
            enabled=bool(payload.get("enabled", True)),
            rotation_deg=int(orientation.get("rotation_deg", 0)),
            orientation_locked=bool(orientation.get("locked", False)),
            orientation_basis=str(orientation.get("basis", "USER_CANONICAL")),
            orientation_note=str(orientation.get("note", "")),
            floors=tuple(MapFloor(**x) for x in payload.get("floors", ())),
            regions=tuple(MapRegion(region_id=x["region_id"], name=x["name"], polygon_uv=tuple(tuple(p) for p in x.get("polygon_uv", ()))) for x in payload.get("regions", ())),
            landmarks=tuple(MapLandmark(**x) for x in payload.get("landmarks", ())),
            updated_at=str(payload.get("updated_at", utc_now_iso())),
        )


def vars_no_slots(value: object) -> dict[str, Any]:
    return {name: getattr(value, name) for name in value.__dataclass_fields__}  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class MapTrainingCapture:
    capture_id: str
    session_id: str
    map_id: str
    floor_id: str
    view_role: str
    source_frame: int
    frame_image: str
    u: float
    v: float
    heading_deg: float | None = None
    region_id: str = ""
    landmark_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.view_role not in {"SURVIVOR_1", "SURVIVOR_2", "SURVIVOR_3", "SURVIVOR_4", "KILLER"}:
            raise ValueError("unsupported view_role")
        if self.source_frame < 0:
            raise ValueError("source_frame must be non-negative")
        if not 0 <= self.u <= 1 or not 0 <= self.v <= 1:
            raise ValueError("u/v must be normalized 0..1")
        if self.heading_deg is not None and not 0 <= self.heading_deg < 360:
            raise ValueError("heading_deg must be in 0..<360")


@dataclass(frozen=True, slots=True)
class MapLocationCandidate:
    floor_id: str
    u: float
    v: float
    confidence_milli: int

    def __post_init__(self) -> None:
        _bounded(self.floor_id, "floor_id")
        if not 0.0 <= float(self.u) <= 1.0 or not 0.0 <= float(self.v) <= 1.0:
            raise ValueError("candidate u/v must be normalized 0..1")
        if not 0 <= int(self.confidence_milli) <= 1000:
            raise ValueError("candidate confidence_milli must be 0..1000")


@dataclass(frozen=True, slots=True)
class MapLocalizationResult:
    map_id: str
    floor_id: str
    u: float
    v: float
    view_role: str
    confidence_milli: int
    heading_deg: float | None = None
    region_id: str = ""
    nearest_landmark_id: str = ""
    candidates: tuple[MapLocationCandidate, ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.map_id, "map_id")
        _bounded(self.floor_id, "floor_id")
        if self.view_role not in {"SURVIVOR_1", "SURVIVOR_2", "SURVIVOR_3", "SURVIVOR_4", "KILLER"}:
            raise ValueError("unsupported view_role")
        if not 0.0 <= float(self.u) <= 1.0 or not 0.0 <= float(self.v) <= 1.0:
            raise ValueError("localization u/v must be normalized 0..1")
        if not 0 <= int(self.confidence_milli) <= 1000:
            raise ValueError("confidence_milli must be 0..1000")
        if self.heading_deg is not None and not 0.0 <= float(self.heading_deg) < 360.0:
            raise ValueError("heading_deg must be in 0..<360")


class MapTrainingDatasetStore:
    """Workspace-local ground-truth capture store for future cross-view localization training."""
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(())

    def _write(self, rows: Iterable[MapTrainingCapture]) -> None:
        payload = {"schema_version": "1.0.0", "captures": [vars_no_slots(x) for x in rows]}
        fd, raw = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        os.close(fd); temp = Path(raw)
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def list(self) -> tuple[MapTrainingCapture, ...]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return tuple(MapTrainingCapture(**row) for row in payload.get("captures", ()))

    def append(self, capture: MapTrainingCapture) -> bool:
        rows = list(self.list())
        if any(x.capture_id == capture.capture_id for x in rows):
            return False
        rows.append(capture); self._write(rows); return True


class MapIntelligenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(())

    def _write(self, rows: Iterable[MapRecord]) -> None:
        payload = {"schema_version": "1.0.0", "maps": [x.to_dict() for x in sorted(rows, key=lambda r: r.map_name)]}
        fd, raw = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        os.close(fd); temp = Path(raw)
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def list(self) -> tuple[MapRecord, ...]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return tuple(MapRecord.from_dict(x) for x in payload.get("maps", ()))

    def upsert(self, record: MapRecord) -> MapRecord:
        rows = {x.map_id: x for x in self.list()}; rows[record.map_id] = record; self._write(rows.values()); return record

    def get(self, map_id: str) -> MapRecord:
        for row in self.list():
            if row.map_id == map_id: return row
        raise KeyError(map_id)

    def set_orientation(self, map_id: str, rotation_deg: int, *, note: str = "") -> MapRecord:
        row = self.get(map_id)
        updated = replace(row, rotation_deg=rotation_deg, orientation_locked=True, orientation_note=note, updated_at=utc_now_iso())
        return self.upsert(updated)

    def unlock_orientation(self, map_id: str) -> MapRecord:
        row = self.get(map_id)
        return self.upsert(replace(row, orientation_locked=False, updated_at=utc_now_iso()))

    def disable(self, map_id: str) -> MapRecord:
        row = self.get(map_id)
        return self.upsert(replace(row, enabled=False, updated_at=utc_now_iso()))


__all__ = [
    "MapFloor", "MapRegion", "MapLandmark", "MapRecord", "MapTrainingCapture",
    "MapLocationCandidate", "MapLocalizationResult", "MapTrainingDatasetStore", "MapIntelligenceStore",
]
