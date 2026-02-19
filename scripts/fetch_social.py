"""Fetch Bluesky posts for candidates and generate AI summaries.

For each candidate in the DB that has a bluesky_handle:
  1. Fetches recent posts via the public Bluesky API (no auth required).
  2. Upserts each post as a SocialPost row (uri is the upsert key — safe to re-run).
  3. Generates a Dutch AI summary from post texts and saves to candidate.social_summary.

Usage:
    uv run python scripts/fetch_social.py
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Candidate, Election, Party, SocialPost
from app.services.llm import summarize_social_posts

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BLUESKY_API = "https://public.api.bsky.app/xrpc"
MAX_POSTS = 25


def fetch_author_feed(handle: str) -> list[dict]:
    """Return raw feed items from the Bluesky API, or [] on any error."""
    actor = handle.lstrip("@")
    url = f"{BLUESKY_API}/app.bsky.feed.getAuthorFeed"
    params = {"actor": actor, "limit": MAX_POSTS, "filter": "posts_no_replies"}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json().get("feed", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"  Account not found: {handle}")
        else:
            logger.warning(f"  HTTP {e.response.status_code} for {handle}")
        return []
    except httpx.RequestError as e:
        logger.warning(f"  Request error for {handle}: {e}")
        return []


def _parse_embed(post: dict) -> dict | None:
    """Extract the resolved embed object from a post, or None if absent.

    The API returns a resolved 'embed' on post (not post.record.embed).
    We store it as-is; the template uses embed['$type'] to render correctly.
    Quoted-post embeds are stored but rendered as a simple link-out.
    """
    return post.get("embed")


def upsert_posts(db, candidate: Candidate, feed_items: list[dict]) -> list[str]:
    """Upsert SocialPost rows for each feed item. Returns list of post texts."""
    texts = []
    for item in feed_items:
        post = item.get("post", {})
        record = post.get("record", {})

        uri = post.get("uri", "")
        text = record.get("text", "").strip()
        if not uri or not text:
            continue

        # Parse ISO timestamp from the post record
        created_at_str = record.get("createdAt", "")
        try:
            posted_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            posted_at = datetime.utcnow()

        embed = _parse_embed(post)

        existing = db.query(SocialPost).filter(SocialPost.uri == uri).first()
        if existing:
            # Refresh engagement counts and embed on re-run
            existing.like_count = post.get("likeCount", 0)
            existing.reply_count = post.get("replyCount", 0)
            existing.repost_count = post.get("repostCount", 0)
            existing.embed_json = embed
        else:
            db.add(SocialPost(
                candidate_id=candidate.id,
                uri=uri,
                text=text,
                posted_at=posted_at,
                like_count=post.get("likeCount", 0),
                reply_count=post.get("replyCount", 0),
                repost_count=post.get("repostCount", 0),
                embed_json=embed,
            ))

        texts.append(text)

    db.commit()
    return texts


def main():
    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        candidates = (
            db.query(Candidate)
            .join(Party)
            .filter(
                Party.election_id == election.id,
                Candidate.bluesky_handle.isnot(None),
            )
            .order_by(Party.name, Candidate.position_on_list)
            .all()
        )

        if not candidates:
            logger.info("No candidates with Bluesky handles found in the database.")
            logger.info("Add 'bluesky' fields to candidates in your election YAML and re-run ingestion.")
            return

        logger.info(f"Processing {len(candidates)} candidates with Bluesky handles")

        for candidate in candidates:
            logger.info(f"{candidate.name} ({candidate.bluesky_handle})")
            feed_items = fetch_author_feed(candidate.bluesky_handle)

            if not feed_items:
                logger.info("  No posts found, skipping")
                continue

            logger.info(f"  Fetched {len(feed_items)} posts, upserting...")
            texts = upsert_posts(db, candidate, feed_items)
            logger.info(f"  Upserted {len(texts)} posts")

            if texts:
                logger.info("  Generating AI summary...")
                try:
                    candidate.social_summary = summarize_social_posts(candidate.name, texts)
                    db.commit()
                    logger.info("  Done")
                except Exception:
                    logger.exception(f"  Summary generation failed for {candidate.name}, skipping")

            time.sleep(0.5)  # be polite to the API

        logger.info("Social media fetch complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
