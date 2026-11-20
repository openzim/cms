import base64
import binascii
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import xxhash
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Illustration
from cms_backend.utils.zim import (
    ILLUSTRATION_HEX_DIGEST_SUFFIX,
    ILLUSTRATION_METADATA_PREFIX,
)

HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def compute_hex_digest(data: str) -> str:
    """Compute the hexadecimal digest of a base64 encoded illustration."""
    return xxhash.xxh3_64_hexdigest(decode_illustration(data))


def is_hex_digest(value: str | None) -> bool:
    """Whether a value looks like an xxh3_64 hexadecimal digest."""
    return value is not None and HEX_DIGEST_PATTERN.fullmatch(value) is not None


def decode_illustration(value: str) -> bytes:
    """Decode a base64 encoded illustration."""
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid base64 illustration: {exc}") from exc


def get_illustration_or_none(
    session: OrmSession, hex_digest: str
) -> Illustration | None:
    return session.scalars(
        select(Illustration).where(Illustration.hex_digest == hex_digest)
    ).one_or_none()


def get_illustration(session: OrmSession, hex_digest: str) -> Illustration:
    illustration = get_illustration_or_none(session, hex_digest)
    if illustration is None:
        raise RecordDoesNotExistError(f"Illustration '{hex_digest}' does not exist")
    return illustration


def create_illustration(session: OrmSession, *, data: str) -> Illustration:
    """Store a base64 encoded illustration and return its record.

    Illustration rows are content-addressed so an existing row is reused when
    the same illustration has already been stored.
    """
    hex_digest = compute_hex_digest(data)
    if (illustration := get_illustration_or_none(session, hex_digest)) is not None:
        return illustration

    illustration = Illustration(hex_digest=hex_digest, data=data)
    session.add(illustration)
    return illustration


def resolve_illustration_hex_digest(
    session: OrmSession, value: str | None
) -> str | None:
    """Turn an illustration payload into the digest of a stored illustration.

    The value is either a hexadecimal digest referencing an existing
    illustration (used by promotion actions and history reverts) or a base64
    encoded image (used by the UI when uploading a new illustration).
    """
    if value is None:
        return None

    if is_hex_digest(value) and get_illustration_or_none(session, value) is not None:
        return value

    return create_illustration(session, data=value).hex_digest


def extract_illustrations_from_metadata(
    session: OrmSession, zim_metadata: dict[str, Any]
) -> dict[str, Any]:
    """Move base64 illustrations out of ZIM metadata and reference their digest.

    Incoming zimfarm metadata contains raw illustrations under keys such as
    ``Illustration_48x48@1``. They are stored in the illustration table and
    replaced by a ``<key>_hex_digest`` entry.
    """
    updated_metadata: dict[str, Any] = deepcopy(zim_metadata)

    for key in list(updated_metadata):
        if not key.startswith(ILLUSTRATION_METADATA_PREFIX):
            continue
        if key.endswith(ILLUSTRATION_HEX_DIGEST_SUFFIX):
            continue

        value = updated_metadata.pop(key)
        if value in (None, ""):
            raise ValueError(f"{key} in zim metadata has no value")

        updated_metadata[f"{key}{ILLUSTRATION_HEX_DIGEST_SUFFIX}"] = (
            resolve_illustration_hex_digest(session, str(value))
        )

    return updated_metadata


def get_illustration_metadata_hex_digest(
    zim_metadata: Mapping[str, Any], key: str
) -> str | None:
    """Get the digest stored for a ZIM Illustration metadata key."""
    value = zim_metadata.get(f"{key}{ILLUSTRATION_HEX_DIGEST_SUFFIX}")
    return str(value) if value is not None else None
