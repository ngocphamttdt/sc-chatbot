"""Knowledge ingestion using LangChain document loaders.

Sources supported:
- Raw text  -> wrap in Document
- File      -> TextLoader (.md/.txt) hoặc BSHTMLLoader (.html)
- JSON product catalog -> detect by 'sku' field, index into FAISS
- Folder    -> đệ quy qua tất cả file hợp lệ
- URL       -> WebBaseLoader

Pipeline: Loader -> RecursiveCharacterTextSplitter -> FAISS upsert.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import (
    BSHTMLLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    WebBaseLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.knowledge import vectorstore
from app.tenancy import TenantContext

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=["\n\n", "\n", "。", ". ", " ", ""],
)

_TEXT_EXTS = {".md", ".txt"}
_HTML_EXTS = {".html", ".htm"}
_PDF_EXTS = {".pdf"}
_DOCX_EXTS = {".docx"}
_JSON_EXTS = {".json"}


def _chunk_and_upsert(tenant: TenantContext, docs: Iterable[Document]) -> int:
    chunks = _SPLITTER.split_documents(list(docs))
    return vectorstore.upsert(tenant, chunks)


def is_product_catalog(path: str | Path) -> bool:
    """Return True if path is a JSON array of objects with a 'sku' field."""
    p = Path(path)
    if p.suffix.lower() not in _JSON_EXTS:
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return isinstance(data, list) and len(data) > 0 and "sku" in data[0]
    except Exception:
        return False


def ingest_product_catalog(tenant: TenantContext, path: str | Path) -> int:
    """Parse a product catalog JSON and index each product into FAISS."""
    products = json.loads(Path(path).read_text(encoding="utf-8"))
    n = 0
    for p in products:
        text = (
            f"Sản phẩm {p['sku']} - {p['name']}\n"
            f"Danh mục: {p.get('category', '')}\n"
            f"Giá: {p.get('price')}đ\n"
            f"Mô tả: {p.get('description', '')}\n"
            + (f"Công dụng / hướng dẫn: {p['usage']}\n" if p.get("usage") else "")
            + (f"Chống chỉ định: {p['contraindication']}\n" if p.get("contraindication") else "")
        )
        n += ingest_text(tenant, text, source=f"product:{p['sku']}")
    return n


def ingest_text(tenant: TenantContext, text: str, source: str) -> int:
    doc = Document(page_content=text, metadata={"source": source})
    return _chunk_and_upsert(tenant, [doc])


def ingest_file(tenant: TenantContext, path: str | Path) -> int:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in _HTML_EXTS:
        loader = BSHTMLLoader(str(p))
    elif suffix in _TEXT_EXTS:
        loader = TextLoader(str(p), encoding="utf-8")
    elif suffix in _PDF_EXTS:
        loader = PyPDFLoader(str(p))
    elif suffix in _DOCX_EXTS:
        loader = Docx2txtLoader(str(p))
    elif suffix in _JSON_EXTS:
        if is_product_catalog(p):
            return ingest_product_catalog(tenant, p)
        return ingest_text(tenant, p.read_text(encoding="utf-8"), source=str(p))
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")
    return _chunk_and_upsert(tenant, loader.load())


def ingest_folder(tenant: TenantContext, folder: str | Path) -> int:
    docs: list[Document] = []
    for p in Path(folder).rglob("*"):
        suffix = p.suffix.lower()
        if suffix in _TEXT_EXTS:
            docs.extend(TextLoader(str(p), encoding="utf-8").load())
        elif suffix in _HTML_EXTS:
            docs.extend(BSHTMLLoader(str(p)).load())
    return _chunk_and_upsert(tenant, docs)


def ingest_url(tenant: TenantContext, url: str) -> int:
    loader = WebBaseLoader(
        url,
        requests_kwargs={"headers": {"User-Agent": "sc-chatbot/0.1"}, "timeout": 15},
    )
    return _chunk_and_upsert(tenant, loader.load())
