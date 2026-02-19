import logging
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models import Candidate, Election, Party
from app.services.pdf import extract_pages_from_pdf, extract_text_from_pdf, chunk_pages

logger = logging.getLogger(__name__)


def load_yaml_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def slugify(city: str, date_val: date) -> str:
    return f"{city}-{date_val.year}"


def ingest_election(
    db: Session, config_path: Path, party_filter: str | None = None
) -> Election:
    """Load YAML config and populate DB with election, parties, and candidates.

    Safe to re-run: uses upsert logic based on slug / name matching.
    If party_filter is given (abbreviation or name), only that party is ingested.
    """
    config = load_yaml_config(config_path)
    data_dir = config_path.parent.parent  # data/ directory (parent of elections/)

    election_data = config["election"]
    election_date = date.fromisoformat(election_data["date"])
    slug = slugify(election_data["city"], election_date)

    # Upsert election
    election = db.query(Election).filter(Election.slug == slug).first()
    if election:
        election.name = election_data["name"]
        election.city = election_data["city"]
        election.date = election_date
        logger.info(f"Updated election: {election.name}")
    else:
        election = Election(
            slug=slug,
            name=election_data["name"],
            city=election_data["city"],
            date=election_date,
        )
        db.add(election)
        db.flush()
        logger.info(f"Created election: {election.name}")

    # Ingest parties (optionally filtered to a single party)
    parties = config.get("parties", [])
    if party_filter:
        needle = party_filter.lower()
        parties = [
            p for p in parties
            if p.get("abbreviation", "").lower() == needle
            or p.get("name", "").lower() == needle
        ]
        if not parties:
            logger.warning(f"No party matching '{party_filter}' found in config")
    for party_data in parties:
        _ingest_party(db, election, party_data, data_dir)

    db.commit()
    logger.info("Ingestion complete")
    return election


def _ingest_party(
    db: Session, election: Election, party_data: dict, data_dir: Path
) -> Party:
    """Upsert a party and its candidates."""
    party = (
        db.query(Party)
        .filter(Party.election_id == election.id, Party.name == party_data["name"])
        .first()
    )

    poll_updated_at: date | None = None
    if raw_date := party_data.get("poll_updated_at"):
        poll_updated_at = date.fromisoformat(str(raw_date))

    if party:
        party.abbreviation = party_data.get("abbreviation", "")
        party.website_url = party_data.get("website")
        party.logo_url = party_data.get("logo")
        party.current_seats = party_data.get("current_seats")
        party.polled_seats = party_data.get("polled_seats")
        party.poll_updated_at = poll_updated_at
        logger.info(f"  Updated party: {party.name}")
    else:
        party = Party(
            election_id=election.id,
            name=party_data["name"],
            abbreviation=party_data.get("abbreviation", ""),
            website_url=party_data.get("website"),
            logo_url=party_data.get("logo"),
            current_seats=party_data.get("current_seats"),
            polled_seats=party_data.get("polled_seats"),
            poll_updated_at=poll_updated_at,
        )
        db.add(party)
        db.flush()
        logger.info(f"  Created party: {party.name}")

    # Process program PDF if available
    pdf_path_str = party_data.get("program_pdf")
    if pdf_path_str:
        pdf_path = data_dir / pdf_path_str
        if pdf_path.exists():
            logger.info(f"    Extracting PDF: {pdf_path}")
            pages = extract_pages_from_pdf(pdf_path)
            party.program_text = extract_text_from_pdf(pdf_path)

            # Store page-aware chunks as documents for RAG
            _ingest_pdf_chunks(db, party, pages)
        else:
            logger.warning(f"    PDF not found: {pdf_path}")

    # Ingest candidates
    for cand_data in party_data.get("candidates", []):
        _ingest_candidate(db, party, cand_data)

    return party


def _ingest_candidate(db: Session, party: Party, cand_data: dict) -> Candidate:
    """Upsert a candidate."""
    candidate = (
        db.query(Candidate)
        .filter(
            Candidate.party_id == party.id,
            Candidate.position_on_list == cand_data["position"],
        )
        .first()
    )

    if candidate:
        candidate.name = cand_data["name"]
        candidate.linkedin_url = cand_data.get("linkedin")

        new_handle = cand_data.get("bluesky")
        if candidate.bluesky_handle != new_handle:
            candidate.bluesky_handle = new_handle
            if new_handle is None:
                # Handle removed from YAML — clear derived social data too
                candidate.social_summary = None
                from app.models import SocialPost
                db.query(SocialPost).filter(SocialPost.candidate_id == candidate.id).delete()
                logger.info(f"    Cleared social data for: {candidate.name}")

        logger.info(f"    Updated candidate: {candidate.name}")
    else:
        candidate = Candidate(
            party_id=party.id,
            name=cand_data["name"],
            position_on_list=cand_data["position"],
            bluesky_handle=cand_data.get("bluesky"),
            linkedin_url=cand_data.get("linkedin"),
        )
        db.add(candidate)
        logger.info(f"    Created candidate: {candidate.name}")

    return candidate


def _ingest_pdf_chunks(db: Session, party: Party, pages: list[tuple[int, str]]) -> None:
    """Chunk page-aware program text and store as Document rows (without embeddings yet)."""
    from app.models import Document

    # Remove existing chunks for this party to avoid duplicates on re-run
    db.query(Document).filter(
        Document.party_id == party.id, Document.source_type == "program"
    ).delete()

    chunks = chunk_pages(pages)
    for i, chunk in enumerate(chunks):
        doc = Document(
            party_id=party.id,
            source_type="program",
            content=chunk["content"],
            metadata_={
                "chunk_index": i,
                "total_chunks": len(chunks),
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
            },
        )
        db.add(doc)

    logger.info(f"    Stored {len(chunks)} document chunks")
