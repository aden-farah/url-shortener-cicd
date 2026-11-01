import logging
import secrets
import string
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.config import LOG_LEVEL
from app.db import get_db

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("url_shortener")

APP_DIRECTORY = Path(__file__).resolve().parent
MAX_SHORT_CODE_ATTEMPTS = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


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
            logger.warning("Short code collision, retrying")
            continue

        db.refresh(new_url)
        logger.info("Created short URL %s", new_url.short_code)
        return new_url

    logger.error(
        "Could not generate a unique short code after %d attempts",
        MAX_SHORT_CODE_ATTEMPTS,
    )
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


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Readiness check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable"},
        )

    return {"status": "ready"}


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
        logger.info("Short code not found: %r", short_code)
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    db.commit()

    return RedirectResponse(
        url=original_url,
        status_code=307,
    )