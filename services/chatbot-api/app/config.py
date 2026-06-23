"""Centralised settings loaded from environment variables / .env file.

At import time, settings are bootstrapped from env vars (backward compat).
At app startup, `init_settings()` is called to load from DB and override.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ── Metadata for every setting ────────────────────────────────────────────
# Used by the admin API for descriptions, UI grouping, and secret masking.

SETTING_METADATA: dict[str, dict] = {
    "llm_provider": {"description": "LLM provider (openai, azure)", "is_secret": False, "group": "LLM"},
    "llm_temperature": {"description": "Nhiệt độ sinh phản hồi (0-2)", "is_secret": False, "group": "LLM"},
    "llm_model": {"description": "Tên model chat (GPT, Claude...)", "is_secret": False, "group": "LLM"},
    "openai_api_key": {"description": "OpenAI API key", "is_secret": True, "group": "OpenAI", "depends_on": {"key": "llm_provider", "value": "openai"}},
    "openai_base_url": {"description": "OpenAI base URL (hỗ trợ compatible API)", "is_secret": False, "group": "OpenAI", "depends_on": {"key": "llm_provider", "value": "openai"}},
    "openai_embed_model": {"description": "OpenAI embedding model name", "is_secret": False, "group": "OpenAI", "depends_on": {"key": "llm_provider", "value": "openai"}},
    "azure_endpoint": {"description": "Azure OpenAI endpoint", "is_secret": False, "group": "Azure OpenAI", "depends_on": {"key": "llm_provider", "value": "azure"}},
    "azure_api_key": {"description": "Azure OpenAI API key", "is_secret": True, "group": "Azure OpenAI", "depends_on": {"key": "llm_provider", "value": "azure"}},
    "azure_api_version": {"description": "Azure API version", "is_secret": False, "group": "Azure OpenAI", "depends_on": {"key": "llm_provider", "value": "azure"}},
    "azure_chat_deployment": {"description": "Azure chat deployment name", "is_secret": False, "group": "Azure OpenAI", "depends_on": {"key": "llm_provider", "value": "azure"}},
    "azure_embed_deployment": {"description": "Azure embedding deployment name", "is_secret": False, "group": "Azure OpenAI", "depends_on": {"key": "llm_provider", "value": "azure"}},
    "embedding_provider": {"description": "Embedding provider (huggingface, openai, azure)", "is_secret": False, "group": "Embeddings"},
    "hf_embed_model": {"description": "HuggingFace embedding model name", "is_secret": False, "group": "Embeddings"},
    "data_dir": {"description": "Thư mục lưu dữ liệu runtime", "is_secret": False, "group": "Storage"},
    "default_tenant": {"description": "Tenant mặc định", "is_secret": False, "group": "Storage"},
    "storage_backend": {"description": "Loại lưu trữ (tinydb, mongo)", "is_secret": False, "group": "Storage"},
    "mongo_uri": {"description": "MongoDB connection URI", "is_secret": True, "group": "Storage"},
    "telegram_bot_token": {"description": "Telegram bot token", "is_secret": True, "group": "Telegram"},
    "telegram_default_tenant": {"description": "Tenant mặc định cho Telegram", "is_secret": False, "group": "Telegram"},
    "client_server_url": {"description": "URL của mock business API", "is_secret": False, "group": "Client Server"},
    "internal_api_key": {"description": "Internal API key giữa các service", "is_secret": True, "group": "Client Server"},
    "jwt_secret": {"description": "JWT secret key", "is_secret": True, "group": "Auth"},
    "jwt_expires_min": {"description": "JWT expiration (phút)", "is_secret": False, "group": "Auth"},
    "admin_user": {"description": "Tên đăng nhập admin", "is_secret": False, "group": "Auth"},
    "admin_password": {"description": "Mật khẩu admin", "is_secret": True, "group": "Auth"},
}


@dataclass
class Settings:
    llm_provider: str = "openai"
    llm_temperature: float = 0.2
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_api_version: str = "2024-10-21"
    azure_chat_deployment: str = "gpt-4o-mini"
    azure_embed_deployment: str = "text-embedding-3-small"
    embedding_provider: str = "huggingface"
    hf_embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    data_dir: Path = Path("./data").resolve()
    default_tenant: str = "demo-beauty"
    storage_backend: str = "tinydb"
    mongo_uri: str = "mongodb://localhost:27017/scchatbot"
    telegram_bot_token: str = ""
    telegram_default_tenant: str = "demo-beauty"
    client_server_url: str = "http://localhost:8001"
    internal_api_key: str = ""
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_min: int = 60
    admin_user: str = "admin"
    admin_password: str = "admin123"

    _repo: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._load_from_env()

    def _load_from_env(self):
        for key, meta in SETTING_METADATA.items():
            env_val = os.getenv(key.upper(), None)
            if env_val is not None:
                self._set_str(key, env_val)

    def _set_str(self, key: str, value: str):
        current = getattr(self, key, None)
        if isinstance(current, bool):
            setattr(self, key, value.lower() in ("1", "true", "yes"))
        elif isinstance(current, int):
            try:
                setattr(self, key, int(value))
            except (ValueError, TypeError):
                pass
        elif isinstance(current, float):
            try:
                setattr(self, key, float(value))
            except (ValueError, TypeError):
                pass
        elif isinstance(current, Path):
            setattr(self, key, Path(value).resolve())
        else:
            setattr(self, key, value)

    def _load_from_repo(self):
        if not self._repo:
            return
        for row in self._repo.list(scope="global"):
            key = row["key"]
            value = row["value"]
            if hasattr(self, key):
                self._set_str(key, value)

    def reload(self):
        if self._repo:
            self._load_from_repo()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def as_dict(self, mask_secrets: bool = True) -> dict:
        result = {}
        for key in SETTING_METADATA:
            val = getattr(self, key)
            meta = SETTING_METADATA[key]
            if mask_secrets and meta["is_secret"]:
                val = "*****"
            result[key] = val
        return result


# Module-level singleton – always importable, populated from env at import.
settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)


def init_settings(
    storage_backend: str | None = None,
    data_dir: str | Path | None = None,
    mongo_uri: str | None = None,
) -> None:
    """Call once during FastAPI lifespan startup to load settings from DB.

    Falls back to env if DB is empty (bootstrap).
    """
    from app.settings_repository import create_repository

    bs = (storage_backend or os.getenv("STORAGE_BACKEND", "tinydb")).lower()
    dd = Path(data_dir or os.getenv("DATA_DIR", "./data")).resolve()
    mu = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/scchatbot")
    dd.mkdir(parents=True, exist_ok=True)

    repo = create_repository(bs, data_dir=dd, mongo_uri=mu)
    settings._repo = repo

    rows = repo.list(scope="global")
    if rows:
        settings._load_from_repo()
        #settings._load_from_env()  # env vars always win over DB
    else:
        for key in SETTING_METADATA:
            val = getattr(settings, key)
            meta = SETTING_METADATA[key]
            repo.set(key, str(val), scope="global", description=meta["description"], is_secret=meta["is_secret"])

    settings.data_dir.mkdir(parents=True, exist_ok=True)
