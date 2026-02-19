from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import Candidate, Election, Motion, MotionCandidate, Party

router = APIRouter(prefix="/kandidaten")


@router.get("/")
def candidate_list(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    parties = []
    if election:
        parties = (
            db.query(Party)
            .filter(Party.election_id == election.id)
            .options(selectinload(Party.candidates))
            .order_by(Party.current_seats.desc().nullslast(), Party.name)
            .all()
        )
        for party in parties:
            party.candidates.sort(key=lambda c: c.position_on_list)
    return request.app.state.templates.TemplateResponse(
        request,
        "candidates/list.html",
        {"election": election, "parties": parties},
    )


@router.get("/{candidate_id}")
def candidate_detail(
    candidate_id: int, request: Request, db: Session = Depends(get_db)
):
    candidate = (
        db.query(Candidate)
        .options(joinedload(Candidate.party), joinedload(Candidate.posts))
        .filter(Candidate.id == candidate_id)
        .first()
    )
    if not candidate:
        return request.app.state.templates.TemplateResponse(
            request, "candidates/detail.html", {"candidate": None}
        )

    # Motions submitted by this candidate
    candidate_motions = (
        db.query(Motion)
        .join(MotionCandidate)
        .filter(MotionCandidate.candidate_id == candidate.id)
        .order_by(Motion.submission_date.desc().nullslast())
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "candidates/detail.html",
        {"candidate": candidate, "candidate_motions": candidate_motions},
    )
