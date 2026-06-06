"""Per-tenant FAISS vector store wrapper."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.llm import get_embeddings
from app.tenancy import TenantContext

_INDEX_NAME = "kb"


def _index_path(tenant: TenantContext) -> Path:
    return tenant.vector_dir


def load(tenant: TenantContext) -> FAISS | None:
    path = _index_path(tenant)
    if not (path / f"{_INDEX_NAME}.faiss").exists():
        return None
    return FAISS.load_local(
        str(path),
        get_embeddings(),
        index_name=_INDEX_NAME,
        allow_dangerous_deserialization=True,
    )


def save(tenant: TenantContext, store: FAISS) -> None:
    store.save_local(str(_index_path(tenant)), index_name=_INDEX_NAME)


def upsert(tenant: TenantContext, docs: Sequence[Document]) -> int:
    if not docs:
        return 0
    store = load(tenant)
    if store is None:
        store = FAISS.from_documents(list(docs), get_embeddings())
    else:
        store.add_documents(list(docs))
    save(tenant, store)
    return len(docs)


def search(tenant: TenantContext, query: str, k: int = 4) -> list[Document]:
    store = load(tenant)
    if store is None:
        return []
    return store.similarity_search(query, k=k)
