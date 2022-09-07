import pathlib
import tempfile

import openzim_uploader

from backend.collections.kiwix_public import KiwixPublicCollection
from backend.constants import BackendConf
from backend.exporters import ExporterInterface
from backend.formatters.kiwixlibraryxml import KiwixLibraryXml


class KiwixPublicExporter(ExporterInterface):
    async def exporte():
        src_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(src_path, "w") as f:
            f.write(await KiwixLibraryXml.generate(collection=KiwixPublicCollection()))

        await openzim_uploader.check_and_upload_file(
            src_path=src_path,
            upload_uri=BackendConf.upload_uri,
            private_key=BackendConf.private_key,
            delete=True,
        )
