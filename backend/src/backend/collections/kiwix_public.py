from typing import Iterator

from backend.collections import CollectionInterface
from backend.models import Title


class KiwixPublicCollection(CollectionInterface):
    async def get_book_ids(self) -> Iterator[str]:
        for title in (
            await Title.objects.exclude_fields(["tags", "languages"])
            .select_related("books")
            .all()
        ):
            flavours = []
            for book in (
                await title.books.exclude_fields(
                    ["title", "counter", "languages", "zimcheck", "tags"]
                )
                .select_related("metadata")
                .order_by("-period")
                .all()
            ):
                if not await book.metadata.filter(name="Flavour").exists():
                    if "" not in flavours:
                        flavours.append("")
                        yield book.id
                    continue
                flavour = (await book.metadata.get(name="Flavour")).value
                if flavour not in flavours:
                    flavours.append(flavour)
                    yield book.id
