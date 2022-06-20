from typing import Iterator

from backend.collections import CollectionInterface
from backend.models import Book


class KiwixPublicCollection(CollectionInterface):
    async def get_book_ids(self) -> Iterator[str]:
        """placeholder collection (See #75)"""
        for book in await Book.objects.all():
            yield book.id

    async def get_size(self) -> int:
        return await Book.objects.count()
