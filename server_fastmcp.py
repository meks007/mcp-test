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


app = WireDebugMiddleware(mcp.http_app(transport="streamable-http"))


if __name__ == "__main__":
    logger.info("FastMCP: %s", importlib.metadata.version("fastmcp"))
    logger.info("MCP SDK: %s", importlib.metadata.version("mcp"))
    uvicorn.run(app, host=HOST, port=PORT, log_level="debug")
