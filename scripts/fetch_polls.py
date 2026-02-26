"""Fetch and store polling data from configured sources.

Reads polling_sources from each election YAML in ELECTIONS_DIR, scrapes each
enabled source, upserts Poll + PollResult rows, and updates Party.polled_seats /
Party.poll_updated_at from the newest poll.

Usage:
    # All elections:
    uv run python scripts/fetch_polls.py

    # Single city:
    uv run python scripts/fetch_polls.py --city amsterdam
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from ruamel.yaml import YAML

from app.config import settings
from app.database import SessionLocal
from app.models import Election
from app.services.polls import fetch_and_store_polls

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fetch polling data from configured sources")
    parser.add_argument(
        "--city",
        default=None,
        help="Only fetch polls for this city (e.g. amsterdam, den-haag)",
    )
    args = parser.parse_args()

    elections_dir = settings.elections_dir_path
    if not elections_dir.exists():
        logger.error(f"Elections directory not found: {elections_dir}")
        sys.exit(1)

    yamls = sorted(elections_dir.glob("*.yml"))
    if args.city:
        yamls = [y for y in yamls if y.stem.lower() == args.city.lower()]
    if not yamls:
        logger.warning(f"No YAML files found in {elections_dir}")
        return

    yaml_parser = YAML()
    db = SessionLocal()
    try:
        for yaml_path in yamls:
            with open(yaml_path) as f:
                config = yaml_parser.load(f)

            sources = config.get("polling_sources", [])
            enabled = [s for s in sources if s.get("enabled", True)]
            if not enabled:
                logger.info(f"{yaml_path.name}: no enabled polling sources, skipping")
                continue

            election_city = config.get("election", {}).get("city", yaml_path.stem)
            election = db.query(Election).filter(Election.city == election_city).first()
            if not election:
                logger.warning(f"{yaml_path.name}: no election in DB for city '{election_city}', skipping (run ingest first)")
                continue

            logger.info(f"\n=== {election.name} ({len(enabled)} source(s)) ===")
            polls = fetch_and_store_polls(db, election, config)

            logger.info(f"Stored/updated {len(polls)} poll(s)")
            for poll in polls:
                logger.info(
                    f"  [{poll.id}] {poll.source_name} | "
                    f"field_end={poll.field_end} | "
                    f"results={len(poll.results)}"
                )
    finally:
        db.close()


if __name__ == "__main__":
    main()
