import math

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Election, Motion, MotionCandidate, MotionParty, Party

router = APIRouter(prefix="/moties")

PAGE_SIZE = 20


@router.get("/")
def motion_list(
    request: Request,
    db: Session = Depends(get_db),
    type: str = "",
    result: str = "",
    party_id: int | None = None,
    q: str = "",
    page: int = 1,
):
    election = db.query(Election).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "motions/list.html", {"election": None, "motions": [], "parties": []}
        )

    query = (
        db.query(Motion)
        .filter(Motion.election_id == election.id)
    )

    if type:
        query = query.filter(Motion.motion_type == type)
    if result:
        query = query.filter(Motion.result == result)
    if party_id:
        query = query.join(MotionParty).filter(MotionParty.party_id == party_id)
    if q.strip():
        query = query.filter(Motion.title.ilike(f"%{q.strip()}%"))

    total = query.count()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))

    motion_ids = [
        row[0]
        for row in query
        .with_entities(Motion.id)
        .order_by(Motion.submission_date.desc().nullslast(), Motion.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    ]
    motions = (
        db.query(Motion)
        .options(joinedload(Motion.parties).joinedload(MotionParty.party))
        .filter(Motion.id.in_(motion_ids))
        .order_by(Motion.submission_date.desc().nullslast(), Motion.id.desc())
        .all()
    ) if motion_ids else []

    parties = (
        db.query(Party)
        .filter(Party.election_id == election.id)
        .order_by(Party.name)
        .all()
    )

    context = {
        "election": election,
        "motions": motions,
        "parties": parties,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "filter_type": type,
        "filter_result": result,
        "filter_party_id": party_id,
        "filter_q": q,
    }

    if request.headers.get("HX-Request"):
        return request.app.state.templates.TemplateResponse(
            request, "motions/_list_partial.html", context
        )

    return request.app.state.templates.TemplateResponse(
        request, "motions/list.html", context
    )


@router.get("/statistieken")
def motion_stats(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "motions/stats.html", {"election": None, "stats": []}
        )

    parties = (
        db.query(Party)
        .filter(Party.election_id == election.id)
        .order_by(Party.name)
        .all()
    )

    stats = []
    for party in parties:
        total = (
            db.query(func.count(Motion.id))
            .join(MotionParty)
            .filter(MotionParty.party_id == party.id, Motion.election_id == election.id)
            .scalar()
        )
        adopted = (
            db.query(func.count(Motion.id))
            .join(MotionParty)
            .filter(
                MotionParty.party_id == party.id,
                Motion.election_id == election.id,
                func.lower(Motion.result) == "aangenomen",
            )
            .scalar()
        )
        rejected = (
            db.query(func.count(Motion.id))
            .join(MotionParty)
            .filter(
                MotionParty.party_id == party.id,
                Motion.election_id == election.id,
                func.lower(Motion.result) == "verworpen",
            )
            .scalar()
        )
        moties = (
            db.query(func.count(Motion.id))
            .join(MotionParty)
            .filter(
                MotionParty.party_id == party.id,
                Motion.election_id == election.id,
                Motion.motion_type == "Motie",
            )
            .scalar()
        )
        amendementen = (
            db.query(func.count(Motion.id))
            .join(MotionParty)
            .filter(
                MotionParty.party_id == party.id,
                Motion.election_id == election.id,
                Motion.motion_type == "Amendement",
            )
            .scalar()
        )

        if total > 0:
            success_rate = round(adopted / total * 100) if total else 0
            stats.append({
                "party": party,
                "total": total,
                "moties": moties,
                "amendementen": amendementen,
                "adopted": adopted,
                "rejected": rejected,
                "success_rate": success_rate,
            })

    # Sort by total motions descending
    stats.sort(key=lambda s: s["total"], reverse=True)

    return request.app.state.templates.TemplateResponse(
        request, "motions/stats.html", {"election": election, "stats": stats}
    )


@router.get("/{motion_id}")
def motion_detail(motion_id: int, request: Request, db: Session = Depends(get_db)):
    motion = (
        db.query(Motion)
        .options(
            joinedload(Motion.parties).joinedload(MotionParty.party),
            joinedload(Motion.candidates).joinedload(MotionCandidate.candidate),
        )
        .filter(Motion.id == motion_id)
        .first()
    )

    return request.app.state.templates.TemplateResponse(
        request, "motions/detail.html", {"motion": motion}
    )
