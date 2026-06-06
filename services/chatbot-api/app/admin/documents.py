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

from tinydb import Query, TinyDB

from app.knowledge import ingest as ingest_pipeline
from app.tenancy import TenantContext

log = logging.getLogger(__name__)


def list_documents(tenant: TenantContext) -> list[dict]:
    with TinyDB(tenant.documents_db) as db:
        rows = db.all()
    rows.sort(key=lambda r: r.get("uploaded_at", 0), reverse=True)
    return rows


def get_document(tenant: TenantContext, doc_id: str) -> dict | None:
    Q = Query()
    with TinyDB(tenant.documents_db) as db:
        return db.get(Q.id == doc_id)


def save_upload(tenant: TenantContext, filename: str, content: bytes) -> dict:
    """Persist the file + a `processing` document record."""
    doc_id = uuid.uuid4().hex[:12]
    safe_name = Path(filename).name  # strip path components
    target = tenant.uploads_dir / f"{doc_id}_{safe_name}"
    target.write_bytes(content)

    record = {
        "id": doc_id,
        "filename": safe_name,
        "path": str(target),
        "status": "processing",
        "chunk_count": 0,
        "uploaded_at": time.time(),
        "size_bytes": len(content),
        "error": None,
    }
    with TinyDB(tenant.documents_db) as db:
        db.insert(record)
    return record


def run_ingest(tenant: TenantContext, doc_id: str) -> None:
    """Sync ingestion. Call from a BackgroundTasks runner so HTTP returns fast."""
    Q = Query()
    with TinyDB(tenant.documents_db) as db:
        rec = db.get(Q.id == doc_id)
    if not rec:
        log.warning("ingest skipped — doc %s missing", doc_id)
        return

    try:
        n = ingest_pipeline.ingest_file(tenant, rec["path"])
        with TinyDB(tenant.documents_db) as db:
            db.update(
                {"status": "done", "chunk_count": n, "error": None},
                Q.id == doc_id,
            )
    except Exception as e:  # noqa: BLE001
        log.exception("ingest failed for doc %s", doc_id)
        with TinyDB(tenant.documents_db) as db:
            db.update(
                {"status": "failed", "error": f"{type(e).__name__}: {e}"},
                Q.id == doc_id,
            )


def delete_document(tenant: TenantContext, doc_id: str) -> bool:
    Q = Query()
    with TinyDB(tenant.documents_db) as db:
        rec = db.get(Q.id == doc_id)
        if not rec:
            return False
        db.remove(Q.id == doc_id)
    p = Path(rec.get("path", ""))
    if p.exists():
        try:
            p.unlink()
        except OSError:
            log.warning("could not delete file %s", p)
    return True
