import base64
from dataclasses import dataclass
from typing import Annotated, Any

import pycountry
import regex
from pydantic import (
    AfterValidator,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)


@dataclass(frozen=True)
class GraphemeLength:
    min: int | None = None
    max: int | None = None

    def __call__(self, v: str, info: ValidationInfo) -> str:
        context = info.context
        if context and context.get("skip_validation"):
            return v
        n = len(regex.findall(r"\X", v))
        if self.min is not None and n < self.min:
            raise ValueError(
                f"String should have at least {self.min} grapheme clusters (got {n})"
            )
        if self.max is not None and n > self.max:
            raise ValueError(
                f"String should have at most {self.max} grapheme clusters (got {n})"
            )
        return v


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


def validate_language_code(value: str | None, info: ValidationInfo) -> str | None:
    """Validate that string is a valid ISO-693-3 language code"""
    if value is None:
        return value
    context = info.context
    if context and context.get("skip_validation"):
        return value

    if pycountry.languages.get(alpha_3=value):  # pyright: ignore[reportUnknownMemberType]
        return value
    raise ValueError(
        f"Language code '{value}' is not a supported ISO-639-3 language code"
    )


def validate_comma_separated_lang_code(
    value: str | None, info: ValidationInfo
) -> str | None:
    """Validate that string is a comma separated list of ISO-693-3 language codes"""
    if value is None:
        return value
    for lang_code in value.split(","):
        validate_language_code(lang_code, info)
    return value


def validate_zim_flavour(value: str, info: ValidationInfo):
    if not value:
        return value
    context = info.context
    if context and context.get("skip_validation"):
        return value
    if not value.isalpha():
        raise ValueError("Flavour '{value}' must only contain alphabetic characters.")
    return value


LangCode = Annotated[
    str,
    WrapValidator(skip_validation),
    AfterValidator(validate_comma_separated_lang_code),
]

ZimFlavour = Annotated[
    NotEmptyString,
    WrapValidator(skip_validation),
    AfterValidator(validate_zim_flavour),
]
