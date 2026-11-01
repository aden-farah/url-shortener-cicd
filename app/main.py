import secrets
import string
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.db import Base, engine, get_db

APP_DIRECTORY = Path(__file__).resolve().parent
MAX_SHORT_CODE_ATTEMPTS = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="URL Shortener API", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=APP_DIRECTORY / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=APP_DIRECTORY / "templates",
)


class URLRequest(BaseModel):
    url: HttpUrl


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


def create_url_with_unique_code(
    db: Session,
    original_url: str,
) -> models.URL:
    for _ in range(MAX_SHORT_CODE_ATTEMPTS):
        new_url = models.URL(
            original_url=original_url,
            short_code=generate_short_code(),
        )
        db.add(new_url)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue

        db.refresh(new_url)
        return new_url

    raise HTTPException(
        status_code=503,
        detail="Could not create a short URL, please try again",
    )


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
    new_url = create_url_with_unique_code(db, str(payload.url))

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
    result = db.execute(
        update(models.URL)
        .where(models.URL.short_code == short_code)
        .values(click_count=models.URL.click_count + 1)
        .returning(models.URL.original_url)
    )
    original_url = result.scalar_one_or_none()

    if original_url is None:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    db.commit()

    return RedirectResponse(
        url=original_url,
        status_code=307,
    )