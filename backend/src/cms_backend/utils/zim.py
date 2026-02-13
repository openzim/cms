from typing import Any


def get_missing_metadata_keys(zim_metadata: dict[str, Any]) -> list[str]:
    """Get the the list of missing metadata keys from a zim."""
    return [
        key
        for key in sorted(
            [
                "Name",
                "Title",
                "Creator",
                "Publisher",
                "Date",
                "Description",
                "Language",
            ]
        )
        if key not in zim_metadata or not zim_metadata.get(key)
    ]
