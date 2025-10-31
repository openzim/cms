import datetime
from typing import Any

import pydantic
from pydantic import ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


def serialize_datetime(value: datetime.datetime) -> str:
    """Serialize datetime to ISO format with UTC indication.

    Naive datetimes are assumed to be UTC and get a 'Z' suffix.
    Timezone-aware datetimes are serialized with their timezone info.
    """
    if value.tzinfo is None:
        return value.isoformat(timespec="seconds") + "Z"
    return value.isoformat(timespec="seconds")


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: Any) -> Any:
        """Serialize datetime fields with proper timezone indication"""
        if isinstance(value, datetime.datetime):
            return serialize_datetime(value)
        return value


class WithExtraModel(BaseModel):
    """BaseModel with extra fields allowed"""

    model_config = ConfigDict(
        extra="allow",
    )


class CamelModel(BaseModel):
    """BaseModel with camelCase field aliases"""

    model_config = ConfigDict(
        alias_generator=to_camel,
    )


def to_kebab_case(string: str) -> str:
    return string.replace("_", "-")


class DashModel(BaseModel):
    """BaseModel with kebab-case field aliases"""

    model_config = ConfigDict(
        alias_generator=to_kebab_case,
    )
