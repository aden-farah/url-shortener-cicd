import pytest
from sqlalchemy.exc import OperationalError

from app.db import SessionLocal, get_db
from app.main import app, generate_short_code
from app.models import URL

EXAMPLE_URL = "https://example.com/some/page"


def create_short_url(client, url=EXAMPLE_URL):
    response = client.post("/shorten", json={"url": url})
    assert response.status_code == 201
    return response.json()


def test_health_returns_healthy(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_shorten_creates_short_url(client):
    data = create_short_url(client)

    assert data["original_url"] == EXAMPLE_URL
    assert len(data["short_code"]) == 6
    assert data["short_url"].endswith("/" + data["short_code"])
    assert data["click_count"] == 0


def test_redirect_goes_to_original_url(client):
    data = create_short_url(client)

    response = client.get(f"/{data['short_code']}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == EXAMPLE_URL


def test_redirect_increments_click_count(client):
    data = create_short_url(client)

    client.get(f"/{data['short_code']}", follow_redirects=False)
    client.get(f"/{data['short_code']}", follow_redirects=False)

    with SessionLocal() as db:
        url = db.query(URL).filter(URL.short_code == data["short_code"]).one()

    assert url.click_count == 2


def test_unknown_short_code_returns_404(client):
    response = client.get("/doesnotexist", follow_redirects=False)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad_url",
    ["not-a-url", "ftp://example.com/file", "javascript:alert(1)"],
)
def test_invalid_url_is_rejected(client, bad_url):
    response = client.post("/shorten", json={"url": bad_url})

    assert response.status_code == 422


def test_generate_short_code_uses_letters_and_digits():
    code = generate_short_code(10)

    assert len(code) == 10
    assert code.isalnum()


def test_shorten_retries_when_short_code_already_exists(client, monkeypatch):
    first = create_short_url(client)
    codes = iter([first["short_code"], "newcode1"])
    monkeypatch.setattr("app.main.generate_short_code", lambda length=6: next(codes))

    second = create_short_url(client, "https://example.com/other")

    assert second["short_code"] == "newcode1"


def test_shorten_returns_503_when_no_unique_code_found(client, monkeypatch):
    first = create_short_url(client)
    monkeypatch.setattr(
        "app.main.generate_short_code", lambda length=6: first["short_code"]
    )

    response = client.post("/shorten", json={"url": "https://example.com/other"})

    assert response.status_code == 503


def test_ready_returns_ready_when_database_is_up(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


class BrokenSession:
    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("database down"))


def test_ready_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
