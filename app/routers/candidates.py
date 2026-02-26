from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import Candidate, Election, Motion, MotionCandidate, Party

router = APIRouter()


@router.get("/verkiezingen/{slug}/kandidaten")
def candidate_list(slug: str, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )
    parties = (
        db.query(Party)
        .filter(Party.election_id == election.id)
        .options(selectinload(Party.candidates))
        .order_by(Party.polled_seats.desc().nullslast(), Party.current_seats.desc().nullslast(), Party.name)
        .all()
    )
    for party in parties:
        party.candidates.sort(key=lambda c: c.position_on_list)
    return request.app.state.templates.TemplateResponse(
        request,
        "candidates/list.html",
        {"election": election, "parties": parties},
    )


@router.get("/verkiezingen/{slug}/kandidaten/{candidate_id}")
def candidate_detail(
    slug: str, candidate_id: int, request: Request, db: Session = Depends(get_db)
):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )
    candidate = (
        db.query(Candidate)
        .options(joinedload(Candidate.party), joinedload(Candidate.posts))
        .filter(Candidate.id == candidate_id)
        .first()
    )
    if not candidate or candidate.party.election_id != election.id:
        return request.app.state.templates.TemplateResponse(
            request, "candidates/detail.html", {"candidate": None, "election": election}
        )

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
        {"election": election, "candidate": candidate, "candidate_motions": candidate_motions},
    )
