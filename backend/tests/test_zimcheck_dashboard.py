import pytest
from ormar.exceptions import NoMatch

from backend.models import Book
from backend.routes.zimcheck_dashboard import zim_check_dashboard


@pytest.mark.asyncio
async def test_zim_check_dashboard(client):
    response = await client.get("/v1/zimcheck")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == {"checkData": {}}


@pytest.mark.asyncio
async def test_zimcheck_dashboard_NoMatch(monkeypatch):
    def raise_NoMatch(*args, **kwargs):
        raise NoMatch("No match")

    monkeypatch.setattr(Book.objects, "first", raise_NoMatch)
    response = await zim_check_dashboard()
    assert response == {"checkData": {}}
