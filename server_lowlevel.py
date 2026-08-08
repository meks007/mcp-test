import asyncio
import importlib.metadata
import logging

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

BUNDLE_URI = "test://bundle"
FIRST_FILE_URI = "test://files/first.txt"
FIRST_FILE_MIME = "text/plain"
FIRST_FILE_BASE64 = "Rmlyc3Qgc3RhdGljIGZpbGUu"
SECOND_FILE_URI = "test://files/second.bin"
SECOND_FILE_MIME = "application/octet-stream"
SECOND_FILE_BASE64 = "AAECAwQF"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
app = Server("lowlevel-resource-contents-test")


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=BUNDLE_URI,
            name="Static resource bundle",
            mimeType="application/octet-stream",
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> list[types.BlobResourceContents]:
    if uri != BUNDLE_URI:
        raise ValueError(f"Resource not found: {uri}")

    return [
        types.BlobResourceContents(
            uri=FIRST_FILE_URI,
            mimeType=FIRST_FILE_MIME,
            blob=FIRST_FILE_BASE64,
        ),
        types.BlobResourceContents(
            uri=SECOND_FILE_URI,
            mimeType=SECOND_FILE_MIME,
            blob=SECOND_FILE_BASE64,
        ),
    ]


async def main() -> None:
    logger.info("Python: %s", importlib.metadata.version("mcp"))
    logger.info("MCP SDK: %s", importlib.metadata.version("mcp"))
    async with mcp.server.stdio.stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
