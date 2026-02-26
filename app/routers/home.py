from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Election

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    elections = db.query(Election).order_by(Election.date).all()
    return request.app.state.templates.TemplateResponse(
        request,
        "home.html",
        {"elections": elections},
    )
