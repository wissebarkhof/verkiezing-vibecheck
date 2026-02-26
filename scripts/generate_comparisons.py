"""Generate AI-powered topic comparisons across parties.

Usage:
    # All elections:
    uv run python scripts/generate_comparisons.py

    # Single city:
    uv run python scripts/generate_comparisons.py --city amsterdam
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.database import SessionLocal
from app.models import Election, Party, TopicComparison
from app.services.llm import compare_topics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _find_relevant_text(program_text: str, topic: str, max_chars: int = 3000) -> str:
    """Extract text most relevant to a topic from a program.

    Simple approach: search for paragraphs containing topic keywords.
    Falls back to first N chars if no match found.
    """
    if not program_text:
        return ""

    keywords = topic.lower().split()
    paragraphs = program_text.split("\n\n")
    relevant = []
    total_len = 0

    for para in paragraphs:
        para_lower = para.lower()
        if any(kw in para_lower for kw in keywords):
            relevant.append(para)
            total_len += len(para)
            if total_len >= max_chars:
                break

    if relevant:
        return "\n\n".join(relevant)[:max_chars]

    # Fallback: return beginning of program
    return program_text[:max_chars]


def _process_election(db, election: Election, yaml_path: Path) -> None:
    """Generate comparisons for a single election."""
    if not yaml_path.exists():
        logger.warning(f"YAML not found for {election.city}: {yaml_path}")
        return

    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    topics = config.get("topics", [])
    if not topics:
        logger.info(f"  No topics defined for {election.city}")
        return

    parties = (
        db.query(Party)
        .filter(Party.election_id == election.id, Party.program_text.isnot(None))
        .all()
    )

    for topic in topics:
        logger.info(f"  Generating comparison for: {topic}")

        party_positions = {}
        for party in parties:
            relevant = _find_relevant_text(party.program_text, topic)
            if relevant:
                party_positions[party.name] = relevant

        if not party_positions:
            logger.warning(f"    No relevant text found for '{topic}'")
            continue

        comparison = compare_topics(topic, party_positions)

        existing = (
            db.query(TopicComparison)
            .filter(
                TopicComparison.election_id == election.id,
                TopicComparison.topic_name == topic,
            )
            .first()
        )
        if existing:
            existing.comparison_json = comparison
        else:
            tc = TopicComparison(
                election_id=election.id,
                topic_name=topic,
                comparison_json=comparison,
            )
            db.add(tc)

        db.commit()
        logger.info(f"    Done: {len(comparison)} parties compared")

    logger.info(f"  Generated comparisons for {len(topics)} topics")


def main():
    parser = argparse.ArgumentParser(description="Generate AI topic comparisons")
    parser.add_argument(
        "--city",
        default=None,
        help="Only process this city (e.g. amsterdam, den-haag)",
    )
    args = parser.parse_args()

    elections_dir = settings.elections_dir_path

    db = SessionLocal()
    try:
        elections = db.query(Election).order_by(Election.city).all()
        if not elections:
            logger.error("No elections found. Run ingestion first.")
            return

        if args.city:
            elections = [e for e in elections if e.city.lower() == args.city.lower()]
            if not elections:
                logger.error(f"No election found for city '{args.city}'")
                return

        for election in elections:
            logger.info(f"\n=== {election.name} ===")
            yaml_path = elections_dir / f"{election.city}.yml"
            _process_election(db, election, yaml_path)

    finally:
        db.close()


if __name__ == "__main__":
    main()
