import importlib.metadata
import logging

import uvicorn
from fastmcp import FastMCP
from fastmcp.resources import ResourceContent, ResourceResult

BUNDLE_URI = "test://bundle"
FIRST_FILE_MIME = "text/plain"
FIRST_FILE_BYTES = b"First static file."
SECOND_FILE_MIME = "application/octet-stream"
SECOND_FILE_BYTES = bytes([0, 1, 2, 3, 4, 5])
HOST = "0.0.0.0"
PORT = 8098

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
mcp = FastMCP("fastmcp-resource-contents-test")


@mcp.resource(BUNDLE_URI, mime_type="application/octet-stream")
def read_bundle() -> ResourceResult:
    return ResourceResult(
        contents=[
            ResourceContent(content=FIRST_FILE_BYTES, mime_type=FIRST_FILE_MIME),
            ResourceContent(content=SECOND_FILE_BYTES, mime_type=SECOND_FILE_MIME),
        ]
    )


@mcp.tool()
def get_bundle() -> str:
    """Return the URI of the static test resource bundle."""
    return f"Static resource bundle: {BUNDLE_URI}"


app = mcp.http_app(transport="streamable-http")


if __name__ == "__main__":
    logger.info("FastMCP: %s", importlib.metadata.version("fastmcp"))
    logger.info("MCP SDK: %s", importlib.metadata.version("mcp"))
    uvicorn.run(app, host=HOST, port=PORT)
