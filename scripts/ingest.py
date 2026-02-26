"""Load election YAML config(s) + PDFs into the database.

Usage:
    # Ingest all elections in the directory:
    uv run python scripts/ingest.py

    # Ingest a single city:
    uv run python scripts/ingest.py --city amsterdam
    uv run python scripts/ingest.py --city den-haag

    # Custom directory:
    uv run python scripts/ingest.py --dir data/elections/gemeenteraad-2026

    # Ingest only one party within a city:
    uv run python scripts/ingest.py --city amsterdam --party BIJ1
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
from app.services.ingest import ingest_election, ingest_elections_dir

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Ingest election data into the database")
    parser.add_argument(
        "--dir",
        type=Path,
        default=settings.elections_dir_path,
        help=f"Directory containing election YAML files (default: {settings.ELECTIONS_DIR})",
    )
    parser.add_argument(
        "--city",
        default=None,
        help="Only ingest this city (e.g. amsterdam, den-haag, rotterdam)",
    )
    parser.add_argument(
        "--party",
        default=None,
        help="Only ingest this party (abbreviation or name, e.g. BIJ1). Requires --city.",
    )
    args = parser.parse_args()

    if args.party and not args.city:
        parser.error("--party requires --city")

    if not args.dir.exists():
        logging.error(f"Elections directory not found: {args.dir}")
        sys.exit(1)

    db = SessionLocal()
    try:
        if args.city and args.party:
            # Single-city + single-party mode: use the lower-level ingest_election directly
            config_path = args.dir / f"{args.city}.yml"
            if not config_path.exists():
                logging.error(f"Config file not found: {config_path}")
                sys.exit(1)
            election = ingest_election(db, config_path, party_filter=args.party)
            logging.info(f"Done! Election '{election.name}' (slug: '{election.slug}')")
        else:
            elections = ingest_elections_dir(db, args.dir, city_filter=args.city)
            logging.info(f"Done! Ingested {len(elections)} election(s).")
            for election in elections:
                logging.info(f"  {election.name} (slug: '{election.slug}')")
    finally:
        db.close()


if __name__ == "__main__":
    main()
