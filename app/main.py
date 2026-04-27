from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.error_handlers import register_exception_handlers
from .api.middleware import RequestIdMiddleware
from .api.routes.chat import router as chat_router
from .core.settings import get_settings
from .infra.structured_log import setup_logging
from .infra.tracer import trace


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    trace("app_startup", {"app": "maths-intelligence-agent"}, component="http")
    yield
    trace("app_shutdown", {}, component="http")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Maths Intelligence Agent",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestIdMiddleware)
    application.include_router(chat_router)
    return application


app = create_app()
