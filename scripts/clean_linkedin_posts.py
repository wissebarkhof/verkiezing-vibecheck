"""Remove bogus LinkedIn posts that contain cookie wall / login wall content.

When the LinkedIn scraper is redirected to the cookie consent page or the
login wall it sometimes stores that page's text as a post. This script
finds and deletes those rows, and clears the linkedin_summary for any
candidate whose remaining posts would be insufficient.

Usage:
    uv run python scripts/clean_linkedin_posts.py           # dry-run (shows what would be deleted)
    uv run python scripts/clean_linkedin_posts.py --delete  # actually delete
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Candidate, SocialPost

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Any LinkedIn post whose text contains one of these phrases is junk — it's the
# cookie consent page, the login wall, or other LinkedIn UI chrome.
_JUNK_PHRASES = [
    # Cookie consent page (Dutch)
    "LinkedIn respecteert uw privacy",
    "LinkedIn en derden gebruiken essentiële",
    "Selecteer Accepteren of Afwijzen",
    "Cookiebeleid van LinkedIn",
    "Akkoord en lid worden",
    "Lid worden van LinkedIn",
    # Auth / login wall
    "Log in to LinkedIn",
    "Aanmelden bij LinkedIn",
    "Wachtwoord (meer dan 6 tekens)",
    # Generic cookie-wall indicators
    "essentiële en niet-essentiële cookies",
    "Auteursrechtenbeleid",
    "Merkbeleid",
    "Instellingen voor gasten",
]


def is_junk(text: str) -> bool:
    return any(phrase in text for phrase in _JUNK_PHRASES)


def main():
    parser = argparse.ArgumentParser(description="Remove bogus LinkedIn posts from DB")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete the posts (default is dry-run)",
    )
    parser.add_argument(
        "--clear-summaries",
        action="store_true",
        default=True,
        help="Clear linkedin_summary for candidates whose post count drops to 0 (default: True)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        posts = (
            db.query(SocialPost)
            .filter(SocialPost.platform == "linkedin")
            .all()
        )

        junk_posts = [p for p in posts if is_junk(p.text)]
        logger.info(f"Found {len(junk_posts)} junk post(s) out of {len(posts)} LinkedIn post(s)")

        if not junk_posts:
            logger.info("Nothing to clean up.")
            return

        # Log what we found
        affected_candidate_ids = set()
        for post in junk_posts:
            affected_candidate_ids.add(post.candidate_id)
            preview = post.text[:80].replace("\n", " ")
            logger.info(f"  [{'DELETE' if args.delete else 'DRY-RUN'}] post id={post.id} "
                        f"candidate_id={post.candidate_id}: {preview!r}…")

        if not args.delete:
            logger.info(
                f"\nDry run complete — {len(junk_posts)} post(s) would be deleted. "
                "Re-run with --delete to apply."
            )
            return

        # Delete junk posts
        for post in junk_posts:
            db.delete(post)
        db.commit()
        logger.info(f"Deleted {len(junk_posts)} junk post(s)")

        # Optionally clear summaries for candidates with no remaining posts
        if args.clear_summaries:
            for candidate_id in affected_candidate_ids:
                remaining = (
                    db.query(SocialPost)
                    .filter(
                        SocialPost.candidate_id == candidate_id,
                        SocialPost.platform == "linkedin",
                    )
                    .count()
                )
                if remaining == 0:
                    candidate = db.query(Candidate).get(candidate_id)
                    if candidate and candidate.linkedin_summary:
                        logger.info(
                            f"  Clearing linkedin_summary for {candidate.name} "
                            f"(candidate_id={candidate_id}, no posts remain)"
                        )
                        candidate.linkedin_summary = None
            db.commit()
            logger.info("Summary cleanup done")

    finally:
        db.close()


if __name__ == "__main__":
    main()
