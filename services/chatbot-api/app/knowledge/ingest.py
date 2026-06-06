"""Knowledge ingestion using LangChain document loaders.

Sources supported:
- Raw text  -> wrap in Document
- File      -> TextLoader (.md/.txt) hoặc BSHTMLLoader (.html)
- Folder    -> đệ quy qua tất cả file hợp lệ
- URL       -> WebBaseLoader

Pipeline: Loader -> RecursiveCharacterTextSplitter -> FAISS upsert.
"""
from __future__ import annotations

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


def _chunk_and_upsert(tenant: TenantContext, docs: Iterable[Document]) -> int:
    chunks = _SPLITTER.split_documents(list(docs))
    return vectorstore.upsert(tenant, chunks)


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
