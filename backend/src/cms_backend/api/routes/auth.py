from typing import Annotated

from fastapi import APIRouter, Depends

from cms_backend.api.routes.dependencies import get_current_user
from cms_backend.db.models import User
from cms_backend.db.user import create_user_schema
from cms_backend.schemas.orms import UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserSchema:
    """Get the current authenticated user's information including scopes."""
    return create_user_schema(current_user)
