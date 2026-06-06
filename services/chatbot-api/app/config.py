"""Centralised settings loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str            # "azure" | "openai"
    llm_temperature: float

    # OpenAI / OpenAI-compatible
    openai_api_key: str
    openai_base_url: str
    llm_model: str
    openai_embed_model: str

    # Azure OpenAI
    azure_endpoint: str
    azure_api_key: str
    azure_api_version: str
    azure_chat_deployment: str
    azure_embed_deployment: str

    # Embeddings
    embedding_provider: str      # "huggingface" | "openai" | "azure"
    hf_embed_model: str

    # Storage
    data_dir: Path
    default_tenant: str

    # Telegram bot (polling worker)
    telegram_bot_token: str
    telegram_default_tenant: str

    # client-server (mock business REST API)
    client_server_url: str
    internal_api_key: str

    # web-admin (JWT login)
    jwt_secret: str
    jwt_expires_min: int
    admin_user: str
    admin_password: str

    # Chat history backend
    storage_backend: str          # "tinydb" | "mongo"
    mongo_uri: str


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


settings = Settings(
    llm_provider=_get("LLM_PROVIDER", "openai").lower(),
    llm_temperature=float(_get("LLM_TEMPERATURE", "0.2")),

    openai_api_key=_get("OPENAI_API_KEY"),
    openai_base_url=_get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    llm_model=_get("LLM_MODEL", "gpt-4o-mini"),
    openai_embed_model=_get("OPENAI_EMBED_MODEL", "text-embedding-3-small"),

    azure_endpoint=_get("AZURE_OPENAI_ENDPOINT"),
    azure_api_key=_get("AZURE_OPENAI_API_KEY"),
    azure_api_version=_get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    azure_chat_deployment=_get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
    azure_embed_deployment=_get("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small"),

    embedding_provider=_get("EMBEDDING_PROVIDER", "huggingface").lower(),
    hf_embed_model=_get(
        "HF_EMBED_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ),

    data_dir=Path(_get("DATA_DIR", "./data")).resolve(),
    default_tenant=_get("DEFAULT_TENANT", "demo-beauty"),

    telegram_bot_token=_get("TELEGRAM_BOT_TOKEN"),
    telegram_default_tenant=_get("TELEGRAM_DEFAULT_TENANT", "demo-beauty"),

    client_server_url=_get("CLIENT_SERVER_URL", "http://localhost:8001"),
    internal_api_key=_get("INTERNAL_API_KEY", ""),

    jwt_secret=_get("JWT_SECRET", "dev-secret-change-me"),
    jwt_expires_min=int(_get("JWT_EXPIRES_MIN", "60")),
    admin_user=_get("ADMIN_USER", "admin"),
    admin_password=_get("ADMIN_PASSWORD", "admin123"),

    storage_backend=_get("STORAGE_BACKEND", "tinydb").lower(),
    mongo_uri=_get("MONGO_URI", "mongodb://localhost:27017/scchatbot"),
)

settings.data_dir.mkdir(parents=True, exist_ok=True)
