import openzim_uploader
import pytest

from backend.exporters import ExporterInterface
from backend.exporters.kiwix_public_exporter import KiwixPublicExporter


@pytest.mark.asyncio
async def test_exporter_interface():

    with pytest.raises(NotImplementedError):
        for _ in await ExporterInterface().exporter():
            ...


@pytest.mark.asyncio
async def test_kiwix_public_exporter(monkeypatch):
    async def mock_upload_file(
        src_path,
        upload_uri,
        private_key,
        username=None,
        resume=False,
        watch=None,
        move=False,
        delete=False,
        compress=False,
        bandwidth=None,
        cipher=None,
        delete_after=None,
    ):
        # So as not to upload the server test file
        ...

    monkeypatch.setattr(openzim_uploader, "upload_file", mock_upload_file)

    await KiwixPublicExporter.exporte()
