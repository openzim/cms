from backend.collections.kiwix_public import KiwixPublicCollection
from backend.exporters import exporter
from backend.formatters.kiwixlibraryxml import KiwixLibraryXml


class KiwixPublicExporter:
    async def kiwix_library_xml_exporter():
        await exporter(
            await KiwixLibraryXml.generate(collection=KiwixPublicCollection())
        )
