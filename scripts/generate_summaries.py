"""Generate AI summaries for all party programs.

Usage:
    uv run python scripts/generate_summaries.py
    uv run python scripts/generate_summaries.py --party BIJ1
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Party
from app.services.llm import summarize_program

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate AI summaries for party programs")
    parser.add_argument(
        "--party",
        default=None,
        help="Only generate summary for this party (abbreviation or name, e.g. BIJ1)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(Party).filter(Party.program_text.isnot(None))
        if args.party:
            needle = args.party.lower()
            q = q.filter(
                Party.abbreviation.ilike(needle) | (Party.name.ilike(needle))
            )
        parties = q.all()
        if not parties:
            logger.info("No parties with program text found. Run ingestion first.")
            return

        for party in parties:
            logger.info(f"Generating summary for {party.name}...")
            summary = summarize_program(party.name, party.program_text)
            party.description = summary
            db.commit()
            logger.info(f"  Done ({len(summary)} chars)")

        logger.info(f"Generated summaries for {len(parties)} parties")
    finally:
        db.close()


if __name__ == "__main__":
    main()
