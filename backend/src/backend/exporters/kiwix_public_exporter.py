import pathlib
import tempfile

import openzim_uploader

from backend.collections.kiwix_public import KiwixPublicCollection
from backend.constants import BackendConf, logger
from backend.exporters import ExporterInterface
from backend.formatters.kiwixlibraryxml import KiwixLibraryXml


class KiwixPublicExporter(ExporterInterface):
    """
    Export kiwix library collection in kiwix xml and upload on
    the production server
    """

    src_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)

    @classmethod
    async def export(cls):
        try:
            with open(cls.src_path, "w") as f:
                f.write(
                    await KiwixLibraryXml.generate(collection=KiwixPublicCollection())
                )
        except Exception as exc:
            logger.warning("Export Failed for XML File")
            logger.exception(exc)
            return False
        return (
            openzim_uploader.check_and_upload_file(
                src_path=cls.src_path,
                upload_uri=BackendConf.upload_uri,
                private_key=BackendConf.private_key,
                delete=True,
            )
            == 0
        )
