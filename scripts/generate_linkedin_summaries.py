"""Generate AI LinkedIn activity summaries for candidates with scraped posts.

For each candidate that has LinkedIn posts but no linkedin_summary yet,
summarizes their post activity in Dutch. Stores the result in candidate.linkedin_summary.

Run fetch_linkedin.py first to populate posts and structured profile fields.

Usage:
    uv run python scripts/generate_linkedin_summaries.py
    uv run python scripts/generate_linkedin_summaries.py --party BIJ1
    uv run python scripts/generate_linkedin_summaries.py --limit 5
    uv run python scripts/generate_linkedin_summaries.py --regenerate
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Candidate, Election, Party, SocialPost
from app.services.llm import summarize_linkedin_posts

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate AI LinkedIn activity summaries for candidates")
    parser.add_argument(
        "--party",
        default=None,
        help="Only generate summaries for this party (abbreviation or name, e.g. BIJ1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of candidates to process (0 = all)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate summaries even if linkedin_summary already exists",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        from sqlalchemy import exists

        query = (
            db.query(Candidate)
            .join(Party)
            .filter(
                Party.election_id == election.id,
                exists().where(
                    SocialPost.candidate_id == Candidate.id,
                    SocialPost.platform == "linkedin",
                ),
            )
        )

        if not args.regenerate:
            query = query.filter(Candidate.linkedin_summary.is_(None))

        if args.party:
            needle = args.party.lower()
            query = query.filter(
                Party.abbreviation.ilike(f"%{needle}%")
                | Party.name.ilike(f"%{needle}%")
            )

        candidates = query.order_by(Party.name, Candidate.position_on_list).all()

        if not candidates:
            logger.info("No candidates needing LinkedIn summaries.")
            return

        if args.limit:
            candidates = candidates[: args.limit]

        logger.info(f"Generating LinkedIn activity summaries for {len(candidates)} candidates")

        for i, candidate in enumerate(candidates, 1):
            logger.info(f"[{i}/{len(candidates)}] {candidate.name}")

            posts = (
                db.query(SocialPost)
                .filter(
                    SocialPost.candidate_id == candidate.id,
                    SocialPost.platform == "linkedin",
                )
                .order_by(SocialPost.posted_at.desc())
                .limit(25)
                .all()
            )

            post_texts = [p.text for p in posts if p.text and len(p.text) > 20]
            if not post_texts:
                logger.info(f"  No usable LinkedIn posts, skipping")
                continue

            logger.info(f"  {len(post_texts)} posts found")

            try:
                candidate.linkedin_summary = summarize_linkedin_posts(
                    candidate.name, post_texts
                )
                db.commit()
                logger.info(f"  Done ({len(candidate.linkedin_summary)} chars)")
            except Exception:
                logger.exception(f"  Summary generation failed for {candidate.name}")

        logger.info("LinkedIn activity summary generation complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
