from backend.main import shutdown, startup


def singlescript(func):
    async def inner():
        await startup()
        await func()
        await shutdown()

    return inner
