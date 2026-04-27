import sqlite3
from fastapi import APIRouter, Depends
from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: sqlite3.Connection = Depends(get_db)):
    db_ok = False
    try:
        db.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        pass

    services_status: dict[str, str] = {}
    try:
        from app.scheduler import get_services
        for svc in get_services():
            try:
                services_status[svc.name] = "ok" if svc.health_check() else "fail"
            except Exception:
                services_status[svc.name] = "fail"
    except Exception:
        pass

    overall = "ok" if db_ok and all(s == "ok" for s in services_status.values()) else "degraded"
    return {"status": overall, "db": "ok" if db_ok else "fail", "services": services_status}
