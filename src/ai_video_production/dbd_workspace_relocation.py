"""TASK-050 R6 journaled Workspace relocation."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os, shutil, tempfile
from pathlib import Path
from uuid import uuid4

from .dbd_training_studio_foundation import WorkspaceDescriptor, WorkspaceRegistry, WorkspaceService


@dataclass(frozen=True, slots=True)
class WorkspaceMoveReceipt:
    migration_id: str
    workspace_id: str
    source_path: str
    destination_path: str
    file_count: int
    total_bytes: int
    source_preserved: bool
    journal_path: str


def _hash(path: Path) -> tuple[int, str]:
    h = hashlib.sha256(); size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            size += len(chunk); h.update(chunk)
    return size, h.hexdigest()


class WorkspaceRelocationService:
    def __init__(self, registry: WorkspaceRegistry | None = None) -> None:
        self.registry = registry or WorkspaceRegistry()
        self.workspace_service = WorkspaceService(self.registry)

    def relocate(self, workspace: WorkspaceDescriptor, destination_parent: str | Path) -> WorkspaceMoveReceipt:
        preflight = self.workspace_service.migration_preflight(workspace, destination_parent)
        if not preflight.can_migrate:
            raise ValueError(" / ".join(preflight.blockers))

        source = Path(preflight.source_path)
        destination = Path(preflight.destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        migration_id = "workspace-move-" + uuid4().hex
        temp_destination = destination.parent / f".{destination.name}.{migration_id}.tmp"

        journal_dir = source / "receipts" / "workspace-migrations"
        journal_dir.mkdir(parents=True, exist_ok=True)
        journal_path = journal_dir / f"{migration_id}.json"

        def write_journal(state: str, **extra) -> None:
            payload = {
                "schema_version":"1.0.0","migration_id":migration_id,
                "workspace_id":workspace.workspace_id,
                "source_path":str(source),"destination_path":str(destination),
                "state":state,**extra,
            }
            fd, raw = tempfile.mkstemp(prefix=".workspace-move.",suffix=".tmp",dir=journal_dir)
            os.close(fd); temp = Path(raw)
            try:
                temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                os.replace(temp,journal_path)
            finally:
                temp.unlink(missing_ok=True)

        write_journal("STARTED")
        try:
            shutil.copytree(source,temp_destination)
            write_journal("COPIED")

            journal_rel = journal_path.relative_to(source).as_posix()
            source_files = {
                p.relative_to(source).as_posix(): _hash(p)
                for p in source.rglob("*")
                if p.is_file() and p != journal_path and not p.is_symlink()
            }
            destination_files = {
                p.relative_to(temp_destination).as_posix(): _hash(p)
                for p in temp_destination.rglob("*")
                if p.is_file() and p.relative_to(temp_destination).as_posix()!=journal_rel and not p.is_symlink()
            }
            if source_files != destination_files:
                raise ValueError("移行先の検証に失敗しました。元ワークスペースは変更していません。")

            if destination.exists():
                if any(destination.iterdir()):
                    raise ValueError("移行先が空ではありません。")
                destination.rmdir()
            os.replace(temp_destination,destination)

            activated = self.workspace_service.open(destination)
            if activated.workspace_id != workspace.workspace_id:
                raise ValueError("Workspace ID verification failed after activation")

            final_payload = {
                "schema_version":"1.0.0","migration_id":migration_id,
                "workspace_id":workspace.workspace_id,
                "source_path":str(source),"destination_path":str(destination),
                "state":"ACTIVATED","source_preserved":True,
            }
            activated_journal = destination / "receipts" / "workspace-migrations" / journal_path.name
            activated_journal.write_text(json.dumps(final_payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            journal_path.write_text(json.dumps(final_payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

            return WorkspaceMoveReceipt(
                migration_id=migration_id, workspace_id=workspace.workspace_id,
                source_path=str(source), destination_path=str(destination),
                file_count=len(source_files),
                total_bytes=sum(size for size,_ in source_files.values()),
                source_preserved=True, journal_path=str(activated_journal),
            )
        except Exception:
            shutil.rmtree(temp_destination,ignore_errors=True)
            write_journal("FAILED")
            raise

    @staticmethod
    def delete_preserved_source(receipt: WorkspaceMoveReceipt, *, explicit_confirmation: str) -> None:
        if explicit_confirmation != receipt.workspace_id:
            raise ValueError("元ワークスペース削除にはWorkspace IDの明示確認が必要です。")
        source=Path(receipt.source_path); destination=Path(receipt.destination_path)
        if source==destination: raise ValueError("source and destination are identical")
        if not (destination/"workspace.json").is_file():
            raise ValueError("有効な移行先を確認できません。")
        shutil.rmtree(source)
