"""Generate embeddings for all document chunks and store in pgvector.

Usage:
    uv run python scripts/generate_embeddings.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.services.embedding import embed_all_documents

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    db = SessionLocal()
    try:
        count = embed_all_documents(db)
        logging.info(f"Embedded {count} documents total")
    finally:
        db.close()


if __name__ == "__main__":
    main()
