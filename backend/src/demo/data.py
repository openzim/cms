import asyncio

from backend.models import Title, database


@database.transaction()
async def load_fixture():
    await Title.objects.create(ident="wikipedia_en_test")
    await Title.objects.create(ident="wikipedia_hi_test")
    await Title.objects.create(ident="wikipedia_zh_test")
    await Title.objects.create(ident="wikipedia_et_test")
    await Title.objects.create(ident="wikipedia_fr_test")
    await Title.objects.create(ident="wikipedia_de_test")
    await Title.objects.create(ident="wikipedia_gu_test")
    await Title.objects.create(ident="wikipedia_lt_test")
    await Title.objects.create(ident="wikipedia_ml_test")
    await Title.objects.create(ident="wikipedia_no_test")
    print(await Title.objects.filter().count(), "titles in DB")


asyncio.run(load_fixture())
