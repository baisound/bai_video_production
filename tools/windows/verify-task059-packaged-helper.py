"""Verify the TASK-059 staged, bundled and embedded helper identities."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys


PACKAGED_HELPER_FILENAME = "BAI Video Production Key Helper.exe"
GENERATED_IDENTITY_FILENAME = "_bvp_task059_packaged_helper_identity.py"
DIGEST_ATTRIBUTE = "EXPECTED_PACKAGED_HELPER_SHA256"
MAX_HELPER_BYTES = 128 * 1024 * 1024
MAX_IDENTITY_BYTES = 256


def _sha256(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("helper identity is invalid")
    stream = None
    try:
        stream = path.open("rb")
        before = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size < 1
            or before.st_size > MAX_HELPER_BYTES
        ):
            raise ValueError("helper identity is invalid")
        digest = hashlib.sha256()
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        for coordinate in ("st_dev", "st_ino", "st_size", "st_mtime_ns"):
            if getattr(before, coordinate) != getattr(after, coordinate):
                raise ValueError("helper identity is unstable")
        return "sha256:" + digest.hexdigest()
    except OSError:
        raise ValueError("helper identity is invalid") from None
    finally:
        if stream is not None:
            stream.close()


def verify_packaged_helper(
    staged_helper: Path,
    bundled_helper: Path,
    generated_identity: Path,
) -> str:
    for helper in (staged_helper, bundled_helper):
        if (
            not helper.is_absolute()
            or helper.name.casefold() != PACKAGED_HELPER_FILENAME.casefold()
        ):
            raise ValueError("helper path identity is invalid")
    if (
        not generated_identity.is_absolute()
        or generated_identity.name != GENERATED_IDENTITY_FILENAME
        or generated_identity.is_symlink()
        or not generated_identity.is_file()
        or generated_identity.stat().st_size > MAX_IDENTITY_BYTES
    ):
        raise ValueError("generated identity is invalid")
    staged_digest = _sha256(staged_helper)
    bundled_digest = _sha256(bundled_helper)
    if staged_digest != bundled_digest:
        raise ValueError("helper identities do not match")
    expected_source = f'{DIGEST_ATTRIBUTE} = "{staged_digest}"\n'
    try:
        actual_source = generated_identity.read_text(encoding="ascii")
    except (OSError, UnicodeError):
        raise ValueError("generated identity is invalid") from None
    if actual_source != expected_source:
        raise ValueError("embedded helper identity does not match")
    return staged_digest


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 3:
        return 64
    try:
        verify_packaged_helper(*(Path(value) for value in arguments))
    except Exception as exc:
        del exc
        print("[ERROR] TASK-059 packaged helper verification failed.")
        return 2
    print("[PASS] TASK-059 packaged helper identities match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
