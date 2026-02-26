from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Election, Motion, MotionParty, Party

router = APIRouter()


@router.get("/verkiezingen/{slug}/partijen")
def party_list(slug: str, request: Request, db: Session = Depends(get_db)):
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
    return request.app.state.templates.TemplateResponse(
        request,
        "parties/list.html",
        {"election": election, "parties": parties},
    )


@router.get("/verkiezingen/{slug}/partijen/{party_id}")
def party_detail(slug: str, party_id: int, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )
    party = (
        db.query(Party)
        .filter(Party.id == party_id, Party.election_id == election.id)
        .first()
    )
    if not party:
        return request.app.state.templates.TemplateResponse(
            request, "parties/detail.html", {"party": None, "election": election}
        )

    motion_count = (
        db.query(func.count(Motion.id))
        .join(MotionParty)
        .filter(MotionParty.party_id == party.id)
        .scalar()
    )
    recent_motions = (
        db.query(Motion)
        .join(MotionParty)
        .filter(MotionParty.party_id == party.id)
        .order_by(Motion.submission_date.desc().nullslast())
        .limit(5)
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "parties/detail.html",
        {
            "election": election,
            "party": party,
            "motion_count": motion_count,
            "recent_motions": recent_motions,
        },
    )
