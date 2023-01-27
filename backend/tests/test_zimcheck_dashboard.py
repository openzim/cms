import pytest


@pytest.mark.asyncio
async def test_zim_check_dashboard(client, book_dict_with_logs, title_without_book):

    response = await client.get("/v1/zimcheck")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    # empty string means there is no Scraper metadata
    assert response.json() == {"checkData": {"": {"redundant": 2, "empty": 1}}}
