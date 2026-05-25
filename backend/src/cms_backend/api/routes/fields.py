import base64
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)


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


def validate_base64(value: str) -> str:
    """Validate that a string is a base64 string."""
    try:
        base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 string: {exc}") from exc
    return value


NoNullCharString = Annotated[str, AfterValidator(no_null_char)]

NotEmptyString = Annotated[NoNullCharString, AfterValidator(not_empty)]

SkipField = Annotated[int, Field(ge=0), WrapValidator(skip_validation)]

LimitFieldMax200 = Annotated[int, Field(ge=1, le=200), WrapValidator(skip_validation)]

Base64Str = Annotated[NotEmptyString, AfterValidator(validate_base64)]
