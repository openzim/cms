import datetime
import re
import uuid
from typing import List, Optional, Tuple

import databases
import ormar
import pydantic
import sqlalchemy

from backend.constants import BackendConf

METADATA_MAX_LEN = 2048
KIND_TEXT: str = "text"
KIND_ILLUSTRATION: str = "illustration"
KIND_BINARY: str = "binary"
KINDS: Tuple[str] = (KIND_TEXT, KIND_ILLUSTRATION, KIND_BINARY)
ILLUSTRATION_PATTERN: str = (
    r"^Illustration_" r"(?P<height>\d+)x(?P<width>\d+)(@(?P<scale>\d+))?$"
)
BOOK_ONLY_METADATA = ("Counter", "Flavour")

database = databases.Database(databases.DatabaseURL(BackendConf.database_url))


class BaseMeta(ormar.ModelMeta):
    metadata = sqlalchemy.MetaData()
    database = database


class Language(ormar.Model):
    """Content Language

    Can't be represented solely by ZIM/Book metadata as `Language` can contain more
    than one value.

    Language name and native repr stored on creation"""

    class Meta(BaseMeta):
        tablename = "languages"

    code: str = ormar.String(primary_key=True, max_length=3)
    name: str = ormar.String(max_length=100)
    native: str = ormar.String(max_length=100)


class TagMixin:
    """ZIM Tag is a text slug stored along others in `Tags` metadata

    https://wiki.openzim.org/wiki/Tags"""

    name: str = ormar.String(primary_key=True, max_length=255)

    @property
    def private(self) -> bool:
        return self.name.startswith("_")


class TitleTag(ormar.Model, TagMixin):
    """Non-Book-specific Tags exposed on Title"""

    class Meta(BaseMeta):
        tablename = "titles_tags"


class BookTag(ormar.Model, TagMixin):
    """Original from-ZIM file Tags"""

    class Meta(BaseMeta):
        tablename = "books_tags"


class EntryMixin:
    @property
    def language(self):
        """Shortcut to first (usually only) language"""
        return self.languages.first()

    @property
    def illustrations(self) -> ormar.QuerySet:
        """Shortcut to Illustrations (stored as MetaData)"""
        return self.metadata.filter(name__startswith="Illustration_")

    @property
    def illustration(self) -> ormar.Model:
        """Shortcut to mandatory sized 48 Illustration"""
        return self.illustrations.get(name__exact="Illustration_48x48")

    async def get_illustration(self, size: int = 48) -> bytes:
        """Binary data for an Illustration, by size"""
        return (
            await self.illustrations.get(name__exact=f"Illustration_{size}x{size}")
        ).bin_value


class Title(ormar.Model, EntryMixin):
    """Shell around Books to customize user-facing metadata

    Copy of Book metadata that can be later edited and will serve as metadata
    base for exports.

    See: https://wiki.openzim.org/wiki/Metadata"""

    class Meta(BaseMeta):
        tablename = "titles"

    # book identifier ~ recipe
    ident: str = ormar.String(primary_key=True, max_length=255)

    # most are single language but spec allows multiple ones
    languages: Optional[List[Language]] = ormar.ManyToMany(
        Language, related_name="titles"
    )
    tags: Optional[List[TitleTag]] = ormar.ManyToMany(TitleTag, related_name="titles")


class Book(ormar.Model, EntryMixin):
    """Actual ZIM file's details

    Archive of actual metadata stored in a ZIM file (set on ZIM creation).
    Serves as source to feed Title creation"""

    class Meta(BaseMeta):
        tablename = "books"

    # ZIM UUID
    id: uuid.UUID = ormar.UUID(primary_key=True, uuid_format="string")
    # parsed/filetrable data from metadata
    period: datetime.date = ormar.Date()
    counter: pydantic.Json = ormar.JSON()
    languages: Optional[List[Language]] = ormar.ManyToMany(
        Language, related_name="books"
    )
    tags: Optional[List[BookTag]] = ormar.ManyToMany(BookTag, related_name="books")

    # non-metadata exposed info built from Reader::getArticleCount()
    article_count: int = ormar.Integer()
    # non-metadata exposed info built from getArchiveMediaCount
    media_count: int = ormar.Integer()
    # non-metadata exposed info built from getArchiveFileSize
    size: int = ormar.BigInteger()

    # ingester-provided non-metadata
    url: pydantic.HttpUrl = ormar.String(max_length=2083)
    zimcheck: pydantic.Json = ormar.JSON()

    # not sure yet if should be Optional or not
    title: Optional[Title] = ormar.ForeignKey(Title, related_name="books")

    async def book_name(self) -> str:
        try:
            return (await self.metadata.get(name="Name")).value
        except ormar.exceptions.NoMatch:
            # if the book doesn't have metadata Name
            return ""


