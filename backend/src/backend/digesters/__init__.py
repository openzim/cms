class DigesterInterface:

    slug: str
    description: str
    status: str = "pending"

    @classmethod
    async def generate(cls) -> bytes:
        raise NotImplementedError
