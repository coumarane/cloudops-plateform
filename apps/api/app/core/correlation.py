from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


def current_correlation_id() -> str:
    value = correlation_id_var.get()
    return value if value and value != "-" else str(uuid4())


def bind_correlation_id(value: str | None = None) -> str:
    correlation_id = value or str(uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        correlation_id = headers.get("x-correlation-id") or str(uuid4())
        token = correlation_id_var.set(correlation_id)

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers") or [])
                raw_headers.append((b"x-correlation-id", correlation_id.encode()))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            correlation_id_var.reset(token)
