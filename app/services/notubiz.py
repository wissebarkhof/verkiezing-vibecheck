"""Notubiz API client for fetching council motions and amendments.

The Notubiz API serves Amsterdam council meeting data (raadsinformatie).
Module items within agenda items represent motions (moties) and amendments
(amendementen). Each module item has attributes identified by numeric IDs.

Attribute ID reference:
    1  = Titel
    2  = Hoofddocument (PDF)
    15 = Datum indiening
    17 = Datum afdoening
    21 = Document afdoening
    35 = Toelichting (vote explanation, raw HTML)
    36 = Indiener(s) (submitters, multiple persons)
    37 = Fractie (parties, multiple)
    45 = Type ("Motie" / "Amendement")
    54 = Gekoppeld evenement (linked agenda item)
    62 = Uitslag ("aangenomen" / "verworpen")
"""

import logging
import time
from datetime import date, datetime

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.notubiz.nl"
ORGANISATION_ID = 281  # Amsterdam
API_VERSION = "1.10.8"
REQUEST_DELAY = 0.3  # seconds between requests


def _get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the Notubiz API and return parsed JSON."""
    url = f"{BASE_URL}/{path}"
    default_params = {"format": "json", "version": API_VERSION}
    if params:
        default_params.update(params)

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=default_params)
        response.raise_for_status()
        return response.json()


def fetch_events(date_from: date, date_to: date) -> list[dict]:
    """Fetch all meeting events for Amsterdam within a date range."""
    params = {
        "organisation_id": ORGANISATION_ID,
        "date_from": f"{date_from} 00:00:00",
        "date_to": f"{date_to} 23:59:59",
    }
    data = _get("events", params)
    events = data.get("events", [])
    logger.info(f"Fetched {len(events)} events from {date_from} to {date_to}")
    return events


def fetch_meeting_detail(meeting_id: int) -> dict:
    """Fetch full meeting detail including agenda items and module_items."""
    data = _get(f"events/meetings/{meeting_id}")
    return data.get("meeting", {})


def fetch_module_item(item_id: int) -> dict:
    """Fetch a single module item (motion/amendment) with all attributes."""
    data = _get(f"modules/0/items/{item_id}")
    return data.get("item", {})


def extract_module_item_ids(meeting: dict) -> list[int]:
    """Walk the agenda tree and extract all module_item IDs from a meeting."""
    ids = []

    def walk(items: list[dict]) -> None:
        for item in items:
            for mi in item.get("module_items", []):
                ids.append(mi["id"])
            walk(item.get("agenda_items", []))

    # Top-level module_items
    for mi in meeting.get("module_items", []):
        ids.append(mi["id"])

    # Walk nested agenda items
    walk(meeting.get("agenda_items", []))

    return ids


def parse_motion_attributes(item: dict) -> dict:
    """Parse a module item's attributes into a structured dict.

    Returns a dict with: title, motion_type, result, submission_date,
    resolution_date, toelichting, document_url, resolution_document_url,
    submitters (list of dicts), parties (list of dicts).
    """
    result = {
        "title": None,
        "motion_type": None,
        "result": None,
        "submission_date": None,
        "resolution_date": None,
        "toelichting": None,
        "document_url": None,
        "resolution_document_url": None,
        "submitters": [],
        "parties": [],
    }

    for attr in item.get("attributes", {}).get("attribute", []):
        attr_id = attr["@attributes"]["id"]
        value = attr.get("value")
        values = attr.get("values", {}).get("value", [])
        # Normalize single value to list
        if isinstance(values, dict):
            values = [values]

        if attr_id == 1:  # Titel
            result["title"] = value

        elif attr_id == 45:  # Type
            result["motion_type"] = value

        elif attr_id == 62:  # Uitslag
            result["result"] = value

        elif attr_id == 15:  # Datum indiening
            result["submission_date"] = _parse_date(value)

        elif attr_id == 17:  # Datum afdoening
            result["resolution_date"] = _parse_date(value)

        elif attr_id == 35:  # Toelichting
            result["toelichting"] = value

        elif attr_id == 2:  # Hoofddocument
            if isinstance(value, dict):
                result["document_url"] = value.get("url")

        elif attr_id == 21:  # Document afdoening
            if isinstance(value, dict):
                result["resolution_document_url"] = value.get("url")

        elif attr_id == 36:  # Indiener(s)
            for v in values:
                result["submitters"].append({
                    "name": v.get("@cdata", ""),
                    "person_id": v.get("@attributes", {}).get("id"),
                })

        elif attr_id == 37:  # Fractie
            for v in values:
                result["parties"].append({
                    "name": v.get("@cdata", ""),
                    "party_id": v.get("@attributes", {}).get("id"),
                })

    return result


def _parse_date(value: str | None) -> date | None:
    """Parse a Notubiz datetime string to a date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, AttributeError):
        return None


