from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Candidate, Election, Motion, MotionCandidate, Party

router = APIRouter(prefix="/kandidaten")


@router.get("/")
def candidate_list(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    candidates = []
    if election:
        candidates = (
            db.query(Candidate)
            .join(Party)
            .filter(Party.election_id == election.id)
            .options(joinedload(Candidate.party))
            .order_by(Party.name, Candidate.position_on_list)
            .all()
        )
    return request.app.state.templates.TemplateResponse(
        request,
        "candidates/list.html",
        {"election": election, "candidates": candidates},
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
