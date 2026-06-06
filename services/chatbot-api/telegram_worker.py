"""Run the Telegram bot worker (long polling).

Standalone process that lives next to the FastAPI HTTP server.
Usage:
    cd services/chatbot-api
    python telegram_worker.py
"""
from app.integrations.telegram_bot import run_polling


if __name__ == "__main__":
    run_polling()
