from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

from server.api.routes import router as api_router
from server.config import get_settings
from server.db.mongo import init_db
from server.utils.logging import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger("server")

    app = FastAPI(title="Deterministic MCQ Generator API", version="1.0.0")

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request, exc: RequestValidationError):
        return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"detail": exc.errors()})

    origins = settings.cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        logger.info("MongoDB connected; service ready.")

    app.include_router(api_router)
    return app


app = create_app()
