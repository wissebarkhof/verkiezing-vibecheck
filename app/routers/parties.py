from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Election, Motion, MotionParty, Party

router = APIRouter(prefix="/partijen")


@router.get("/")
def party_list(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    parties = []
    if election:
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


@router.get("/{party_id}")
def party_detail(party_id: int, request: Request, db: Session = Depends(get_db)):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        return request.app.state.templates.TemplateResponse(
            request, "parties/detail.html", {"party": None}
        )

    # Motions data
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
            "party": party,
            "motion_count": motion_count,
            "recent_motions": recent_motions,
        },
    )
