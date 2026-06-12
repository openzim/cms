from cms_backend.db.models import Title


def get_title_flavours(title: Title) -> list[str]:
    return [title_flavour.flavour for title_flavour in title.flavours]
