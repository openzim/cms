from backend.models import Book, BookTag, Title, TitleTag


async def clear_book_dict_from(book_id: str, tags: str):
    book = await Book.objects.get(id=book_id)
    if book.title:
        title = await Title.objects.get(ident=book.title.ident)
        for language in await title.languages.all():
            await language.delete()
        await title.tags.clear(keep_reversed=False)
        await title.metadata.clear(keep_reversed=False)
        await title.books.clear()
        await title.delete()

    await book.languages.clear(keep_reversed=False)
    await book.tags.clear(keep_reversed=False)
    await book.metadata.clear(keep_reversed=False)
    await book.delete()

    await BookTag.objects.filter(name__in=tags.split(";")).delete()
    await TitleTag.objects.filter(name__in=tags.split(";")).delete()
