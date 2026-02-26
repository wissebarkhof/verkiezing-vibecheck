import yaml
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Candidate, Election, Motion, Party

router = APIRouter()


@router.get("/verkiezingen/{slug}")
def election_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )

    party_count = (
        db.query(func.count(Party.id))
        .filter(Party.election_id == election.id)
        .scalar()
        or 0
    )
    candidate_count = (
        db.query(func.count(Candidate.id))
        .join(Party)
        .filter(Party.election_id == election.id)
        .scalar()
        or 0
    )
    motion_count = (
        db.query(func.count(Motion.id))
        .filter(Motion.election_id == election.id)
        .scalar()
        or 0
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "elections/detail.html",
        {
            "election": election,
            "party_count": party_count,
            "candidate_count": candidate_count,
            "motion_count": motion_count,
        },
    )


@router.get("/verkiezingen/{slug}/programmas")
def programs_page(slug: str, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )

    parties = (
        db.query(Party)
        .filter(Party.election_id == election.id)
        .order_by(Party.current_seats.desc().nullslast(), Party.name)
        .all()
    )

    # Build name → PDF URL map from YAML (program_pdf not stored in DB)
    pdf_map: dict[str, str] = {}
    yaml_path = settings.elections_dir_path / f"{election.city}.yml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            config = yaml.safe_load(f)
        for p in config.get("parties", []):
            if p.get("program_pdf"):
                pdf_map[p["name"]] = "/" + p["program_pdf"]

    return request.app.state.templates.TemplateResponse(
        request,
        "programmas.html",
        {"election": election, "parties": parties, "pdf_map": pdf_map},
    )
