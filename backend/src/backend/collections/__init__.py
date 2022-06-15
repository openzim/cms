from typing import Iterator


class CollectionInterface:
    async def get_book_ids(self) -> Iterator[str]:
        raise NotImplementedError()

    async def get_size(self) -> int:
        raise NotImplementedError()
