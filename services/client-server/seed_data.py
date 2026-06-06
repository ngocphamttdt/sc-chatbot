"""Print a summary of the seed data loaded into the in-memory store.

Storage auto-bootstraps when the FastAPI app starts; this script is just a
convenience for verifying that the JSON files parse correctly.
"""
from __future__ import annotations

import json

from app import storage


def main() -> None:
    storage.bootstrap()
    summary = {
        "products": len(storage.all_products()),
        "spa_services": len(storage.all_spa_services()),
        "tours": len(storage.all_tours()),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
