class FormaterInterface:
    slug: str
    description: str

    @classmethod
    async def generate(cls) -> bytes:
        raise NotImplementedError  # pragma: nocover
