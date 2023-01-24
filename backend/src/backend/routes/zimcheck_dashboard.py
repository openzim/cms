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
async def zim_check_dashboard():

    dic_checks = {}
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

    dict_total_checks = {key: 0 for key in keys}
    for title in await Title.objects.all():
        try:
            last_book = (
                await Book.objects.filter(title=title)
                .order_by("-period")
                .exclude_fields(["title", "counter", "languages", "tags"])
                .first()
            )
        except NoMatch:
            continue

        scraper_name = await last_book.get_scraper_name()
        if scraper_name not in dic_checks:
            dic_checks.update({scraper_name: {key: 0 for key in keys}})

        for log in last_book.zimcheck.get("logs"):
            check = log.get("check")
            dic_checks[scraper_name][check] = dic_checks[scraper_name].get(check, 0) + 1
            dict_total_checks[check] = dict_total_checks.get(check, 0) + 1

    return {"checkData": dic_checks, "checkTotals": dict_total_checks}
