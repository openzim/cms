from fastapi import APIRouter
from ormar.exceptions import NoMatch

from backend.models import Book, Title, database

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get(
    "",
    status_code=200,
    tags=["dashboard"],
    responses={
        200: {
            "description": "Condensed stats of zimcheck data",
        },
    },
)
@database.transaction()
async def ZimcheckDashboard():

    dic_scraper = {}
    keys = [
        "integrity",
        "empty",
        "metadata",
        "favicon",
        "main_page",
        "redundant",
        "url_internal",
        "url_external",
        "redirect",
    ]

    dict_totals = {key: 0 for key in keys}
    for title in await Title.objects.all():
        try:
            first_book = (
                await Book.objects.filter(title=title)
                .order_by("-period")
                .exclude_fields(["title", "counter", "languages", "tags"])
                .first()
            )
            scraper_name = await first_book.get_scraper_name()
        except NoMatch:
            continue

        if scraper_name not in dic_scraper:
            dic_scraper.update({scraper_name: {key: 0 for key in keys}})

        for log in first_book.zimcheck.get("logs"):
            check = log.get("check")
            dic_scraper[scraper_name][check] = (
                dic_scraper[scraper_name].get(check, 0) + 1
            )
            dict_totals[check] = dict_totals.get(check, 0) + 1

    return {"checkData": dic_scraper, "dictTotals": dict_totals}
