"""Search for candidate LinkedIn profile URLs and write them into the election YAML.

For each candidate without a 'linkedin' field, searches the Brave Search API for
their name + party + city on linkedin.com/in/. High-confidence matches (>= 0.75
fuzzy similarity between the URL slug and the candidate name) are written back to
the YAML automatically. Possible matches (0.55–0.75) are printed for manual review.

Uses ruamel.yaml for round-trip parsing so existing YAML formatting is preserved.

Requires BRAVE_API_KEY env var (free tier: https://brave.com/search/api/).

Usage:
    uv run python scripts/hydrate_linkedin_urls.py
    uv run python scripts/hydrate_linkedin_urls.py --dry-run
"""

import argparse
import logging
import os
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import httpx
from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

AUTO_WRITE_THRESHOLD = 0.75  # write URL to YAML automatically
SUGGEST_THRESHOLD = 0.55     # print as possible match for manual review
REQUEST_DELAY = 1.0          # Brave API free tier allows 1 req/sec

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.lower().split())


def _slug_to_name(slug: str) -> str:
    """Convert a LinkedIn URL slug like 'rutger-groot-wassink-1234ab' to a name string."""
    # Remove trailing ID-like suffixes (hex or alphanumeric chunks at the end)
    slug = re.sub(r"-[0-9a-f]{4,}$", "", slug)
    return slug.replace("-", " ")


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _extract_linkedin_urls(results: list[dict]) -> list[str]:
    """Extract linkedin.com/in/ profile URLs from Brave API results."""
    pattern = re.compile(r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([a-zA-Z0-9\-]+)')
    seen = set()
    urls = []
    for result in results:
        url = result.get("url", "")
        m = pattern.search(url)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            urls.append(f"https://www.linkedin.com/in/{m.group(1)}")
    return urls


def search_linkedin(
    client: httpx.Client, candidate_name: str, party_name: str, city: str
) -> list[str]:
    """Search Brave API for LinkedIn profile URLs matching the candidate."""
    query = f'"{candidate_name}" {party_name} {city} site:linkedin.com/in/'
    try:
        response = client.get(BRAVE_API_URL, params={"q": query, "count": 10})
        if response.status_code == 429:
            logger.warning(f"  Rate limited, waiting 5s...")
            time.sleep(5)
            response = client.get(BRAVE_API_URL, params={"q": query, "count": 10})
        response.raise_for_status()
        data = response.json()
        results = data.get("web", {}).get("results", [])
        return _extract_linkedin_urls(results)
    except httpx.HTTPError as e:
        logger.warning(f"  Search error for '{candidate_name}': {e}")
        return []


def find_best_match(candidate_name: str, urls: list[str]) -> tuple[str, float] | None:
    """Return (url, score) for the best-matching LinkedIn URL, or None."""
    best_url, best_score = None, 0.0
    for url in urls:
        parsed = urlparse(url)
        slug = parsed.path.strip("/").split("/")[-1]
        slug_name = _slug_to_name(slug)
        score = _similarity(candidate_name, slug_name)
        if score > best_score:
            best_score = score
            best_url = url
    if best_url:
        return best_url, best_score
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print matches without writing to YAML")
    parser.add_argument(
        "--party",
        default=None,
        help="Only process candidates from this party (abbreviation or name, e.g. BIJ1)",
    )
    args = parser.parse_args()

    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.error("BRAVE_API_KEY env var not set. Get a free key at https://brave.com/search/api/")
        sys.exit(1)

    config_path = Path(settings.ELECTION_CONFIG)
    yaml = YAML()
    yaml.preserve_quotes = True

    with open(config_path) as f:
        config = yaml.load(f)

    city = config.get("election", {}).get("city", "")
    wrote = 0
    suggestions = []

    client = httpx.Client(
        timeout=15.0,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        },
    )

    for party in config.get("parties", []):
        party_name = party.get("name", "")
        if args.party:
            needle = args.party.lower()
            if (
                party.get("abbreviation", "").lower() != needle
                and party_name.lower() != needle
            ):
                continue
        logger.info(f"\n--- {party_name} ---")

        for candidate in party.get("candidates", []):
            if candidate.get("linkedin"):
                continue  # already has a URL

            name = candidate["name"]
            urls = search_linkedin(client, name, party_name, city)
            match = find_best_match(name, urls)

            if not match:
                logger.debug(f"  No results: {name}")
                time.sleep(REQUEST_DELAY)
                continue

            url, score = match

            if score >= AUTO_WRITE_THRESHOLD:
                logger.info(f"  ✓ {name:40s} → {url}  ({score:.0%})")
                if not args.dry_run:
                    candidate["linkedin"] = url
                wrote += 1
            elif score >= SUGGEST_THRESHOLD:
                suggestions.append((party_name, name, url, score))

            time.sleep(REQUEST_DELAY)

    client.close()

    if not args.dry_run and wrote:
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        logger.info(f"\nWrote {wrote} LinkedIn URLs to {config_path}")
    elif args.dry_run:
        logger.info(f"\n[dry-run] Would write {wrote} LinkedIn URLs")

    if suggestions:
        print("\nPossible matches to verify manually:")
        print(f"  {'Candidate':<40}  {'URL':<60}  Score")
        print(f"  {'-'*40}  {'-'*60}  -----")
        for party_name, name, url, score in suggestions:
            print(f"  {name:<40}  {url:<60}  {score:.0%}")


if __name__ == "__main__":
    main()
