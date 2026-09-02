from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.core.correlation import CorrelationIdMiddleware
from app.core.logging import configure_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_application: FastAPI):
    configure_logging()
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.8.0",
        description="CloudOps Platform API. GitHub Actions visibility and certificate monitoring. Credential and GitHub App private keys stay in a secret backend. Secret values are never stored in PostgreSQL.",
        lifespan=lifespan,
    )
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )
    application.include_router(v1_router, prefix="/api/v1")

    @application.middleware("http")
    async def https_only(request: Request, call_next):
        if settings.require_https:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto != "https":
                return JSONResponse({"detail": "HTTPS is required outside local development"}, status_code=400)
        return await call_next(request)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/metrics")
    def metrics():
        from fastapi.responses import PlainTextResponse

        from app.core.metrics import render_prometheus

        return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")

    return application


app = create_app()
