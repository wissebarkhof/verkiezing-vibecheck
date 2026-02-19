"""Search Bluesky for candidate handles and write them into the election YAML.

For each candidate without a 'bluesky' field, searches the Bluesky actor search
API by name. High-confidence matches (>= 0.85 similarity) are written back to the
YAML automatically. Possible matches (0.60–0.85) are printed for manual review.

Uses ruamel.yaml for round-trip parsing so existing YAML formatting is preserved.

Usage:
    uv run python scripts/hydrate_bluesky_handles.py
    uv run python scripts/hydrate_bluesky_handles.py --dry-run
"""

import argparse
import logging
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

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

BLUESKY_API = "https://public.api.bsky.app/xrpc"
AUTO_WRITE_THRESHOLD = 0.85   # write handle to YAML automatically
SUGGEST_THRESHOLD = 0.60      # print as possible match for manual review


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.lower().split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def search_actor(name: str) -> list[dict]:
    """Search Bluesky actors by name. Returns list of {handle, displayName}."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{BLUESKY_API}/app.bsky.actor.searchActors",
                params={"q": name, "limit": 8},
            )
            response.raise_for_status()
            return response.json().get("actors", [])
    except httpx.HTTPError as e:
        logger.warning(f"  Search error for '{name}': {e}")
        return []


def find_best_match(candidate_name: str, actors: list[dict]) -> tuple[str, float] | None:
    """Return (handle, score) for the best-matching actor, or None."""
    best_handle, best_score = None, 0.0
    for actor in actors:
        display = actor.get("displayName", "")
        if not display:
            continue
        score = _similarity(candidate_name, display)
        if score > best_score:
            best_score = score
            best_handle = actor["handle"]
    if best_handle:
        return best_handle, best_score
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

    config_path = Path(settings.ELECTION_CONFIG)
    yaml = YAML()
    yaml.preserve_quotes = True

    with open(config_path) as f:
        config = yaml.load(f)

    wrote = 0
    suggestions = []

    for party in config.get("parties", []):
        party_name = party.get("name", "")
        if args.party:
            needle = args.party.lower()
            if (
                party.get("abbreviation", "").lower() != needle
                and party_name.lower() != needle
            ):
                continue
        for candidate in party.get("candidates", []):
            if candidate.get("bluesky"):
                continue  # already has a handle

            name = candidate["name"]
            actors = search_actor(name)
            match = find_best_match(name, actors)

            if not match:
                logger.debug(f"  No results: {name}")
                time.sleep(0.3)
                continue

            handle, score = match

            if score >= AUTO_WRITE_THRESHOLD:
                logger.info(f"  ✓ {name:40s} → @{handle}  ({score:.0%})")
                if not args.dry_run:
                    candidate["bluesky"] = f"@{handle}"
                wrote += 1
            elif score >= SUGGEST_THRESHOLD:
                suggestions.append((party_name, name, handle, score))

            time.sleep(0.3)  # be polite to the API

    if not args.dry_run and wrote:
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        logger.info(f"\nWrote {wrote} handles to {config_path}")
    elif args.dry_run:
        logger.info(f"\n[dry-run] Would write {wrote} handles")

    if suggestions:
        print("\nPossible matches to verify manually:")
        print(f"  {'Candidate':<40}  {'Handle':<40}  Score")
        print(f"  {'-'*40}  {'-'*40}  -----")
        for party_name, name, handle, score in suggestions:
            print(f"  {name:<40}  @{handle:<40}  {score:.0%}")


if __name__ == "__main__":
    main()
