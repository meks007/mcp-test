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

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("starlette").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
app = Server("lowlevel-resource-contents-test")
session_manager = StreamableHTTPSessionManager(app=app, json_response=True)


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


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_bundle",
            description="Return the URI of the static test resource bundle.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        )
    ]

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=types.AnyUrl(BUNDLE_URI),
            name="Static resource bundle",
            mimeType="application/octet-stream",
        )
    ]


@app.read_resource()
async def read_resource(uri: types.AnyUrl) -> list[types.BlobResourceContents]:
    requested_uri = str(uri)
    logger.debug("READ_RESOURCE uri=%r string=%s", uri, requested_uri)
    if requested_uri != BUNDLE_URI:
        raise ValueError(f"Resource not found: {requested_uri}")

    return [
        types.BlobResourceContents(
            uri=types.AnyUrl(FIRST_FILE_URI),
            mimeType=FIRST_FILE_MIME,
            blob=FIRST_FILE_BASE64,
        ),
        types.BlobResourceContents(
            uri=types.AnyUrl(SECOND_FILE_URI),
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
    routes=[Mount("/", app=session_manager.handle_request)],
    lifespan=lifespan,
)
http_app = WireDebugMiddleware(http_app)


if __name__ == "__main__":
    uvicorn.run(http_app, host=HOST, port=PORT, log_level="debug")
