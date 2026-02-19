"""Fetch council motions (moties) and amendments (amendementen) from the Notubiz API.

For each meeting in the date range:
  1. Fetches meeting detail with agenda items.
  2. Extracts module_item IDs (motions/amendments linked to agenda items).
  3. Fetches each module item's detail and parses attributes.
  4. Upserts into the motions table (notubiz_item_id is the upsert key).
  5. Links submitting parties and candidates via association tables.

Unmatched party/candidate names are logged for manual review. The raw Notubiz
names are always stored in the association tables for audit purposes.

Usage:
    uv run python scripts/fetch_motions.py
    uv run python scripts/fetch_motions.py --date-from 2025-01-01 --date-to 2025-02-01
"""

import argparse
import logging
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Candidate, Election, Motion, MotionCandidate, MotionParty, Party
from app.services.notubiz import (
    REQUEST_DELAY,
    extract_module_item_ids,
    fetch_events,
    fetch_meeting_detail,
    fetch_module_item,
    match_candidate,
    match_party,
    parse_motion_attributes,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Default: full council term start to today
DEFAULT_DATE_FROM = date(2022, 3, 31)


def upsert_motion(
    db,
    election_id: int,
    notubiz_item_id: int,
    parsed: dict,
    meeting_event_id: int | None,
    db_parties: list,
    db_candidates: list,
    unmatched_parties: Counter,
    unmatched_candidates: Counter,
) -> None:
    """Upsert a single motion and its party/candidate associations."""
    motion = db.query(Motion).filter(Motion.notubiz_item_id == notubiz_item_id).first()

    if motion:
        # Update existing
        motion.title = parsed["title"] or motion.title
        motion.motion_type = parsed["motion_type"]
        motion.result = parsed["result"]
        motion.submission_date = parsed["submission_date"]
        motion.resolution_date = parsed["resolution_date"]
        motion.toelichting = parsed["toelichting"]
        motion.document_url = parsed["document_url"]
        motion.resolution_document_url = parsed["resolution_document_url"]
        motion.meeting_event_id = meeting_event_id
        # Clear and re-create associations (simpler than diffing)
        db.query(MotionParty).filter(MotionParty.motion_id == motion.id).delete()
        db.query(MotionCandidate).filter(MotionCandidate.motion_id == motion.id).delete()
    else:
        motion = Motion(
            election_id=election_id,
            notubiz_item_id=notubiz_item_id,
            title=parsed["title"] or f"Untitled ({notubiz_item_id})",
            motion_type=parsed["motion_type"],
            result=parsed["result"],
            submission_date=parsed["submission_date"],
            resolution_date=parsed["resolution_date"],
            toelichting=parsed["toelichting"],
            document_url=parsed["document_url"],
            resolution_document_url=parsed["resolution_document_url"],
            meeting_event_id=meeting_event_id,
        )
        db.add(motion)
        db.flush()  # get motion.id

    # Link parties
    for p in parsed["parties"]:
        party_id = match_party(p["name"], db_parties)
        if not party_id:
            unmatched_parties[p["name"]] += 1
        db.add(MotionParty(
            motion_id=motion.id,
            party_id=party_id,
            notubiz_party_name=p["name"],
        ))

    # Link candidates
    for s in parsed["submitters"]:
        candidate_id = match_candidate(s["name"], s.get("person_id"), db_candidates)
        if not candidate_id:
            unmatched_candidates[s["name"]] += 1
        db.add(MotionCandidate(
            motion_id=motion.id,
            candidate_id=candidate_id,
            notubiz_person_name=s["name"],
            notubiz_person_id=s.get("person_id"),
        ))


def main():
    parser = argparse.ArgumentParser(description="Fetch motions from Notubiz API")
    parser.add_argument("--date-from", type=date.fromisoformat, default=DEFAULT_DATE_FROM)
    parser.add_argument("--date-to", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    db = SessionLocal()
    try:
        election = db.query(Election).first()
        if not election:
            logger.error("No election found. Run ingestion first.")
            return

        db_parties = db.query(Party).filter(Party.election_id == election.id).all()
        db_candidates = (
            db.query(Candidate)
            .join(Party)
            .filter(Party.election_id == election.id)
            .all()
        )
        logger.info(
            f"Loaded {len(db_parties)} parties and {len(db_candidates)} candidates for matching"
        )

        # Fetch events
        events = fetch_events(args.date_from, args.date_to)
        time.sleep(REQUEST_DELAY)

        # Track unmatched names
        unmatched_parties: Counter = Counter()
        unmatched_candidates: Counter = Counter()
        total_motions = 0
        seen_item_ids: set[int] = set()

        for event in events:
            if event.get("announcement") or event.get("canceled"):
                continue

            event_id = event["id"]
            attrs = {a["id"]: a["value"] for a in event.get("attributes", [])}
            event_title = attrs.get(1, f"Event {event_id}")

            logger.info(f"Fetching meeting: {event_title} (id={event_id})")
            meeting = fetch_meeting_detail(event_id)
            time.sleep(REQUEST_DELAY)

            module_item_ids = extract_module_item_ids(meeting)
            if not module_item_ids:
                logger.info(f"  No module items found, skipping")
                continue

            # Deduplicate: same motion can appear in multiple agenda items
            new_ids = [mid for mid in module_item_ids if mid not in seen_item_ids]
            seen_item_ids.update(new_ids)

            logger.info(f"  Found {len(new_ids)} new module items (of {len(module_item_ids)} total)")

            for item_id in new_ids:
                try:
                    item = fetch_module_item(item_id)
                    time.sleep(REQUEST_DELAY)

                    parsed = parse_motion_attributes(item)
                    if not parsed["title"]:
                        logger.warning(f"  Skipping item {item_id}: no title")
                        continue

                    upsert_motion(
                        db=db,
                        election_id=election.id,
                        notubiz_item_id=item_id,
                        parsed=parsed,
                        meeting_event_id=event_id,
                        db_parties=db_parties,
                        db_candidates=db_candidates,
                        unmatched_parties=unmatched_parties,
                        unmatched_candidates=unmatched_candidates,
                    )
                    total_motions += 1

                except Exception:
                    logger.exception(f"  Error processing module item {item_id}")

            db.commit()
            logger.info(f"  Committed batch")

        logger.info(f"\nDone. Processed {total_motions} motions/amendments.")

        if unmatched_parties:
            logger.warning("Unmatched party names (add to PARTY_ALIASES if needed):")
            for name, count in unmatched_parties.most_common():
                logger.warning(f"  {name}: {count} occurrences")

        if unmatched_candidates:
            logger.warning("Unmatched candidate names:")
            for name, count in unmatched_candidates.most_common():
                logger.warning(f"  {name}: {count} occurrences")

    finally:
        db.close()


if __name__ == "__main__":
    main()
