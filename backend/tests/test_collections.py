import pytest

from backend.collections import CollectionInterface
from backend.collections.kiwix_public import KiwixPublicCollection
from backend.models import Book


@pytest.mark.asyncio
async def test_collection_interface():
    with pytest.raises(NotImplementedError):
        for _ in await CollectionInterface().get_book_ids():
            ...

    with pytest.raises(NotImplementedError):
        for _ in await CollectionInterface().get_size():
            ...


@pytest.mark.asyncio
async def test_kiwix_public(titles_with_metadata_books):
    books_ids = KiwixPublicCollection().get_book_ids()
    async for book_id in books_ids:
        assert await Book.objects.filter(id=book_id).exists()
