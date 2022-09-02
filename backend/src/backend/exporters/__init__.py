import pathlib
import tempfile

import openzim_uploader

from backend.constants import BackendConf


async def exporter(data):
    src_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False).name)
    with open(src_path, "w") as f:
        f.write(data)
        f.close()

    await openzim_uploader.check_and_upload_file(
        src_path=src_path,
        upload_uri=BackendConf.upload_uri,
        private_key=BackendConf.private_key,
        delete=True,
    )
