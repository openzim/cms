from fastapi import APIRouter
from ormar.exceptions import NoMatch

from backend.models import Book, Title, database

router = APIRouter(
    prefix="/zimcheck",
    tags=["zimcheck"],
)


@router.get(
    "",
    status_code=200,
    tags=["zimcheck"],
    responses={
        200: {
            "description": "Overview of Zimcheck data",
        },
    },
)
@database.transaction()
async def zim_check_dashboard():
    scraper_data = {}

    def increment(scraper: str, check: str):
        if scraper not in scraper_data:
            scraper_data[scraper] = {}
        if check not in scraper_data[scraper]:
            scraper_data[scraper][check] = 0
        scraper_data[scraper][check] += 1

    for title in await Title.objects.all():
        try:
            last_book = (
                await Book.objects.filter(title=title)
                .order_by("-period")
                .exclude_fields(
                    [
                        "title",
                        "counter",
                        "languages",
                        "tags",
                    ]
                )
                .first()
            )
        except NoMatch:
            continue

        scraper = await last_book.get_scraper_name()
        for log in last_book.zimcheck.get("logs", []):
            increment(scraper, log.get("check", "Unknown"))

    return {"checkData": scraper_data}
