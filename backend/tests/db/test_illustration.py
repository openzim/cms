import base64

import pytest
import xxhash
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import illustration as db_illustration
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Illustration


def test_create_illustration_stores_base64_and_digest(
    dbsession: OrmSession, illustration_48x48_at_1: str
):
    raw_data = base64.b64decode(illustration_48x48_at_1)

    illustration = db_illustration.create_illustration(
        dbsession, data=illustration_48x48_at_1
    )
    dbsession.flush()

    assert illustration.hex_digest == xxhash.xxh3_64_hexdigest(raw_data)
    assert illustration.data == illustration_48x48_at_1


def test_create_illustration_reuses_existing_row(
    dbsession: OrmSession, illustration_48x48_at_1: str
):
    first = db_illustration.create_illustration(dbsession, data=illustration_48x48_at_1)
    second = db_illustration.create_illustration(
        dbsession, data=illustration_48x48_at_1
    )
    dbsession.flush()

    assert first.hex_digest == second.hex_digest
    assert dbsession.scalar(select(func.count()).select_from(Illustration)) == 1


def test_get_illustration_or_none(dbsession: OrmSession, illustration_48x48_at_1: str):
    illustration = db_illustration.create_illustration(
        dbsession, data=illustration_48x48_at_1
    )
    dbsession.flush()

    assert (
        db_illustration.get_illustration_or_none(dbsession, illustration.hex_digest)
        is illustration
    )
    assert db_illustration.get_illustration_or_none(dbsession, "0" * 16) is None


def test_get_illustration_raises_when_missing(dbsession: OrmSession):
    with pytest.raises(RecordDoesNotExistError):
        db_illustration.get_illustration(dbsession, "0" * 16)


def test_extract_illustrations_from_metadata(
    dbsession: OrmSession, illustration_48x48_at_1: str
):
    metadata = {
        "Name": "test_en_all",
        "Illustration_48x48@1": illustration_48x48_at_1,
    }

    extracted = db_illustration.extract_illustrations_from_metadata(dbsession, metadata)
    dbsession.flush()

    assert "Illustration_48x48@1" not in extracted
    hex_digest = extracted["Illustration_48x48@1_hex_digest"]
    assert isinstance(hex_digest, str)
    assert db_illustration.get_illustration(dbsession, hex_digest).data == (
        illustration_48x48_at_1
    )
    assert extracted["Name"] == "test_en_all"

    # The caller's metadata is not mutated
    assert metadata["Illustration_48x48@1"] == illustration_48x48_at_1


def test_extract_illustrations_from_metadata_rejects_empty_value(
    dbsession: OrmSession,
):
    """Rejects an lustration metadata key with an empty value."""
    with pytest.raises(ValueError):
        db_illustration.extract_illustrations_from_metadata(
            dbsession, {"Illustration_48x48@1": ""}
        )
