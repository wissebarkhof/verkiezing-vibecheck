from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Election, TopicComparison

router = APIRouter()


@router.get("/verkiezingen/{slug}/vergelijk")
def compare_topics(slug: str, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )
    comparisons = (
        db.query(TopicComparison)
        .filter(TopicComparison.election_id == election.id)
        .order_by(TopicComparison.topic_name)
        .all()
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "compare.html",
        {"election": election, "comparisons": comparisons},
    )
