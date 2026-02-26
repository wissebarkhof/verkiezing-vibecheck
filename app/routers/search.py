import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import Election
from app.services.search import search

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/verkiezingen/{slug}/zoeken")
@limiter.limit("10/minute")
def search_page(slug: str, request: Request, q: str = "", db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.slug == slug).first()
    if not election:
        return request.app.state.templates.TemplateResponse(
            request, "errors/404.html", {}, status_code=404
        )

    results = None
    if q.strip():
        try:
            results = search(db, q.strip(), election_id=election.id)
        except Exception:
            logger.exception("Search failed")
            results = {"answer": "Er ging iets mis bij het zoeken. Probeer het later opnieuw.", "sources": []}

    if request.headers.get("HX-Request"):
        return request.app.state.templates.TemplateResponse(
            request,
            "search_results.html",
            {"results": results, "query": q, "election": election},
        )

    return request.app.state.templates.TemplateResponse(
        request,
        "search.html",
        {"election": election, "query": q, "results": results},
    )
