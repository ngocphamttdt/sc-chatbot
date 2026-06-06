"""Entry point for the client-server (mock business API).

Usage:
    cd services/client-server
    python run.py
"""
from __future__ import annotations

import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
