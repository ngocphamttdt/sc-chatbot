"""Document metadata + upload handling for the admin panel.

Lifecycle:
- upload  -> save file under tenant uploads/, insert record (status=processing)
- ingest  -> chunk + index into FAISS, mark status=done (or failed)
- delete  -> remove record + uploaded file (FAISS chunks stay; orphaned)
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from app.knowledge import ingest as ingest_pipeline
from app.tenancy import TenantContext

log = logging.getLogger(__name__)


def _col():
    from app.core.mongo import documents
    return documents()


def list_documents(tenant: TenantContext) -> list[dict]:
    rows = list(_col().find({"tenant_id": tenant.tenant_id}, {"_id": 0}))
    rows.sort(key=lambda r: r.get("uploaded_at", 0), reverse=True)
    return rows


def get_document(tenant: TenantContext, doc_id: str) -> dict | None:
    return _col().find_one({"tenant_id": tenant.tenant_id, "id": doc_id}, {"_id": 0})


def save_upload(tenant: TenantContext, filename: str, content: bytes) -> dict:
    """Persist the file + a `processing` document record."""
    doc_id = uuid.uuid4().hex[:12]
    safe_name = Path(filename).name
    target = tenant.uploads_dir / f"{doc_id}_{safe_name}"
    target.write_bytes(content)

    record = {
        "tenant_id": tenant.tenant_id,
        "id": doc_id,
        "filename": safe_name,
        "path": str(target),
        "status": "processing",
        "chunk_count": 0,
        "uploaded_at": time.time(),
        "size_bytes": len(content),
        "error": None,
    }
    _col().insert_one(record)
    return {k: v for k, v in record.items() if k != "_id"}


def run_ingest(tenant: TenantContext, doc_id: str) -> None:
    """Sync ingestion. Call from a BackgroundTasks runner so HTTP returns fast."""
    rec = get_document(tenant, doc_id)
    if not rec:
        log.warning("ingest skipped — doc %s missing", doc_id)
        return

    try:
        n = ingest_pipeline.ingest_file(tenant, rec["path"])
        _col().update_one(
            {"tenant_id": tenant.tenant_id, "id": doc_id},
            {"$set": {"status": "done", "chunk_count": n, "error": None}},
        )
    except Exception as e:  # noqa: BLE001
        log.exception("ingest failed for doc %s", doc_id)
        _col().update_one(
            {"tenant_id": tenant.tenant_id, "id": doc_id},
            {"$set": {"status": "failed", "error": f"{type(e).__name__}: {e}"}},
        )


def delete_document(tenant: TenantContext, doc_id: str) -> bool:
    rec = get_document(tenant, doc_id)
    if not rec:
        return False
    _col().delete_one({"tenant_id": tenant.tenant_id, "id": doc_id})
    p = Path(rec.get("path", ""))
    if p.exists():
        try:
            p.unlink()
        except OSError:
            log.warning("could not delete file %s", p)
    return True
