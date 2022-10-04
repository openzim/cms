import pathlib
import tempfile

import openzim_uploader

from backend.collections.kiwix_public import KiwixPublicCollection
from backend.constants import BackendConf, logger
from backend.exporters import ExporterInterface
from backend.formatters.kiwixlibraryxml import KiwixLibraryXml


class KiwixPublicExporter(ExporterInterface):
    """Upload XML Kiwix Library to `UPLOAD_URI`, using `PRIVATE_KEY"""

    async def export():

        src_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)

        try:
            with open(src_path, "w") as f:
                f.write(
                    await KiwixLibraryXml.generate(collection=KiwixPublicCollection())
                )
        except Exception as exc:
            logger.warning(
                f"Failed to write temporary KiwixPublicExporter file to {src_path}"
            )
            logger.exception(exc)
            return False
        try:
            return (
                openzim_uploader.check_and_upload_file(
                    src_path=src_path,
                    upload_uri=BackendConf.upload_uri,
                    private_key=BackendConf.private_key,
                    delete=True,
                )
                == 0
            )
        except Exception as exc:
            logger.warning(f"Failed openzim_uploader : {exc}")
            logger.exception(exc)
            return False
