import re
from pathlib import Path

import markdown as md_lib
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.routers import candidates, compare, elections, home, motions, parties, search

app = FastAPI(title="Verkiezing Vibecheck")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/logos", StaticFiles(directory=BASE_DIR.parent / "data" / "logos"), name="logos")
app.mount("/programs", StaticFiles(directory=BASE_DIR.parent / "data" / "programs"), name="programs")
app.state.templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _markdown(text: str) -> Markup:
    if not text:
        return Markup("")
    # Ensure a blank line before list items so the markdown library renders
    # them as <ul>/<li> rather than leaving "- " as literal paragraph text.
    processed = re.sub(r"([^\n])\n([-*+] |\d+\. )", r"\1\n\n\2", text)
    return Markup(md_lib.markdown(processed, extensions=["sane_lists"]))


app.state.templates.env.filters["markdown"] = _markdown

app.include_router(home.router)
app.include_router(elections.router)
app.include_router(parties.router)
app.include_router(candidates.router)
app.include_router(motions.router)
app.include_router(compare.router)
app.include_router(search.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return app.state.templates.TemplateResponse(
        request, "errors/404.html", {}, status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return app.state.templates.TemplateResponse(
        request, "errors/500.html", {}, status_code=500
    )
