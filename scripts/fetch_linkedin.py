"""Fetch LinkedIn profile data and posts for candidates.

For each candidate in the DB that has a linkedin_url (and no linkedin_headline yet):
  1. Extracts the LinkedIn username from the URL.
  2. Fetches the public LinkedIn profile page via Selenium (real browser).
  3. Extracts structured profile data (headline, experiences, education) and saves to DB.
  4. Fetches recent posts from the activity page and stores as SocialPost rows.

Run generate_linkedin_summaries.py separately to generate AI summaries from stored data.

Usage:
    uv run python scripts/fetch_linkedin.py
"""

import argparse
import hashlib
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Candidate, Election, Party, SocialPost

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRAPE_DELAY = 5  # seconds between profile fetches


def _extract_username(linkedin_url: str) -> str | None:
    """Extract the username/slug from a LinkedIn profile URL."""
    parsed = urlparse(linkedin_url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "in":
        return parts[1]
    return parts[-1] if parts else None


def create_driver():
    """Create a Selenium Chrome driver."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver


def fetch_posts_selenium(driver, username: str) -> list[dict]:
    """Fetch recent posts from a LinkedIn activity page.

    Returns a list of dicts with keys: text, posted_at, uri.
    """
    from selenium.webdriver.common.by import By

    url = f"https://www.linkedin.com/in/{username}/recent-activity/all/"
    driver.get(url)
    time.sleep(5)

    # Scroll down a couple of times to load more posts
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    posts = []
    seen_texts = set()

    # Try to find post containers via data-urn attribute or feed update elements
    post_elements = driver.find_elements(
        By.CSS_SELECTOR,
        "div.feed-shared-update-v2, div[data-urn], article"
    )

    if not post_elements:
        # Fallback: parse the page text for post-like content
        logger.info("  No post elements found via selectors, trying text extraction")
        return _extract_posts_from_text(driver, username)

    for el in post_elements:
        try:
            # Extract post text
            text_el = None
            for selector in [
                "div.feed-shared-update-v2__description",
                "div.update-components-text",
                "span.break-words",
                "div.feed-shared-text",
            ]:
                try:
                    text_el = el.find_element(By.CSS_SELECTOR, selector)
                    if text_el and text_el.text.strip():
                        break
                except Exception:
                    continue

            if not text_el:
                # Try getting all visible text from the element
                full_text = el.text.strip()
                if not full_text or len(full_text) < 20:
                    continue
                # Take only the first portion (before engagement metrics)
                text = _clean_post_text(full_text)
            else:
                text = text_el.text.strip()

            if not text or len(text) < 10:
                continue

            # Deduplicate
            text_key = text[:100]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            # Try to get the post URL from a timestamp link
            post_url = None
            try:
                time_link = el.find_element(
                    By.CSS_SELECTOR,
                    "a.app-aware-link[href*='/activity/'], "
                    "a[href*='/detail/'], "
                    "a.update-components-actor__sub-description-link"
                )
                post_url = time_link.get_attribute("href")
            except Exception:
                pass

            # Generate a stable URI if we couldn't find a link
            if not post_url:
                text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
                post_url = f"linkedin://{username}/post/{text_hash}"

            posts.append({
                "text": text,
                "posted_at": datetime.utcnow(),  # LinkedIn doesn't expose exact timestamps easily
                "uri": post_url,
                "like_count": 0,
                "reply_count": 0,
                "repost_count": 0,
            })
        except Exception:
            continue

    logger.info(f"  Found {len(posts)} posts from activity page")
    return posts[:25]  # cap at 25 like Bluesky


def _clean_post_text(full_text: str) -> str:
    """Extract just the post content from a feed element's full text.

    LinkedIn feed elements include the author name, headline, timestamp,
    engagement counts, etc. Try to strip those out.
    """
    lines = full_text.split("\n")
    content_lines = []
    skip_patterns = [
        r"^\d+$",  # pure numbers (like/comment counts)
        r"^\d+ (likes?|comments?|reactions?|reposts?)",
        r"^Like$", r"^Comment$", r"^Repost$", r"^Send$", r"^Share$",
        r"^\d+[dwmj]\s*$",  # relative timestamps like "3d", "1w", "2m"
        r"^(Vind ik leuk|Reageren|Opnieuw posten|Verzenden)$",  # Dutch
        r"^(Like|Comment|Repost|Send)$",
        r"^\.\.\.(meer|more)$",
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.match(p, stripped, re.IGNORECASE) for p in skip_patterns):
            continue
        content_lines.append(stripped)

    # The actual post text is usually the longest contiguous block
    # Skip first 2-3 lines (author name, headline, timestamp)
    if len(content_lines) > 3:
        content_lines = content_lines[2:]

    return "\n".join(content_lines).strip()


def _extract_posts_from_text(driver, username: str) -> list[dict]:
    """Fallback: extract posts from the full page text when selectors fail."""
    from selenium.webdriver.common.by import By

    page_text = driver.find_element(By.TAG_NAME, "body").text
    if not page_text or len(page_text) < 100:
        return []

    # Split by common post separators in the text
    # LinkedIn activity pages show posts separated by engagement action text
    posts = []
    # Look for blocks of text between "Like Comment Repost Send" patterns
    blocks = re.split(
        r"(?:Vind ik leuk|Like)\s+(?:Reageren|Comment)\s+(?:Opnieuw posten|Repost)\s+(?:Verzenden|Send)",
        page_text,
    )

    for block in blocks:
        block = block.strip()
        if len(block) < 30:
            continue
        # Clean up: remove leading author info lines
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        # Skip the last few lines (often engagement counts)
        text = "\n".join(lines[:-2] if len(lines) > 3 else lines).strip()
        if len(text) < 20:
            continue

        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        posts.append({
            "text": text[:2000],  # cap text length
            "posted_at": datetime.utcnow(),
            "uri": f"linkedin://{username}/post/{text_hash}",
            "like_count": 0,
            "reply_count": 0,
            "repost_count": 0,
        })

    logger.info(f"  Found {len(posts)} posts via text extraction fallback")
    return posts[:25]


def upsert_linkedin_posts(db, candidate, posts: list[dict]) -> list[str]:
    """Upsert LinkedIn posts as SocialPost rows. Returns list of post texts."""
    texts = []
    for post_data in posts:
        uri = post_data["uri"]
        text = post_data["text"]

        existing = db.query(SocialPost).filter(SocialPost.uri == uri).first()
        if existing:
            existing.text = text
            existing.like_count = post_data.get("like_count", 0)
            existing.reply_count = post_data.get("reply_count", 0)
            existing.repost_count = post_data.get("repost_count", 0)
        else:
            db.add(SocialPost(
                candidate_id=candidate.id,
                platform="linkedin",
                uri=uri,
                text=text,
                posted_at=post_data["posted_at"],
                like_count=post_data.get("like_count", 0),
                reply_count=post_data.get("reply_count", 0),
                repost_count=post_data.get("repost_count", 0),
            ))
        texts.append(text)

    db.commit()
    return texts


def login_and_scrape(driver, candidates):
    """Log in to LinkedIn and scrape profiles and posts."""
    from selenium.webdriver.common.by import By

    # Navigate to LinkedIn login
    driver.get("https://www.linkedin.com/login")
    input("Log into LinkedIn in the browser, then press Enter here...")

    # Verify login succeeded
    time.sleep(2)
    if "feed" not in driver.current_url and "mynetwork" not in driver.current_url:
        # Try navigating to feed
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)

    logger.info("Logged in, starting profile scraping...")

    db = SessionLocal()
    scraped = 0
    posts_total = 0

    try:
        for i, candidate in enumerate(candidates, 1):
            username = _extract_username(candidate.linkedin_url)
            if not username:
                continue

            logger.info(f"[{i}/{len(candidates)}] {candidate.name} ({username})")

            # Re-attach the detached candidate object to this session
            db_candidate = db.merge(candidate)

            # Fetch profile data and persist structured fields
            profile = fetch_profile_selenium(driver, username)
            if not profile or not any(profile.get(k) for k in ["headline", "bio", "experiences"]):
                logger.info(f"  No useful profile data, skipping")
            else:
                scraped += 1
                logger.info(f"  Scraped: {profile.get('headline', '(no headline)')}")

                db_candidate.linkedin_headline = profile.get("headline") or None
                db_candidate.linkedin_current_position = profile.get("current_position") or None
                db_candidate.linkedin_current_company = profile.get("current_company") or None
                db_candidate.linkedin_experiences = profile.get("experiences") or None
                db_candidate.linkedin_education = profile.get("schools") or None
                if profile.get("photo_url") and not db_candidate.photo_url:
                    db_candidate.photo_url = profile["photo_url"]
                    logger.info(f"  Photo saved")
                db.commit()
                logger.info(f"  Structured profile fields saved")

            # Fetch posts from activity page
            time.sleep(SCRAPE_DELAY)
            logger.info(f"  Fetching posts...")
            posts = fetch_posts_selenium(driver, username)
            if posts:
                texts = upsert_linkedin_posts(db, db_candidate, posts)
                posts_total += len(texts)
                logger.info(f"  Upserted {len(texts)} LinkedIn posts")

            time.sleep(SCRAPE_DELAY)

        logger.info(
            f"\nLinkedIn fetch complete: scraped {scraped}, posts {posts_total}"
        )
    finally:
        db.close()


def fetch_profile_selenium(driver, username: str) -> dict | None:
    """Fetch a LinkedIn profile page and extract structured data from page text."""
    from selenium.webdriver.common.by import By

    url = f"https://www.linkedin.com/in/{username}/"
    driver.get(url)
    time.sleep(5)  # wait for page to fully load

    page_text = driver.find_element(By.TAG_NAME, "body").text
    page_title = driver.title

    # Extract profile photo URL — try progressively broader selectors
    photo_url = None
    photo_selectors = [
        # Modern LinkedIn (2024+)
        "img.pv-top-card-profile-picture__image--show",
        "img.profile-photo-edit__preview",
        "div.pv-top-card__photo-wrapper img",
        "button.pv-top-card__photo img",
        # Older class names still seen in some views
        "img.pv-top-card-profile-picture__image",
        "img.evi-image.ember-view",
        # Generic: any img inside the top-card section
        "section.artdeco-card img[src*='profile-displayphoto']",
        "section.artdeco-card img[src*='media.licdn.com']",
        # Broadest fallback: first non-icon img with a licdn.com media URL
        "img[src*='media.licdn.com/dms/image']",
    ]
    for selector in photo_selectors:
        try:
            photo_el = driver.find_element(By.CSS_SELECTOR, selector)
            src = photo_el.get_attribute("src") or ""
            if src and "ghost" not in src and "static" not in src:
                photo_url = src
                logger.info(f"  Photo found via selector: {selector}")
                break
        except Exception:
            continue

    if not photo_url:
        # Log candidate img srcs to help identify the right selector next time
        try:
            all_imgs = driver.find_elements(By.TAG_NAME, "img")
            linkedin_srcs = [
                i.get_attribute("src") for i in all_imgs
                if (i.get_attribute("src") or "").startswith("https://media.licdn.com")
            ]
            if linkedin_srcs:
                logger.info(f"  No photo selector matched. Candidate srcs: {linkedin_srcs[:3]}")
            else:
                logger.info(f"  No photo found and no media.licdn.com img srcs on page")
        except Exception:
            pass

    if not page_text or len(page_text) < 100:
        logger.warning(f"    Page too short ({len(page_text)} chars)")
        return None

    # Extract name from page title ("Name | LinkedIn")
    name = page_title.replace(" | LinkedIn", "").strip() if page_title else ""

    # Parse the page text into lines
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]

    # Find the name line, then headline is typically the next meaningful line after it
    headline = ""
    name_idx = None
    for i, line in enumerate(lines):
        if name and line == name:
            name_idx = i
            break
        # Also try partial match for names with suffixes like "· 3de"
        if name and name in line:
            name_idx = i
            break

    if name_idx is not None:
        # Skip "· Xde" connection degree line, find the headline
        for j in range(name_idx + 1, min(name_idx + 5, len(lines))):
            line = lines[j]
            # Skip connection degree indicators and location
            if line.startswith("·") or line in ("Contactgegevens",):
                continue
            if len(line) > 5 and not line.endswith("connecties"):
                headline = line
                break

    # Extract sections from page text
    bio = _extract_section(page_text, "Over") or _extract_section(page_text, "About") or ""

    exp_text = _extract_section(page_text, "Ervaring") or _extract_section(page_text, "Experience") or ""
    experiences = _parse_experience_text(exp_text) if exp_text else []

    edu_text = _extract_section(page_text, "Opleiding") or _extract_section(page_text, "Education") or ""
    schools = _parse_education_text(edu_text) if edu_text else []

    current_position = experiences[0].get("title") if experiences else None
    current_company = experiences[0].get("company") if experiences else None

    return {
        "name": name,
        "headline": headline,
        "bio": bio,
        "current_position": current_position,
        "current_company": current_company,
        "experiences": experiences,
        "schools": schools,
        "skills": [],
        "photo_url": photo_url,
    }


def _extract_section(page_text: str, section_name: str) -> str | None:
    """Extract a section from the page text between section headers."""
    # LinkedIn page text has section names as standalone lines
    lines = page_text.split("\n")
    in_section = False
    section_lines = []
    section_headers = [
        "Experience", "Education", "Skills", "About", "Activity",
        "Licenses & certifications", "Volunteer", "Recommendations",
        "Courses", "Honors", "Projects", "Publications", "Languages",
        # Dutch equivalents
        "Ervaring", "Opleiding", "Vaardigheden", "Over", "Activiteit",
        "Licenties en certificeringen", "Vrijwilligerswerk", "Aanbevelingen",
        "Cursussen", "Onderscheidingen", "Projecten", "Publicaties", "Talen",
        # Navigation items that signal end of profile content
        "Bericht", "Volgen", "Meer", "Contactgegevens",
    ]

    for line in lines:
        stripped = line.strip()
        if stripped == section_name:
            in_section = True
            continue
        if in_section:
            if stripped in section_headers and stripped != section_name:
                break
            section_lines.append(stripped)

    return "\n".join(section_lines).strip() if section_lines else None


def _parse_experience_text(text: str) -> list[dict]:
    """Parse experience entries from section text."""
    entries = []
    lines = [l for l in text.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Skip common non-content lines
        if line in ("Show all experiences", "Show all", "") or line.startswith("Show "):
            i += 1
            continue
        # A company/title entry typically starts with a non-date line
        if not re.match(r"^\d{4}|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", line):
            entry = {"title": line, "company": "", "description": ""}
            # Next lines might be company, dates, description
            if i + 1 < len(lines):
                entry["company"] = lines[i + 1].strip()
            entries.append(entry)
        i += 1
    return entries[:5]  # top 5


def _parse_education_text(text: str) -> list[dict]:
    """Parse education entries from section text."""
    entries = []
    lines = [l for l in text.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ("Show all education", "Show all", "") or line.startswith("Show "):
            i += 1
            continue
        if not re.match(r"^\d{4}", line):
            entry = {"school": line, "degree": "", "field": ""}
            if i + 1 < len(lines):
                entry["degree"] = lines[i + 1].strip()
            entries.append(entry)
        i += 1
    return entries[:3]  # top 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of candidates to process (0 = all)",
    )
    parser.add_argument(
        "--party",
        type=str,
        default=None,
        help="Filter by party name or abbreviation (case-insensitive substring match)",
    )
    parser.add_argument(
        "--skip-fetched",
        action="store_true",
        default=False,
        help=(
            "Also skip candidates that already have LinkedIn posts stored "
            "(useful when adding new accounts without re-fetching existing ones)"
        ),
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        from sqlalchemy import exists

        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        query = (
            db.query(Candidate)
            .join(Party)
            .filter(
                Party.election_id == election.id,
                Candidate.linkedin_url.isnot(None),
            )
        )

        if args.skip_fetched:
            query = query.filter(
                Candidate.linkedin_summary.is_(None),
                ~exists().where(
                    SocialPost.candidate_id == Candidate.id,
                    SocialPost.platform == "linkedin",
                ),
            )
            logger.info("--skip-fetched: skipping candidates that already have a summary or LinkedIn posts")

        if args.party:
            party_filter = args.party.lower()
            query = query.filter(
                (Party.name.ilike(f"%{party_filter}%"))
                | (Party.abbreviation.ilike(f"%{party_filter}%"))
            )

        candidates = query.order_by(Party.name, Candidate.position_on_list).all()

        if not candidates:
            logger.info("No candidates needing LinkedIn data fetch.")
            return

        if args.limit:
            candidates = candidates[: args.limit]

        logger.info(f"Processing {len(candidates)} candidates")
    finally:
        db.close()

    driver = create_driver()
    try:
        login_and_scrape(driver, candidates)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
