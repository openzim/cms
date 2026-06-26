import base64
import io
import re
from typing import Any

from PIL import Image, ImageFile

from cms_backend import logger
from cms_backend.context import parse_bool
from cms_backend.schemas.orms import ZimcheckSummarySchema

# https://github.com/python-pillow/Pillow/issues/1510#issuecomment-151458026
ImageFile.LOAD_TRUNCATED_IMAGES = True


def get_missing_keys(payload: dict[str, Any], *keys: str) -> list[str]:
    """Get the list of missing keys from payload."""
    return [
        key
        for key in sorted(keys)
        if key not in payload or payload.get(key) in (None, "")
    ]


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
        "Illustration_48x48@1",
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


def parse_zimcheck_result(zimcheck: dict[str, Any]) -> ZimcheckSummarySchema:
    """Transform zimcheck result into a summary entry."""
    # Zimcheck results can either have a "result" or a "log" entry and not both.
    # When the result entry is set, it means the results is a valid JSON but if
    # the "log" is set, it means there was an error dumping the results as JSON and
    # everything is stored in the logs
    # https://github.com/openzim/zimfarm/blob/3161401f4e6ed902728b93595bde2956f38d099b/worker/src/zimfarm_worker/task/worker.py#L1173-L1180
    if zimcheck.get("result"):
        logs = zimcheck["result"]["logs"]
        warning_count = 0
        error_count = 0
        for log in logs:
            if log["level"] == "ERROR":
                error_count += 1
            elif log["level"] == "WARNING":
                warning_count += 1
        return ZimcheckSummarySchema(
            zimcheck_version=zimcheck["result"]["zimcheck_version"],
            status=zimcheck["result"]["status"],
            checks=zimcheck["result"]["checks"],
            error_count=error_count,
            warning_count=warning_count,
            retcode=zimcheck["retcode"],
        )
    elif zimcheck.get("log"):
        try:
            zimcheck_version_match = re.search(
                r'[\\]*"zimcheck_version[\\]*"\s*:\s*[\\]*"([^"\\]+)[\\]*"',
                zimcheck["log"],
            )
            status_match = re.search(
                r'[\\]*"status[\\]*"\s*:\s*([\\]*"?(?:true|false|[^,}]+)[\\]*"?)',
                zimcheck["log"],
            )
            checks_match = re.search(
                r'[\\]*"checks[\\]*"\s*:\s*\[(.*?)\](?=[,\}]|$)',
                zimcheck["log"],
                re.DOTALL,
            )

            warning_count = 0
            error_count = 0
            for match in re.findall(
                r'[\\]*"level[\\]*"\s*:\s*[\\]*["\']?([A-Z]+)[\\]*["\']?',
                zimcheck["log"],
                re.IGNORECASE,
            ):
                level = match.upper()
                if level == "ERROR":
                    error_count += 1
                elif level == "WARNING":
                    warning_count += 1

            return ZimcheckSummarySchema(
                zimcheck_version=zimcheck_version_match.group(1)
                if zimcheck_version_match
                else None,
                status=parse_bool(status_match.group(1)) if status_match else None,
                error_count=error_count,
                warning_count=warning_count,
                checks=[
                    check.strip().strip('"') for check in checks_match[1].split(",")
                ]
                if checks_match
                else None,
                retcode=zimcheck["retcode"],
            )
        except Exception:
            logger.exception("encountered error while parsing zimcheck logs")
    return ZimcheckSummarySchema()


def normalize_illustration(image_base64: str):
    image_bytes = base64.b64decode(image_base64, validate=True)
    image = Image.open(io.BytesIO(image_bytes))
    # Save image without any metadata
    buffer = io.BytesIO()
    new_img = Image.new(image.mode, image.size)
    new_img.putdata(image.get_flattened_data())
    new_img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()
