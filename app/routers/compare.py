from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Election, TopicComparison

router = APIRouter(prefix="/vergelijk")


@router.get("/")
def compare_topics(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    comparisons = []
    if election:
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
