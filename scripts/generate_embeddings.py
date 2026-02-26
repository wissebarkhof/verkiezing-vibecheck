"""Generate embeddings for all document chunks and store in pgvector.

Usage:
    uv run python scripts/generate_embeddings.py
    uv run python scripts/generate_embeddings.py --party BIJ1
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Election, Party
from app.services.embedding import embed_all_documents

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate pgvector embeddings for document chunks")
    parser.add_argument(
        "--party",
        default=None,
        help="Only embed documents for this party (abbreviation or name, e.g. BIJ1)",
    )
    parser.add_argument(
        "--city",
        default=None,
        help="Only process this city (e.g. amsterdam)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        party_id = None
        election_id = None
        if args.party:
            needle = args.party.lower()
            party = db.query(Party).filter(
                Party.abbreviation.ilike(needle) | (Party.name.ilike(needle))
            ).first()
            if not party:
                logger.error(f"Party '{args.party}' not found in database")
                sys.exit(1)
            party_id = party.id
            logger.info(f"Filtering to party: {party.name}")
        elif args.city:
            election = db.query(Election).filter(Election.city == args.city.lower()).first()
            if not election:
                logger.error(f"No election found for city '{args.city}'")
                sys.exit(1)
            election_id = election.id
            logger.info(f"Filtering to city: {args.city} (election_id={election_id})")

        count = embed_all_documents(db, party_id=party_id, election_id=election_id)
        logger.info(f"Embedded {count} documents total")
    finally:
        db.close()


if __name__ == "__main__":
    main()
