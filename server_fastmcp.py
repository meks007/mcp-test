import base64
import importlib.metadata
import logging

import mcp.types as types
import uvicorn
from fastmcp import FastMCP

BUNDLE_URI = "test://bundle"
FIRST_FILE_URI = "test://files/first.txt"
FIRST_FILE_MIME = "text/plain"
FIRST_FILE_BYTES = b"First static file."
SECOND_FILE_URI = "test://files/second.bin"
SECOND_FILE_MIME = "application/octet-stream"
SECOND_FILE_BYTES = bytes([0, 1, 2, 3, 4, 5])
HOST = "0.0.0.0"
PORT = 8098

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("starlette").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
mcp = FastMCP("fastmcp-resource-contents-test")


class WireDebugMiddleware:
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.asgi_app(scope, receive, send)
            return

        headers = [(key.decode(), value.decode()) for key, value in scope["headers"]]
        logger.debug(
            "REQUEST method=%s path=%s query=%s headers=%r",
            scope["method"],
            scope["path"],
            scope["query_string"].decode(),
            headers,
        )

        async def debug_receive():
            message = await receive()
            if message["type"] == "http.request":
                logger.debug(
                    "REQUEST_BODY more=%s body=%s",
                    message.get("more_body", False),
                    message.get("body", b"").decode(errors="replace"),
                )
            return message

        async def debug_send(message):
            if message["type"] == "http.response.start":
                response_headers = [
                    (key.decode(), value.decode()) for key, value in message["headers"]
                ]
                logger.debug(
                    "RESPONSE status=%s headers=%r",
                    message["status"],
                    response_headers,
                )
            elif message["type"] == "http.response.body":
                logger.debug(
                    "RESPONSE_BODY more=%s body=%s",
                    message.get("more_body", False),
                    message.get("body", b"").decode(errors="replace"),
                )
            await send(message)

        await self.asgi_app(scope, debug_receive, debug_send)


# ---------------------------------------------------------------------------
# Resource: test://bundle (stub)
# ---------------------------------------------------------------------------
# The @mcp.resource decorator keeps the resource visible in resources/list.
# The actual multi-file response with individual per-file URIs is produced
# by the low-level router installed below, which intercepts the
# ReadResourceRequest before FastMCP's serialisation layer can normalise
# all content URIs to the registered resource URI (test://bundle).

@mcp.resource(BUNDLE_URI, mime_type="application/octet-stream")
def read_bundle() -> list:
    """Stub: actual read is handled by the low-level router below."""
    return []


@mcp.tool()
def get_bundle() -> str:
    """Return the URI of the static test resource bundle."""
    return "Static resource bundle: " + BUNDLE_URI


# ---------------------------------------------------------------------------
# Low-level resource handler
# ---------------------------------------------------------------------------

async def _build_bundle_result() -> types.ServerResult:
    """Build a ReadResourceResult with one BlobResourceContents per file.

    Each entry carries its own URI so the MCP client can distinguish
    the two files. Base64 encoding is performed here.
    """
    logger.debug("_build_bundle_result: building low-level response for %s", BUNDLE_URI)
    return types.ServerResult(
        types.ReadResourceResult(
            contents=[
                types.BlobResourceContents(
                    uri=types.AnyUrl(FIRST_FILE_URI),
                    mimeType=FIRST_FILE_MIME,
                    blob=base64.b64encode(FIRST_FILE_BYTES).decode("ascii"),
                ),
                types.BlobResourceContents(
                    uri=types.AnyUrl(SECOND_FILE_URI),
                    mimeType=SECOND_FILE_MIME,
                    blob=base64.b64encode(SECOND_FILE_BYTES).decode("ascii"),
                ),
            ]
        )
    )


# ---------------------------------------------------------------------------
# Low-level resource router
# ---------------------------------------------------------------------------
# FastMCP stores the low-level MCP server on mcp._mcp_server.
# Its request_handlers dict maps MCP request types to handler callables.
# We capture the FastMCP-registered ReadResourceRequest handler as a
# fallback, then replace it with our router which dispatches known URIs
# directly and delegates everything else to FastMCP.
# Must be installed after all @mcp.resource / @mcp.tool decorators so
# the original FastMCP handler is fully initialised before capture.

_HANDLERS = {
    BUNDLE_URI: _build_bundle_result,
}

_lowlevel_server = mcp._mcp_server
_fastmcp_read_handler = _lowlevel_server.request_handlers.get(types.ReadResourceRequest)

if _fastmcp_read_handler is None:
    raise RuntimeError(
        "FastMCP did not register a ReadResourceRequest handler. "
        "Check FastMCP and MCP SDK versions."
    )


async def _read_resource_router(
    request: types.ReadResourceRequest,
) -> types.ServerResult:
    uri_str = str(request.params.uri)
    logger.debug("_read_resource_router: uri=%s", uri_str)
    handler = _HANDLERS.get(uri_str)
    if handler is not None:
        return await handler()
    return await _fastmcp_read_handler(request)


_lowlevel_server.request_handlers[types.ReadResourceRequest] = _read_resource_router
logger.debug(
    "Low-level resource router installed for URIs: %s", list(_HANDLERS.keys())
)

# ---------------------------------------------------------------------------
# ASGI app
# ---------------------------------------------------------------------------

app = WireDebugMiddleware(mcp.http_app(transport="streamable-http"))


if __name__ == "__main__":
    logger.info("FastMCP: %s", importlib.metadata.version("fastmcp"))
    logger.info("MCP SDK: %s", importlib.metadata.version("mcp"))
    uvicorn.run(app, host=HOST, port=PORT, log_level="debug")
