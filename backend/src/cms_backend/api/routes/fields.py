from typing import Annotated, Any

import regex
from pydantic import (
    AfterValidator,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)


class GraphemeStr(str):
    def __len__(self) -> int:
        # Count the number of grapheme clusters
        return len(regex.findall(r"\X", self))


def to_grapheme_str(value: str):
    return GraphemeStr(value)


def no_null_char(value: str) -> str:
    """Validate that string value does not contains Unicode null character"""
    if "\u0000" in value:
        raise ValueError("Null character is not allowed")

    return value


def skip_validation(
    value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
) -> Any:
    """Skip pydantic validation"""
    context = info.context
    if context and context.get("skip_validation"):
        return value
    return handler(value)


def not_empty(value: str) -> str:
    """Validate that string value is not empty"""
    if not value.strip():
        raise ValueError("String value cannot be empty")

    return value.strip()


NoNullCharString = Annotated[
    str, AfterValidator(no_null_char), AfterValidator(to_grapheme_str)
]

NotEmptyString = Annotated[NoNullCharString, AfterValidator(not_empty)]

SkipField = Annotated[int, Field(ge=0), WrapValidator(skip_validation)]

LimitFieldMax200 = Annotated[int, Field(ge=1, le=200), WrapValidator(skip_validation)]
