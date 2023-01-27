import asyncio
import csv
import datetime
import sys

import requests

from backend.models import Book
from scripts import singlescript


@singlescript
async def check_url():
    """
    args: all
    """

    missing_book_urls = []
    nb_book = 0
    nb_missing_book = 0

    for book in await Book.objects.exclude_fields(
        ["title", "counter", "languages", "zimcheck"]
    ).all():
        nb_book += 1
        url = book.url
        response = requests.head(url)
        if "all" not in sys.argv[1:]:
            if not is_expired(book.period):
                print(book.id, "Is not expired")
                continue
        if response.status_code == 404:
            missing_book_urls.append([nb_book, book.id, url])
            nb_missing_book += 1
            print(book.id, "GONE")
        else:
            print(book.id, "OK")

    print(f"{nb_missing_book} / {nb_book}")
    write_to_csv("missing_books_urls.csv", ["Num", "ID", "URL"], missing_book_urls)


def is_expired(period):
    today = datetime.date.today()
    limit_month = today.replace(day=1) - datetime.timedelta(days=1)
    current_year = today.year
    if (current_year - period.year) == 0:
        if period.month >= limit_month.month:
            return False
    if (current_year - period.year) > 10:
        return False
    return True


def write_to_csv(filename, header, data):
    print(f"Write {filename} file to csv.")
    with open(f"{filename}", "w", newline="") as csvfile:
        write = csv.writer(csvfile)
        write.writerows([header])
        write.writerows(data)


if __name__ == "__main__":
    asyncio.run(check_url())