class MetadataMixin:
    """ZIM Metadata

    ZIM Metadata are unique for an Entry and a Name.
    ex: Book#2 can only have one `Name` Metadata.

    Metadata kind (text, illustration or binary) allows filtering-out
    non-text Metadata which are rare (beside illustration)"""

    id: int = ormar.Integer(primary_key=True)
    name: str = ormar.String(max_length=METADATA_MAX_LEN)
    kind: str = ormar.String(max_length=50, choices=KINDS)
    value: str = ormar.String(max_length=METADATA_MAX_LEN, default="")
    bin_value: Optional[bytes] = ormar.LargeBinary(
        max_length=2**20 * 2, represent_as_base64_str=False, default=b""
    )  # 2MiB

    @property
    def size(self) -> int:
        """Size (width) as exposed by libzim"""
        if self.kind != KIND_ILLUSTRATION:
            return
        m = re.match(ILLUSTRATION_PATTERN, self.name)
        if not m:
            return
        return int(m.groupdict(1)["width"])


class BookMetadata(ormar.Model, MetadataMixin):
    """Metadata associated with a Book

    Book Metadata represents Metadata stored in ZIM file"""

    class Meta(BaseMeta):
        tablename = "books_metadata"
        constraints = [ormar.UniqueColumns("name", "book")]

    book: Book = ormar.ForeignKey(Book, related_name="metadata")


class TitleMetadata(ormar.Model, MetadataMixin):
    """Metadata associated with a Title

    Titles don't have to expose as many Metadata as Books.
    Titles Metadata are meant to be edited/improved."""

    class Meta(BaseMeta):
        tablename = "titles_metadata"
        constraints = [ormar.UniqueColumns("name", "title")]

    title: Title = ormar.ForeignKey(Title, related_name="metadata")


async def get_matched_m2m_combination(
    on: str, items: List[str], combination: str = "intersection"
) -> List[str]:
    """Ids of requested model matching a combination of values on many2many column

    params:
        on: a {model}-{collection} string to indiquate which model and m2m colums
        are being queried.
        model is either `title` or `book`; collection is either `language` or `tag`

        items: list of pk from the m2m target that must all be present to match

    Sample uses:
        get list of titles ident for which the m2m has eng and french language:
            on="title-language", items=["eng", "fra"]
        get list of books uuids for which the m2m has "wiki", "new" and "kid" tags:
            on="book-tag", items=["wiki", "new", "kid"]"""
    model_name, collection_name = on.lower().split("-", 1)
    if model_name not in ("title", "book") or collection_name not in (
        "language",
        "tag",
        "titletag",
    ):
        raise ValueError("Invalid m2m combination request")
    if combination not in ("intersection", "union"):
        raise ValueError("Invalid m2m combination operator request")
    count_condition = "= :nbitems" if combination == "intersection" else ">= 1"

    if model_name == "title":
        model = Title
        id_field = "ident"
        lookup_field = "title"
    # elif on == "book":
    #     model = Book
    #     id_field = "uuid"
    #     lookup_field = "book"
    coll_lookup_field = collection_name
    # fine as long as there's no customed-table-name for the through model
    through_tablename = f"{model.Meta.tablename}_{collection_name}s"

    # expanding bound params alternative (https://stackoverflow.com/a/25168069/631925)
    params = {f"item{idx}": item for idx, item in enumerate(items)}
    where = f"{coll_lookup_field} in (:" + ", :".join(params.keys()) + ")"
    stmt = (
        f"SELECT {model.Meta.tablename}.{id_field} "
        f"FROM {model.Meta.tablename}, "
        f"(SELECT DISTINCT {lookup_field}, COUNT({coll_lookup_field}) as nbi "
        f"FROM {through_tablename} WHERE {where} "
        f"GROUP BY {lookup_field}) tmp "
        f"WHERE {model.Meta.tablename}.{id_field} = tmp.{lookup_field} "
        f"AND tmp.nbi {count_condition};"
    )
    if combination == "intersection":
        params["nbitems"] = len(items)
    return [row[0] for row in await database.fetch_all(stmt, params)]


async def reduce_qs(queryset, on: str = "ident") -> List[str]:
    """executes a queryset and return identifiers as list for later reuse"""
    return [getattr(item, on) for item in await queryset.all()]


async def matching_metadata(
    on: str, name: str, value: str, using: Optional[List[str]] = None
):
    model_name = on
    lookup_field = model_name
    if using:
        params = {f"item{idx}": item for idx, item in enumerate(using)}
        in_clause = f"{lookup_field} in (:" + ", :".join(params.keys()) + ") AND "
    else:
        params = {}
        in_clause = ""

    stmt = (
        f"SELECT DISTINCT xm.{lookup_field} "
        f"FROM {model_name}s_metadata xm "
        f"WHERE {in_clause} "
        "xm.name = :name AND xm.value LIKE :value "
        f"GROUP BY xm.{lookup_field};"
    )
    params["name"] = name
    params["value"] = value
    return [row[0] for row in await database.fetch_all(stmt, params)]


def star_to_like(query: str):
    return query.replace("%", r"\%").replace("*", "%")