# --- Name matching ---

# Aliases for Notubiz party names that don't match our DB names directly.
# Keys are lowercase Notubiz names, values are our DB names/abbreviations.
PARTY_ALIASES: dict[str, str] = {
    "groenlinks": "GroenLinks",
    "pvda": "PvdA",
    "partij van de arbeid": "PvdA",
    "vvd": "VVD",
    "d66": "D66",
    "partij voor de dieren": "PvdD",
    "pvdd": "PvdD",
    "bij1": "BIJ1",
    "volt": "VOLT",
    "cda": "CDA",
    "sp": "SP",
    "ja21": "JA21",
    "denk": "DENK",
    "forum voor democratie": "FvD",
    "fvd": "FvD",
}


def match_party(notubiz_name: str, db_parties: list) -> int | None:
    """Match a Notubiz party name to a DB party. Returns party_id or None.

    Tries in order:
    1. Case-insensitive exact match on name or abbreviation
    2. Alias lookup
    3. Substring match (Notubiz name contains DB name or vice versa)
    """
    lower = notubiz_name.strip().lower()

    for party in db_parties:
        if lower == party.name.lower() or lower == party.abbreviation.lower():
            return party.id

    # Alias lookup
    alias_target = PARTY_ALIASES.get(lower)
    if alias_target:
        for party in db_parties:
            if (
                alias_target.lower() == party.name.lower()
                or alias_target.lower() == party.abbreviation.lower()
            ):
                return party.id

    # Substring match
    for party in db_parties:
        if party.name.lower() in lower or lower in party.name.lower():
            return party.id
        if party.abbreviation.lower() in lower or lower in party.abbreviation.lower():
            return party.id

    return None


def _is_initial(part: str) -> bool:
    """Check if a name part is an initial like 'J.', 'R.B.', 'J', 'M.S.'."""
    stripped = part.replace(".", "")
    return stripped.isalpha() and stripped.isupper() and len(stripped) <= 3


def _extract_last_name(full_name: str) -> str:
    """Extract last name by dropping initials and first names.

    'R.B. Havelaar' -> 'havelaar'
    'M.S. von Gerhardt' -> 'von gerhardt'
    'Rob Havelaar' -> 'havelaar'
    'Melanie van der Horst' -> 'van der horst'
    """
    parts = full_name.strip().split()
    # Drop leading parts that look like initials
    while parts and _is_initial(parts[0]):
        parts.pop(0)
    # For DB names (no initials), drop the first name (assumed to be one word
    # unless it contains lowercase tussenvoegsels like 'van', 'de', 'der')
    if parts and parts[0][0].isupper() and not _is_initial(parts[0]):
        # Check if second part is a tussenvoegsel — if so, first part is the
        # only first name. If second part is also capitalized, still drop just
        # the first part (e.g. "Melanie van der Horst" -> "van der Horst")
        if len(parts) > 1:
            parts.pop(0)
    return " ".join(parts).lower()


def match_candidate(
    notubiz_name: str, person_id: int | None, db_candidates: list
) -> int | None:
    """Match a Notubiz person name to a DB candidate. Returns candidate_id or None.

    Uses last-name matching since Notubiz uses initials (e.g. "J. Broersen")
    while our DB has full names (e.g. "Joris Broersen").
    """
    notubiz_last = _extract_last_name(notubiz_name)
    if not notubiz_last:
        return None

    for candidate in db_candidates:
        db_last = _extract_last_name(candidate.name)
        if notubiz_last == db_last:
            return candidate.id

    return None
