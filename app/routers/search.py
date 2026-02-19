import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.services.search import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zoeken")


@router.get("/")
@limiter.limit("10/minute")
def search_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    results = None
    if q.strip():
        try:
            results = search(db, q.strip())
        except Exception:
            logger.exception("Search failed")
            results = {"answer": "Er ging iets mis bij het zoeken. Probeer het later opnieuw.", "sources": []}

    # If HTMX request, return only the results partial
    if request.headers.get("HX-Request"):
        return request.app.state.templates.TemplateResponse(
            request,
            "search_results.html",
            {"results": results, "query": q},
        )

    return request.app.state.templates.TemplateResponse(
        request,
        "search.html",
        {"query": q, "results": results},
    )
