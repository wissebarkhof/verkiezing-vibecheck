"""Fetch and store polling data from configured sources.

Reads polling_sources from the election YAML config, scrapes each enabled
source, upserts Poll + PollResult rows, and updates Party.polled_seats /
Party.poll_updated_at from the newest poll.

Usage:
    uv run python scripts/fetch_polls.py
    uv run python scripts/fetch_polls.py --config data/elections/amsterdam-2026.yml
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from ruamel.yaml import YAML

from app.database import SessionLocal
from app.models import Election
from app.services.polls import fetch_and_store_polls

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fetch polling data from configured sources")
    parser.add_argument(
        "--config",
        default=os.environ.get("ELECTION_CONFIG", "data/elections/amsterdam-2026.yml"),
        help="Path to election YAML config",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    yaml = YAML()
    with open(config_path) as f:
        config = yaml.load(f)

    sources = config.get("polling_sources", [])
    if not sources:
        logger.warning("No polling_sources found in config. Nothing to do.")
        return

    enabled = [s for s in sources if s.get("enabled", True)]
    logger.info(f"Found {len(enabled)} enabled polling source(s) in {config_path.name}")

    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found in the database. Run ingestion first.")
            sys.exit(1)

        logger.info(f"Election: {election.name}")

        polls = fetch_and_store_polls(db, election, config)

        logger.info(f"\nDone. Stored/updated {len(polls)} poll(s).")
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
