from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import zipfile

_DANGEROUS = {
    "eval": re.compile(r"\beval\s*\("),
    "exec": re.compile(r"\bexec\s*\("),
    "shell_true": re.compile(r"shell\s*=\s*True"),
    "os_system": re.compile(r"\bos\.system\s*\("),
    "rmtree": re.compile(r"\bshutil\.rmtree\s*\("),
}
_PERSONAL_PATH = re.compile(r"(?:[A-Za-z]:\\Users\\[^\\\"\']+|/home/[^/\"\']+|/Users/[^/\"\']+)")

@dataclass(frozen=True, slots=True)
class ExternalSkillInspection:
    sha256: str
    member_count: int
    dangerous_findings: tuple[str, ...]
    personal_path_findings: tuple[str, ...]

    @property
    def safe_for_reference(self) -> bool:
        return not self.dangerous_findings


def inspect_zip(path: str | Path) -> ExternalSkillInspection:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    dangerous: set[str] = set()
    personal: set[str] = set()
    with zipfile.ZipFile(path) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        for info in members:
            if info.file_size > 2_000_000:
                continue
            if not info.filename.lower().endswith((".py", ".json", ".md", ".txt")):
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            for name, pattern in _DANGEROUS.items():
                if pattern.search(text):
                    dangerous.add(f"{name}:{info.filename}")
            if _PERSONAL_PATH.search(text):
                personal.add(info.filename)
    return ExternalSkillInspection(digest, len(members), tuple(sorted(dangerous)), tuple(sorted(personal)))
