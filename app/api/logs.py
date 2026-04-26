import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.utils.sender import execute_send
from app.api.deps import get_db

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("")
def list_logs(
    person_id: Optional[int] = None,
    channel: Optional[str] = None,
    event_type: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT l.*, p.name as person_name FROM notification_log l JOIN people p ON l.person_id=p.id WHERE 1=1"
    params = []
    if person_id: query += " AND l.person_id=?"; params.append(person_id)
    if channel: query += " AND l.channel=?"; params.append(channel)
    if event_type: query += " AND l.event_type=?"; params.append(event_type)
    if trigger_type: query += " AND l.trigger_type=?"; params.append(trigger_type)
    if status: query += " AND l.status=?"; params.append(status)
    if date_from: query += " AND l.sent_at >= ?"; params.append(date_from)
    if date_to: query += " AND l.sent_at <= ?"; params.append(date_to)
    query += " ORDER BY l.sent_at DESC LIMIT 500"
    return [dict(r) for r in db.execute(query, params).fetchall()]

@router.post("/{log_id}/retry", status_code=202)
def retry_log(log_id: int, db: sqlite3.Connection = Depends(get_db)):
    from app.scheduler import get_services
    log = db.execute("SELECT * FROM notification_log WHERE id=?", (log_id,)).fetchone()
    if not log or log["status"] != "failed":
        raise HTTPException(404, "Failed log entry not found")
    person = dict(db.execute("SELECT * FROM people WHERE id=?", (log["person_id"],)).fetchone())
    services = [s for s in get_services() if s.name == log["channel"]]
    execute_send(db, person, log["event_type"], log["trigger_type"], log["message_body"], services, write_state=False)
    return {"status": "retried"}
