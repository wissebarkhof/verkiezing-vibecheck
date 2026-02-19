import yaml
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Election, Party

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    elections = db.query(Election).order_by(Election.date).all()
    return request.app.state.templates.TemplateResponse(
        request,
        "home.html",
        {"elections": elections},
    )


@router.get("/programmas")
def programs_page(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).first()
    parties = []
    if election:
        parties = (
            db.query(Party)
            .filter(Party.election_id == election.id)
            .order_by(Party.current_seats.desc().nullslast(), Party.name)
            .all()
        )

    # Build name → PDF URL map from YAML (program_pdf not stored in DB)
    pdf_map: dict[str, str] = {}
    config_path = settings.election_config_path
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        for p in config.get("parties", []):
            if p.get("program_pdf"):
                pdf_map[p["name"]] = "/" + p["program_pdf"]

    return request.app.state.templates.TemplateResponse(
        request,
        "programmas.html",
        {"election": election, "parties": parties, "pdf_map": pdf_map},
    )
