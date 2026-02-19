"""Generate AI-powered topic comparisons across parties.

Usage:
    uv run python scripts/generate_comparisons.py
"""

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


def main():
    # Load topics from YAML config
    config_path = Path(settings.ELECTION_CONFIG)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    topics = config.get("topics", [])
    if not topics:
        logger.info("No topics defined in YAML config")
        return

    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        parties = (
            db.query(Party)
            .filter(Party.election_id == election.id, Party.program_text.isnot(None))
            .all()
        )

        for topic in topics:
            logger.info(f"Generating comparison for: {topic}")

            # Gather relevant text per party
            party_positions = {}
            for party in parties:
                relevant = _find_relevant_text(party.program_text, topic)
                if relevant:
                    party_positions[party.name] = relevant

            if not party_positions:
                logger.warning(f"  No relevant text found for '{topic}'")
                continue

            comparison = compare_topics(topic, party_positions)

            # Upsert
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
            logger.info(f"  Done: {len(comparison)} parties compared")

        logger.info(f"Generated comparisons for {len(topics)} topics")
    finally:
        db.close()


if __name__ == "__main__":
    main()
