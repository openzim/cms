import tempfile

import openzim_uploader
import pytest

from backend.constants import BackendConf
from backend.exporters import ExporterInterface
from backend.exporters.kiwix_public_exporter import KiwixPublicExporter


@pytest.mark.asyncio
async def test_exporter_interface():
    with pytest.raises(NotImplementedError):
        for _ in await ExporterInterface().export():
            ...


@pytest.mark.asyncio
async def test_incorrect_path(monkeypatch):
    def mock_named_temporary_file(delete=False):
        class MockNamedTemporaryFile(object):
            def __init__(self, *args, **kwargs):
                self.name = "/fakefile"

        return MockNamedTemporaryFile()

    with monkeypatch.context() as mp:
        mp.setattr(tempfile, "NamedTemporaryFile", mock_named_temporary_file)
        assert not await KiwixPublicExporter.export()


@pytest.mark.asyncio
async def test_incorrect_rsa_key(monkeypatch, ssh_private_key):
    with monkeypatch.context() as mp:
        mp.setattr(BackendConf, "private_key", ssh_private_key)
    assert not await KiwixPublicExporter.export()


@pytest.mark.asyncio
async def test_incorrect_url(monkeypatch):
    with monkeypatch.context() as mp:
        mp.setattr(BackendConf, "upload_uri", "sftps://localhost:8080/data/test/")
    assert not await KiwixPublicExporter.export()


@pytest.mark.asyncio
async def test_exception_upload_file(monkeypatch, ssh_private_key):
    def mock_ack_host_fingerprint(host, port):
        ...

    def mock_upload_file(
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
        raise

    with monkeypatch.context() as mp:
        mp.setattr(openzim_uploader, "upload_file", mock_upload_file)
        mp.setattr(openzim_uploader, "ack_host_fingerprint", mock_ack_host_fingerprint)
        mp.setattr(BackendConf, "upload_uri", "sftp://localhost/data/test/")
        mp.setattr(BackendConf, "private_key", ssh_private_key)

        assert not await KiwixPublicExporter.export()


@pytest.mark.asyncio
async def test_kiwix_public_exporter(monkeypatch, ssh_private_key):
    def mock_ack_host_fingerprint(host, port):
        ...

    # So as not to upload the server test file
    def mock_upload_file(
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
        return 0

    with monkeypatch.context() as mp:
        mp.setattr(openzim_uploader, "upload_file", mock_upload_file)
        mp.setattr(openzim_uploader, "ack_host_fingerprint", mock_ack_host_fingerprint)
        mp.setattr(BackendConf, "upload_uri", "sftp://localhost:8080/data/test/")
        mp.setattr(BackendConf, "private_key", ssh_private_key)

        assert await KiwixPublicExporter.export()
