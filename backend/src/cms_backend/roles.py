from enum import StrEnum
from typing import Any, ClassVar


class Permissions:
    names: ClassVar[list[str]] = []

    @classmethod
    def get(cls, **kwargs: Any) -> dict[str, bool]:
        return {perm: kwargs.get(perm, False) for perm in cls.names}

    @classmethod
    def get_all(cls) -> dict[str, bool]:
        return cls.get(**dict.fromkeys(cls.names, True))


class ResourcePermissions(Permissions):
    names: ClassVar[list[str]] = ["create", "read", "update", "delete"]


class RoleEnum(StrEnum):
    EDITOR = "editor"
    VIEWER = "viewer"
    ZIMFARM = "zimfarm"


ROLES: dict[str, dict[str, dict[str, bool]]] = {
    RoleEnum.VIEWER: {},
    RoleEnum.EDITOR: {
        "book": ResourcePermissions.get_all(),
        "title": ResourcePermissions.get_all(),
        "zimfarm_notification": ResourcePermissions.get_all(),
    },
    RoleEnum.ZIMFARM: {
        "zimfarm_notification": ResourcePermissions.get(read=True, create=True),
    },
}


def merge_scopes(
    user_scope: dict[str, dict[str, bool]], all_scopes: dict[str, dict[str, bool]]
) -> dict[str, dict[str, bool]]:
    """Combine user scope and all scopes populating missing user scopes with False."""
    merged: dict[str, dict[str, bool]] = {}

    for category, permissions in all_scopes.items():
        merged[category] = {}
        user_permissions = user_scope.get(category, {})

        for perm, _ in permissions.items():
            merged[category][perm] = user_permissions.get(perm, False)

    return merged
