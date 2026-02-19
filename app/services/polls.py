"""Polling data service.

Supports fetching poll data from configured sources, storing results in the DB,
and keeping Party.polled_seats / Party.poll_updated_at in sync with the newest poll.

Supported source types:
  - "onderzoek_amsterdam": Onderzoek en Statistiek (O&S) Amsterdam articles.
    These are Next.js pages whose __NEXT_DATA__ script tag contains the full
    article body as structured JSON, including chart specifications with
    party percentages and seat projections.
"""

import json
import logging
import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Name matching helpers
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")


def _normalize(name: str) -> str:
    """Lowercase, strip accents, strip punctuation, collapse whitespace."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    name = _PUNCT_RE.sub("", name)
    return " ".join(name.split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def match_party_name(raw_name: str, db_parties: list) -> int | None:
    """Return party_id for the best fuzzy match, or None if below threshold."""
    norm_raw = _normalize(raw_name)
    best_id = None
    best_score = 0.0
    for party in db_parties:
        for candidate in [party.name, party.abbreviation]:
            score = _similarity(norm_raw, _normalize(candidate))
            if score > best_score:
                best_score = score
                best_id = party.id
    # Require a strong match (real pairs like "GroenLinks"/"groenlinks" score 1.0;
    # structurally similar-but-wrong names like "Partij van de Ouderen" vs
    # "Partij voor de Dieren" score ~0.81 and should not be matched)
    if best_score >= 0.85:
        return best_id
    logger.warning(f"No match for poll party '{raw_name}' (best score {best_score:.2f})")
    return None


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; VerkiezingVibecheck/1.0; "
        "+https://github.com/example/verkiezing-vibecheck)"
    )
}

# Dutch month names → month number
_NL_MONTHS = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
    "september": 9, "oktober": 10, "november": 11, "december": 12,
}

# "27 januari en 9 februari 2026" (year only at end)
_PERIOD_SAME_YEAR = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")"
    r"\s+(?:en|t/m|tot|–|-)\s+"
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")\s+(\d{4})",
    re.IGNORECASE,
)

# "27 januari en 9 februari" (no year — caller supplies fallback_year)
_PERIOD_NO_YEAR = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")"
    r"\s+(?:en|t/m|tot|–|-)\s+"
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")(?!\s+\d{4})",
    re.IGNORECASE,
)

# "27 januari 2026 – 9 februari 2026" (year on both sides)
_PERIOD_BOTH_YEARS = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")\s+(\d{4})"
    r"\s*[t/–-]+\s*"
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")\s+(\d{4})",
    re.IGNORECASE,
)

_DATE_SINGLE = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_NL_MONTHS) + r")\s+(\d{4})",
    re.IGNORECASE,
)

# "1.354" or "1,354" Dutch thousands-separated number
_SAMPLE_SIZE_RE = re.compile(r"(\d{1,3}[.,]\d{3}|\d{3,})\s+(?:respondenten|Amsterdammers|personen)")


def _parse_nl_date(day: str, month_str: str, year: int) -> date:
    return date(year, _NL_MONTHS[month_str.lower()], int(day))


def _extract_field_period(text: str, fallback_year: int | None = None) -> tuple[date | None, date | None]:
    """Parse field period start/end from Dutch methodology text.

    Falls back to `fallback_year` (e.g. the publication year) when dates lack
    an explicit year, as O&S often writes "27 januari en 9 februari 1.354 Amsterdammers".
    """
    m = _PERIOD_BOTH_YEARS.search(text)
    if m:
        d1, mo1, y1, d2, mo2, y2 = m.groups()
        return _parse_nl_date(d1, mo1, int(y1)), _parse_nl_date(d2, mo2, int(y2))

    m = _PERIOD_SAME_YEAR.search(text)
    if m:
        d1, mo1, d2, mo2, year_str = m.groups()
        year = int(year_str)
        return _parse_nl_date(d1, mo1, year), _parse_nl_date(d2, mo2, year)

    m = _PERIOD_NO_YEAR.search(text)
    if m and fallback_year:
        d1, mo1, d2, mo2 = m.groups()
        return _parse_nl_date(d1, mo1, fallback_year), _parse_nl_date(d2, mo2, fallback_year)

    # Single date fallback
    m = _DATE_SINGLE.search(text)
    if m:
        d, mo, y = m.groups()
        return None, _parse_nl_date(d, mo, int(y))

    return None, None


def _extract_sample_size(text: str) -> int | None:
    """Parse sample size from Dutch methodology text, e.g. '1.354 Amsterdammers'."""
    m = _SAMPLE_SIZE_RE.search(text)
    if m:
        raw = m.group(1).replace(".", "").replace(",", "")
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def _parse_next_data(soup: BeautifulSoup) -> dict | None:
    """Extract the Next.js __NEXT_DATA__ page props from the page."""
    for tag in soup.find_all("script", {"type": "application/json"}):
        text = tag.string or ""
        if not text.strip():
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            continue
        if "props" in obj and "pageProps" in obj.get("props", {}):
            return obj["props"]["pageProps"]
    return None


def _find_party_chart(body: list) -> dict | None:
    """Return the first shared.visualisation body item that has party data."""
    for item in body:
        if item.get("__component") != "shared.visualisation":
            continue
        spec = item.get("specification", {})
        values = spec.get("data", {}).get("values", [])
        if values and isinstance(values[0], dict) and "party" in values[0]:
            return item
    return None


def _parse_results_from_values(values: list) -> list[dict]:
    """Convert raw chart data values to {party_name_raw, percentage, seats}."""
    parsed = []
    for row in values:
        if not isinstance(row, dict):
            continue
        party_name = row.get("party") or row.get("partij") or row.get("naam")
        if not party_name:
            continue
        pct = row.get("percentage")
        if pct is not None:
            try:
                pct = float(pct) * 100  # O&S stores as 0–1
            except (ValueError, TypeError):
                pct = None
        seats = row.get("seats") or row.get("zetels")
        if seats is not None:
            try:
                seats = int(round(float(seats)))
            except (ValueError, TypeError):
                seats = None
        parsed.append({
            "party_name_raw": str(party_name),
            "percentage": pct,
            "seats": seats,
        })
    return parsed


def scrape_onderzoek_amsterdam(url: str) -> dict:
    """Scrape a poll from an O&S Amsterdam article (Next.js site).

    The page embeds all article data (including chart specs) in a
    <script type="application/json"> tag as Next.js page props.

    Returns a dict with keys:
        field_start  (date | None)
        field_end    (date | None)
        published_at (date | None)
        sample_size  (int | None)
        results      (list[dict]) — [{party_name_raw, percentage, seats}]
    """
    logger.info(f"Fetching O&S article: {url}")
    with httpx.Client(timeout=30, follow_redirects=True, headers=_HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    page_props = _parse_next_data(soup)
    if not page_props:
        raise ValueError("Could not find Next.js page props in the page.")

    # Publication date
    published_at: date | None = None
    pub_str = page_props.get("publishedAt") or page_props.get("publicationDate")
    if pub_str:
        try:
            published_at = datetime.fromisoformat(pub_str[:10]).date()
        except ValueError:
            pass

    body: list = page_props.get("body", [])

    # Party preference chart
    chart_item = _find_party_chart(body)
    if not chart_item:
        raise ValueError("Could not find party preference chart in article body.")

    values = chart_item["specification"]["data"]["values"]
    results = _parse_results_from_values(values)
    logger.info(f"  Extracted {len(results)} party result(s) from chart '{chart_item.get('title')}'")

    # Field period + sample size from methodology text-box
    field_start: date | None = None
    field_end: date | None = None
    sample_size: int | None = None

    fallback_year = published_at.year if published_at else None
    for item in body:
        text = item.get("text") or ""
        if not text:
            continue
        fs, fe = _extract_field_period(text, fallback_year=fallback_year)
        if fe and not field_end:
            field_start, field_end = fs, fe
        n = _extract_sample_size(text)
        if n and not sample_size:
            sample_size = n

    return {
        "field_start": field_start,
        "field_end": field_end,
        "published_at": published_at,
        "sample_size": sample_size,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_SCRAPERS = {
    "onderzoek_amsterdam": scrape_onderzoek_amsterdam,
}


# ---------------------------------------------------------------------------
# Store / upsert
# ---------------------------------------------------------------------------

def fetch_and_store_polls(db, election, config: dict) -> list:
    """Fetch polls from all enabled sources in config, upsert into DB.

    Also updates Party.polled_seats / Party.poll_updated_at from the newest poll
    that has seat data, so the existing party list UI keeps working.

    Returns list of Poll objects that were inserted/updated.
    """
    from app.models.party import Party
    from app.models.poll import Poll, PollResult

    sources = config.get("polling_sources", [])
    if not sources:
        logger.info("No polling_sources configured, nothing to do.")
        return []

    db_parties = db.query(Party).filter(Party.election_id == election.id).all()

    stored_polls: list[Poll] = []

    for source in sources:
        if not source.get("enabled", True):
            logger.info(f"Skipping disabled source: {source['name']}")
            continue

        source_type = source["type"]
        scraper = _SCRAPERS.get(source_type)
        if not scraper:
            logger.warning(f"Unknown source type '{source_type}', skipping.")
            continue

        try:
            data = scraper(source["url"])
        except Exception:
            logger.exception(f"Error scraping {source['name']} ({source['url']})")
            continue

        # field_end is required for the upsert key; fall back to today if not found
        field_end = data["field_end"] or date.today()
        if not data["field_end"]:
            logger.warning(
                f"Could not parse field_end from {source['url']}; using today as fallback."
            )

        # Upsert Poll row
        poll = (
            db.query(Poll)
            .filter(
                Poll.election_id == election.id,
                Poll.source_url == source["url"],
                Poll.field_end == field_end,
            )
            .first()
        )

        if poll:
            logger.info(f"Updating existing poll: {source['name']} / {field_end}")
            poll.source_name = source["name"]
            poll.source_type = source_type
            poll.field_start = data["field_start"]
            poll.published_at = data["published_at"]
            poll.sample_size = data["sample_size"]
            # Wipe old results; will re-create below
            db.query(PollResult).filter(PollResult.poll_id == poll.id).delete()
        else:
            logger.info(f"Inserting new poll: {source['name']} / {field_end}")
            poll = Poll(
                election_id=election.id,
                source_name=source["name"],
                source_url=source["url"],
                source_type=source_type,
                field_start=data["field_start"],
                field_end=field_end,
                published_at=data["published_at"],
                sample_size=data["sample_size"],
            )
            db.add(poll)
            db.flush()  # get poll.id

        # Insert PollResult rows
        unmatched = []
        for row in data["results"]:
            party_id = match_party_name(row["party_name_raw"], db_parties)
            if not party_id:
                unmatched.append(row["party_name_raw"])
            db.add(PollResult(
                poll_id=poll.id,
                party_id=party_id,
                party_name_raw=row["party_name_raw"],
                percentage=row.get("percentage"),
                seats=row.get("seats"),
            ))

        if unmatched:
            logger.warning(
                f"Unmatched party names in '{source['name']}': {', '.join(unmatched)}"
            )

        db.flush()
        stored_polls.append(poll)

    db.commit()

    # Update Party cache fields from the newest poll that has seat data
    _update_party_cache(db, election, db_parties)

    return stored_polls


def _update_party_cache(db, election, db_parties: list) -> None:
    """Overwrite Party.polled_seats / Party.poll_updated_at from the newest poll."""
    from app.models.poll import Poll, PollResult

    # Find the most recent poll for this election that has at least one seat value
    newest_poll = (
        db.query(Poll)
        .filter(Poll.election_id == election.id)
        .order_by(Poll.field_end.desc())
        .first()
    )
    if not newest_poll:
        return

    results = (
        db.query(PollResult)
        .filter(PollResult.poll_id == newest_poll.id, PollResult.seats.isnot(None))
        .all()
    )
    if not results:
        logger.info("Newest poll has no seat data — Party cache not updated.")
        return

    seats_by_party: dict[int, int] = {r.party_id: r.seats for r in results if r.party_id}

    updated = 0
    for party in db_parties:
        if party.id in seats_by_party:
            party.polled_seats = seats_by_party[party.id]
            party.poll_updated_at = newest_poll.field_end
            updated += 1

    db.commit()
    logger.info(f"Updated polled_seats for {updated} parties from poll {newest_poll.id}.")
