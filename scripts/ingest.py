"""Load election YAML config + PDFs into the database.

Usage:
    uv run python scripts/ingest.py
    uv run python scripts/ingest.py --config data/elections/amsterdam-2026.yml
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.database import SessionLocal
from app.services.ingest import ingest_election

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Ingest election data into the database")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(settings.ELECTION_CONFIG),
        help="Path to election YAML config file",
    )
    parser.add_argument(
        "--party",
        default=None,
        help="Only ingest this party (abbreviation or name, e.g. BIJ1)",
    )
    args = parser.parse_args()

    if not args.config.exists():
        logging.error(f"Config file not found: {args.config}")
        sys.exit(1)

    db = SessionLocal()
    try:
        election = ingest_election(db, args.config, party_filter=args.party)
        logging.info(f"Done! Election '{election.name}' loaded with slug '{election.slug}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
