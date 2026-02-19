"""Generate AI summaries of each party's submitted motions and amendments.

For each party that has submitted motions, builds a text overview of their
motion titles, types, and results, then calls the LLM to generate a Dutch
summary of their priorities. Stores the result in party.motion_summary.

Usage:
    uv run python scripts/generate_motion_summaries.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import Election, Motion, MotionParty, Party
from app.services.llm import summarize_party_motions

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        parties = (
            db.query(Party)
            .filter(Party.election_id == election.id)
            .order_by(Party.name)
            .all()
        )

        for party in parties:
            # Get motions submitted by this party
            motions = (
                db.query(Motion)
                .join(MotionParty)
                .filter(
                    MotionParty.party_id == party.id,
                    Motion.election_id == election.id,
                )
                .order_by(Motion.submission_date.desc())
                .all()
            )

            if not motions:
                logger.info(f"{party.name}: no motions found, skipping")
                continue

            logger.info(f"{party.name}: {len(motions)} motions found")

            # Build overview text
            lines = []
            for m in motions:
                result_str = f" ({m.result})" if m.result else ""
                lines.append(f"- [{m.motion_type or '?'}] {m.title}{result_str}")

            motions_text = "\n".join(lines)

            try:
                logger.info(f"  Generating summary...")
                party.motion_summary = summarize_party_motions(party.name, motions_text)
                db.commit()
                logger.info(f"  Done")
            except Exception:
                logger.exception(f"  Summary generation failed for {party.name}")

        logger.info("Motion summary generation complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
