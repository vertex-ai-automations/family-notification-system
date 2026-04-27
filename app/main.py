import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.api import members, notifications, logs, settings as settings_api, health
from app.api.deps import set_db_path
from app.service_factory import build_services


def create_app(db_path: str = "data/family.db", start_scheduler: bool = True) -> FastAPI:
    set_db_path(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path)
        if start_scheduler:
            services = build_services(db_path)
            from app.scheduler import setup_scheduler
            setup_scheduler(services, db_path)
        yield
        if start_scheduler:
            from app.scheduler import stop_scheduler
            stop_scheduler()

    app = FastAPI(title="Family Notification System", lifespan=lifespan)
    app.include_router(members.router)
    app.include_router(notifications.router)
    app.include_router(logs.router)
    app.include_router(settings_api.router)
    app.include_router(health.router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir) and os.listdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app

app = create_app()
