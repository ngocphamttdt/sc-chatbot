"""Chat-model + embeddings factory.

Supports Azure OpenAI, vanilla OpenAI (and OpenAI-compatible like Ollama),
and HuggingFace local embeddings. Chosen by env vars in config.py.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    if settings.llm_provider == "azure":
        from langchain_openai import AzureChatOpenAI

        if not settings.azure_endpoint or not settings.azure_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=azure but AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY missing."
            )
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            azure_deployment=settings.azure_chat_deployment,
            temperature=settings.llm_temperature,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    provider = settings.embedding_provider

    if provider == "azure":
        from langchain_openai import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            azure_deployment=settings.azure_embed_deployment,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embed_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    # Default: local HuggingFace - works offline, supports Vietnamese.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=settings.hf_embed_model)
