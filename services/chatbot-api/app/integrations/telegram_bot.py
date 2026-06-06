"""Telegram bot adapter (long polling).

Receives Telegram updates and forwards them to the in-process chat agent.
No HTTP hop — runs alongside the FastAPI server as a separate worker.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import settings
from app.core import agent
from app.tenancy import get_tenant

log = logging.getLogger(__name__)

TELEGRAM_MSG_LIMIT = 4096


def _session_id(update: Update) -> str:
    user = update.effective_user
    return f"tg-{user.id}" if user else "tg-anonymous"


def _split(text: str, limit: int = TELEGRAM_MSG_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


async def _start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    tenant = get_tenant(settings.telegram_default_tenant)
    await update.message.reply_text(
        f"Xin chào! Em là trợ lý AI của {tenant.name}. "
        f"Anh/chị cần em hỗ trợ gì ạ?"
    )


async def _on_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if not text:
        return

    try:
        tenant = get_tenant(settings.telegram_default_tenant)
    except KeyError:
        await update.message.reply_text(
            "Hệ thống chưa được cấu hình tenant. Vui lòng liên hệ quản trị viên."
        )
        return

    try:
        await update.get_bot().send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except TelegramError:
        log.warning("send_chat_action timed out for chat_id=%s (bỏ qua)", chat_id)

    try:
        result = agent.chat(tenant, _session_id(update), text)
        reply = result.get("reply") or "Xin lỗi, em chưa rõ ý ạ."
    except Exception:
        log.exception("agent.chat failed for chat_id=%s", chat_id)
        reply = "Hệ thống đang bận, vui lòng thử lại sau ạ."

    for chunk in _split(reply):
        await update.message.reply_text(chunk)


def build_application() -> Application:
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is empty. Set it in services/chatbot-api/.env "
            "before running telegram_worker.py."
        )

    app = (
        ApplicationBuilder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))
    return app


def run_polling() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log.info(
        "Starting Telegram bot (polling) for tenant=%s",
        settings.telegram_default_tenant,
    )
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)
