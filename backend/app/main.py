from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import shop, voice
from .config import Settings, load_settings
from .db import init_db
from .errors import register_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    init_db(settings.db_path)

    app = FastAPI(title="AceAssist API", version="0.1.0")
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(shop.router)
    app.include_router(voice.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
