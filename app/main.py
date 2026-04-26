import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.api import members, notifications, logs, settings as settings_api
from app.api.deps import set_db_path

def create_app(db_path: str = "data/family.db") -> FastAPI:
    set_db_path(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path)
        yield

    app = FastAPI(title="Family Notification System", lifespan=lifespan)
    app.include_router(members.router)
    app.include_router(notifications.router)
    app.include_router(logs.router)
    app.include_router(settings_api.router)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app

app = create_app()
