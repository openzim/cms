import openzim_uploader
import pytest

from backend.exporters.kiwix_public_exporter import KiwixPublicExporter


@pytest.mark.asyncio
async def test_kiwix_public_exporter(monkeypatch):
    async def mock_check_and_upload_file(src_path, upload_uri, private_key, delete):
        # So as not to upload the server test file
        ...

    monkeypatch.setattr(
        openzim_uploader, "check_and_upload_file", mock_check_and_upload_file
    )

    await KiwixPublicExporter.kiwix_library_xml_exporter()
