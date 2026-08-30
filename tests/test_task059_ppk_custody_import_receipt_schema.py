from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ai_video_production.owner_signing_key_ppk_custody_import import (
    PpkCustodyImportReceipt,
)
from ai_video_production.serialization import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]


def test_receipt_schema_mirror_and_body_free_record_validation() -> None:
    canonical = (
        ROOT / "schemas" / "owner-signing-key-ppk-custody-import-receipt.schema.json"
    )
    mirror = (
        ROOT
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / canonical.name
    )
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    coordinate = sha256_bytes(b"task059-schema-coordinate")
    receipt = PpkCustodyImportReceipt(
        receipt_id="task059-schema-receipt",
        ready_sha256=coordinate,
        confirmation_sha256=coordinate,
        custody_receipt_sha256=coordinate,
        preflight_sha256=coordinate,
        ppk_file_sha256=coordinate,
        signer_key_id_sha256=coordinate,
        owner_scope_sha256=coordinate,
        destination_path_sha256=coordinate,
        imported_at_epoch_ms=1_777_200_000_000,
    ).to_dict()
    Draft202012Validator(schema).validate(receipt)
    assert "private_key_seed_b64" not in receipt
    assert "public_key_b64" not in receipt
    assert receipt["private_key_export_authorized"] is False
    assert receipt["signing_authorized"] is False
