from fastapi import APIRouter

from backend.models import Book, database

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
    # books = await Book.objects.all()
    return {
        # "books": [{"id": book.id, "name": await book.book_name()} for book in books],
        "totalBook": await Book.objects.count(),
    }
