from typing import Any


def get_missing_keys(payload: dict[str, Any], *keys: str) -> list[str]:
    """Get the list of missing keys from payload."""
    return [key for key in sorted(keys) if key not in payload or not payload.get(key)]


def get_missing_metadata_keys(zim_metadata: dict[str, Any]) -> list[str]:
    """Get the the list of missing metadata keys from a zim."""
    return get_missing_keys(
        zim_metadata,
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Date",
        "Description",
        "Language",
    )


def convert_tags(tags_str: str) -> list[str]:
    """List of tags expanded with libkiwix's additional hints for pic/vid/det/index

    Copied from https://github.com/openzim/python-scraperlib/blob/99047776f5998ef4244a78afb5499e2c23890c70/src/zimscraperlib/zim/_libkiwix.py#L92
    """
    tags = tags_str.split(";")
    tags_list: list[str] = []
    pic_seen = vid_seen = det_seen = index_seen = False
    for tag in tags:
        # not upstream
        if not tag:
            continue
        pic_seen |= tag == "nopic" or tag.startswith("_pictures:")
        vid_seen |= tag == "novid" or tag.startswith("_videos:")
        det_seen |= tag == "nodet" or tag.startswith("_details:")
        index_seen |= tag.startswith("_ftindex")

        if tag == "nopic":
            tags_list.append("_pictures:no")
        elif tag == "novid":
            tags_list.append("_videos:no")
        elif tag == "nodet":
            tags_list.append("_details:no")
        elif tag == "_ftindex":
            tags_list.append("_ftindex:yes")
        else:
            tags_list.append(tag)

    if not index_seen:
        tags_list.append("_ftindex:no")
    if not pic_seen:
        tags_list.append("_pictures:yes")
    if not vid_seen:
        tags_list.append("_videos:yes")
    if not det_seen:
        tags_list.append("_details:yes")
    return tags_list
