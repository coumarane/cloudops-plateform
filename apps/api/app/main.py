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
        version="0.6.0",
        description="CloudOps Platform API. Credential metadata is stored in PostgreSQL; secret material stays in a secret backend. PRD mutations require credential:prod_update.",
        lifespan=lifespan,
    )
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
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

    return application


app = create_app()
