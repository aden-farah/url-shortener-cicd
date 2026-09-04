import secrets
import string
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app import models
from app.db import Base, engine, get_db

APP_DIRECTORY = Path(__file__).resolve().parent

app = FastAPI(title="URL Shortener API")

app.mount(
    "/static",
    StaticFiles(directory=APP_DIRECTORY / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=APP_DIRECTORY / "templates",
)

Base.metadata.create_all(bind=engine)


class URLRequest(BaseModel):
    url: HttpUrl


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


def generate_unique_short_code(
    db: Session,
    length: int = 6,
) -> str:
    while True:
        short_code = generate_short_code(length)

        existing_url = (
            db.query(models.URL)
            .filter(models.URL.short_code == short_code)
            .first()
        )

        if existing_url is None:
            return short_code


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/shorten", status_code=201)
def shorten_url(
    payload: URLRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    short_code = generate_unique_short_code(db)
    original_url = str(payload.url)

    new_url = models.URL(
        original_url=original_url,
        short_code=short_code,
    )

    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    base_url = str(request.base_url).rstrip("/")

    return {
        "original_url": new_url.original_url,
        "short_code": new_url.short_code,
        "short_url": f"{base_url}/{new_url.short_code}",
        "click_count": new_url.click_count,
    }


@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    url = (
        db.query(models.URL)
        .filter(models.URL.short_code == short_code)
        .first()
    )

    if url is None:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    url.click_count += 1
    db.commit()

    return RedirectResponse(
        url=url.original_url,
        status_code=307,
    )