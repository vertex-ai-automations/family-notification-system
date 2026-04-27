import csv
import datetime
import io
import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.utils.sender import execute_send
from app.api.deps import get_db

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _build_filter(person_id, channel, event_type, trigger_type, status, date_from, date_to):
    """Shared between list, export, and delete — keeps filter semantics identical."""
    where = " WHERE 1=1"
    params: list = []
    if person_id:    where += " AND l.person_id=?";    params.append(person_id)
    if channel:      where += " AND l.channel=?";      params.append(channel)
    if event_type:   where += " AND l.event_type=?";   params.append(event_type)
    if trigger_type: where += " AND l.trigger_type=?"; params.append(trigger_type)
    if status:       where += " AND l.status=?";       params.append(status)
    if date_from:    where += " AND l.sent_at >= ?";   params.append(date_from)
    if date_to:      where += " AND l.sent_at <= ?";   params.append(date_to)
    return where, params


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
    where, params = _build_filter(person_id, channel, event_type, trigger_type, status, date_from, date_to)
    query = "SELECT l.*, p.name as person_name FROM notification_log l JOIN people p ON l.person_id=p.id" + where + " ORDER BY l.sent_at DESC LIMIT 500"
    return [dict(r) for r in db.execute(query, params).fetchall()]


@router.get("/export.csv")
def export_logs_csv(
    person_id: Optional[int] = None,
    channel: Optional[str] = None,
    event_type: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """CSV of all matching logs (no 500-row cap — full export)."""
    where, params = _build_filter(person_id, channel, event_type, trigger_type, status, date_from, date_to)
    rows = db.execute(
        "SELECT l.id, p.name AS person_name, l.event_type, l.trigger_type, l.channel, "
        "l.status, l.message_body, l.error_message, l.sent_at "
        "FROM notification_log l JOIN people p ON l.person_id=p.id" + where + " ORDER BY l.sent_at DESC",
        params,
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(["id", "person_name", "event_type", "trigger_type", "channel", "status", "message_body", "error_message", "sent_at"])
    for r in rows:
        writer.writerow([r["id"], r["person_name"], r["event_type"], r["trigger_type"],
                         r["channel"], r["status"], r["message_body"], r["error_message"] or "", r["sent_at"]])
    buf.seek(0)
    filename = f"notification_logs_{datetime.date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("", status_code=200)
def reset_logs(
    person_id: Optional[int] = None,
    channel: Optional[str] = None,
    event_type: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Delete log rows matching the same filters used by list/export.
    With no filters, wipes the entire notification_log table.
    Always preserves notification_state — clearing state would let scheduled
    jobs re-fire today's already-sent notifications."""
    # Build WHERE without the `l.` alias so it works on a bare DELETE.
    where = " WHERE 1=1"
    params: list = []
    if person_id:    where += " AND person_id=?";    params.append(person_id)
    if channel:      where += " AND channel=?";      params.append(channel)
    if event_type:   where += " AND event_type=?";   params.append(event_type)
    if trigger_type: where += " AND trigger_type=?"; params.append(trigger_type)
    if status:       where += " AND status=?";       params.append(status)
    if date_from:    where += " AND sent_at >= ?";   params.append(date_from)
    if date_to:      where += " AND sent_at <= ?";   params.append(date_to)
    cur = db.execute("DELETE FROM notification_log" + where, params)
    db.commit()
    return {"deleted": cur.rowcount}


@router.post("/{log_id}/retry", status_code=202)
def retry_log(log_id: int, db: sqlite3.Connection = Depends(get_db)):
    from app.scheduler import get_services
    log = db.execute("SELECT * FROM notification_log WHERE id=?", (log_id,)).fetchone()
    if not log or log["status"] != "failed":
        raise HTTPException(404, "Failed log entry not found")
    person_row = db.execute("SELECT * FROM people WHERE id=?", (log["person_id"],)).fetchone()
    if not person_row:
        raise HTTPException(404, "Person for this log entry no longer exists")
    person = dict(person_row)
    services = [s for s in get_services() if s.name == log["channel"]]
    execute_send(db, person, log["event_type"], log["trigger_type"], log["message_body"], services, write_state=False)
    return {"status": "retried"}
