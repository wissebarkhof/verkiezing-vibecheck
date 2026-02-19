from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

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
