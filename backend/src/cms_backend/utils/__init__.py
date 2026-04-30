from uuid import UUID


def is_valid_uuid(identifier: str) -> bool:
    """Check if string is a valid UUID"""
    try:
        UUID(identifier)
    except ValueError:
        return False
    return True
