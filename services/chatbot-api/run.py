"""Entry point: `python run.py` starts the chatbot HTTP server.

For development. In production deploy behind uvicorn/gunicorn + a reverse proxy.
"""
from __future__ import annotations

import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    uvicorn.run("app.api.server:app", host="0.0.0.0", port=8000, reload=False)
