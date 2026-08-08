import contextlib
import importlib.metadata
import logging

import mcp.types as types
import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount

BUNDLE_URI = "test://bundle"
FIRST_FILE_URI = "test://files/first.txt"
FIRST_FILE_MIME = "text/plain"
FIRST_FILE_BASE64 = "Rmlyc3Qgc3RhdGljIGZpbGUu"
SECOND_FILE_URI = "test://files/second.bin"
SECOND_FILE_MIME = "application/octet-stream"
SECOND_FILE_BASE64 = "AAECAwQF"
HOST = "0.0.0.0"
PORT = 8097

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
app = Server("lowlevel-resource-contents-test")
session_manager = StreamableHTTPSessionManager(app=app, json_response=True)


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


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    logger.info("MCP SDK: %s", importlib.metadata.version("mcp"))
    async with session_manager.run():
        yield


http_app = Starlette(
    routes=[Mount("/mcp", app=session_manager.handle_request)],
    lifespan=lifespan,
)


if __name__ == "__main__":
    uvicorn.run(http_app, host=HOST, port=PORT)
