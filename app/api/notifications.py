import datetime
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.utils.messaging import render_message, get_default_message
from app.utils.sender import execute_send
from app.api.deps import get_db

router = APIRouter(prefix="/api", tags=["notifications"])

class PreviewRequest(BaseModel):
    person_id: int
    event_type: str
    trigger_type: str

class SendRequest(BaseModel):
    person_id: int
    event_type: str
    trigger_type: str

class PauseRequest(BaseModel):
    paused: bool

def _compute_days(person: dict, event_type: str) -> int:
    today = datetime.date.today()
    date_str = person.get("anniversary") if event_type == "anniversary" and person.get("anniversary") else person.get("birthday")
    if not date_str:
        return 0
    month, day = map(int, date_str.split("-"))
    target = datetime.date(today.year, month, day)
    if target < today:
        target = datetime.date(today.year + 1, month, day)
    return (target - today).days

@router.post("/notifications/preview")
def preview(req: PreviewRequest, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM people WHERE id=?", (req.person_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Person not found")
    person = dict(row)
    for_person = req.trigger_type == "same_day"
    days = _compute_days(person, req.event_type)
    field = f"custom_{req.event_type}_message"
    template = person.get(field) or get_default_message(req.event_type, req.trigger_type, for_person) or ""
    message = render_message(template, person, days=days)
    return {"sms": message, "whatsapp": message, "email": message}

@router.post("/notifications/send", status_code=202)
def send_now(req: SendRequest, db: sqlite3.Connection = Depends(get_db)):
    from app.scheduler import get_services
    row = db.execute("SELECT * FROM people WHERE id=?", (req.person_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Person not found")
    person = dict(row)
    for_person = req.trigger_type == "same_day"
    days = _compute_days(person, req.event_type)
    field = f"custom_{req.event_type}_message"
    template = person.get(field) or get_default_message(req.event_type, req.trigger_type, for_person) or ""
    message = render_message(template, person, days=days)
    write_state = req.trigger_type == "same_day"
    execute_send(db, person, req.event_type, req.trigger_type, message, get_services(), write_state=write_state)
    return {"status": "dispatched"}

@router.put("/members/{person_id}/pause")
def pause_member(person_id: int, req: PauseRequest, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id FROM people WHERE id=?", (person_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Person not found")
    db.execute("UPDATE people SET notifications_paused=? WHERE id=?", (1 if req.paused else 0, person_id))
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())
