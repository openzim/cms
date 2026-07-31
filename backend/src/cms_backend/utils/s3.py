import datetime
import math
import pathlib
import urllib.parse
from typing import Any, cast

from kiwixstorage import (  # pyright: ignore[reportMissingTypeStubs]
    AuthenticationError,
    KiwixStorage,
)

from cms_backend.schemas.models import PartEtag, PresignedUrlPart, S3MultipartUpload


def rebuild_uri(uri: urllib.parse.ParseResult, scheme: str | None = None):
    netloc = ""
    scheme = scheme or uri.scheme
    if uri.username:
        netloc += uri.username
    if uri.password:
        netloc += f":{uri.password}"
    if uri.username or uri.password:
        netloc += "@"
    if uri.hostname:
        netloc += uri.hostname
    if uri.port:
        netloc += f":{uri.port}"
    return urllib.parse.urlparse(
        urllib.parse.urlunparse(
            [scheme, netloc, uri.path, uri.fragment, uri.query, uri.fragment]
        )
    )


def get_kiwix_storage_client(uri: str):
    try:
        upload_uri = urllib.parse.urlparse(uri)
        pathlib.Path(upload_uri.path)
    except Exception as exc:
        raise ValueError(f"invalid upload URI: `{uri}`") from exc

    def get_url_scheme(url: urllib.parse.ParseResult) -> str:
        if url.scheme.startswith("s3"):
            if url.scheme.startswith("s3+https"):
                return "https"
            elif url.scheme.startswith("s3+http"):
                return "http"
            return "https"
        else:
            raise ValueError(f"Unsupported URL scheme in: {url}")

    s3 = KiwixStorage(
        rebuild_uri(upload_uri, scheme=get_url_scheme(upload_uri)).geturl()
    )
    if not s3.check_credentials(  # pyright: ignore[reportUnknownMemberType]
        list_buckets=True, delete=True
    ):
        raise AuthenticationError("check_credentials failed")

    return s3


def generate_view_presigned_url(
    s3: KiwixStorage,
    key: str,
    expires_in: datetime.timedelta = datetime.timedelta(days=7),
) -> str:
    """Generate a presigned URL for read access to file"""
    return cast(
        str,
        s3.client.generate_presigned_url(  # pyright: ignore[reportUnknownMemberType]
            ClientMethod="get_object",
            Params={"Bucket": s3.bucket_name, "Key": key},
            ExpiresIn=expires_in.total_seconds(),
        ),
    )


def generate_multipart_upload_presigned_urls(
    s3: KiwixStorage,
    *,
    key: str,
    filesize: int,
    chunk_size: int,
    upload_id: str | None = None,
    expires_in: datetime.timedelta = datetime.timedelta(days=1),
) -> S3MultipartUpload:
    """Generate presigned URLs for upload to S3 bucket"""
    if upload_id is None:
        response = cast(
            dict[str, Any],
            s3.client.create_multipart_upload(Bucket=s3.bucket_name, Key=key),  # pyright: ignore[reportUnknownMemberType]
        )
        upload_id = cast(str, response["UploadId"])

    num_parts = math.ceil(filesize / chunk_size)
    presigned_urls: list[PresignedUrlPart] = []
    for part_number in range(1, num_parts + 1):
        url = cast(
            str,
            s3.client.generate_presigned_url(  # pyright: ignore[reportUnknownMemberType]
                ClientMethod="upload_part",
                Params={
                    "Bucket": s3.bucket_name,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": part_number,
                },
                ExpiresIn=expires_in.total_seconds(),
            ),
        )
        presigned_urls.append(PresignedUrlPart(part_number=part_number, url=url))
    return S3MultipartUpload(
        upload_id=upload_id,
        key=key,
        bucket=s3.bucket_name,
        num_parts=num_parts,
        presigned_urls=presigned_urls,
    )


def complete_multipart_upload(
    s3: KiwixStorage, *, key: str, parts: list[PartEtag], upload_id: str
):
    sorted_parts = sorted(parts, key=lambda v: v.part_number)
    s3.client.complete_multipart_upload(  # pyright: ignore[reportUnknownMemberType]
        Bucket=s3.bucket_name,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"PartNumber": part.part_number, "ETag": part.etag}
                for part in sorted_parts
            ]
        },
    )
