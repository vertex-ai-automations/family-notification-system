import datetime
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from app.models import PersonCreate, PersonUpdate, PersonPartialUpdate
from app.utils.phone import normalize_phone
from app.api.deps import get_db

router = APIRouter(prefix="/api/members", tags=["members"])

@router.get("")
def list_members(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM people ORDER BY name").fetchall()
    return [dict(r) for r in rows]

@router.get("/upcoming")
def upcoming_events(db: sqlite3.Connection = Depends(get_db)):
    today = datetime.date.today()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]
    events = []
    for p in people:
        for event_type, date_str in [("birthday", p.get("birthday")), ("anniversary", p.get("anniversary") if p.get("married") else None)]:
            if not date_str:
                continue
            try:
                month, day = map(int, date_str.split("-"))
                target = datetime.date(today.year, month, day)
                if target < today:
                    target = datetime.date(today.year + 1, month, day)
                days_away = (target - today).days
                if days_away <= 30:
                    events.append({"id": p["id"], "name": p["name"], "event_type": event_type, "date": date_str, "days_away": days_away})
            except ValueError:
                continue
    return sorted(events, key=lambda x: x["days_away"])

@router.post("", status_code=201)
def create_member(person: PersonCreate, db: sqlite3.Connection = Depends(get_db)):
    data = person.model_dump()
    data["phone"] = normalize_phone(data.get("phone"))
    data["whatsapp"] = normalize_phone(data.get("whatsapp"))
    if data["whatsapp"] and data["whatsapp"] == data["phone"]:
        data["whatsapp"] = None
    cursor = db.execute(
        """INSERT INTO people (name,phone,email,whatsapp,birthday,birth_year,married,spouse_name,
           anniversary,anniversary_year,custom_birthday_message,custom_anniversary_message,notifications_paused)
           VALUES (:name,:phone,:email,:whatsapp,:birthday,:birth_year,:married,:spouse_name,
           :anniversary,:anniversary_year,:custom_birthday_message,:custom_anniversary_message,:notifications_paused)""",
        data
    )
    db.commit()
    row = db.execute("SELECT * FROM people WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)

@router.put("/{person_id}")
def update_member(person_id: int, person: PersonUpdate, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute("SELECT id FROM people WHERE id=?", (person_id,)).fetchone():
        raise HTTPException(404, "Person not found")
    data = person.model_dump()
    data["phone"] = normalize_phone(data.get("phone"))
    data["whatsapp"] = normalize_phone(data.get("whatsapp"))
    if data["whatsapp"] and data["whatsapp"] == data["phone"]:
        data["whatsapp"] = None
    data["id"] = person_id
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        """UPDATE people SET name=:name,phone=:phone,email=:email,whatsapp=:whatsapp,birthday=:birthday,
           birth_year=:birth_year,married=:married,spouse_name=:spouse_name,anniversary=:anniversary,
           anniversary_year=:anniversary_year,custom_birthday_message=:custom_birthday_message,
           custom_anniversary_message=:custom_anniversary_message,notifications_paused=:notifications_paused,
           updated_at=:updated_at WHERE id=:id""",
        data
    )
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())

@router.patch("/{person_id}")
def patch_member(person_id: int, person: PersonPartialUpdate, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute("SELECT id FROM people WHERE id=?", (person_id,)).fetchone():
        raise HTTPException(404, "Person not found")
    data = person.model_dump(exclude_unset=True)
    if "phone" in data:
        data["phone"] = normalize_phone(data.get("phone"))
    if "whatsapp" in data:
        data["whatsapp"] = normalize_phone(data.get("whatsapp"))
        if data["whatsapp"] and data["whatsapp"] == data.get("phone"):
            data["whatsapp"] = None
    if not data:
        return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fragments = ", ".join(f"{k}=:{k}" for k in data)
    data["id"] = person_id
    db.execute(f"UPDATE people SET {fragments} WHERE id=:id", data)
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())


@router.delete("/{person_id}", status_code=204)
def delete_member(person_id: int, db: sqlite3.Connection = Depends(get_db)):
    result = db.execute("DELETE FROM people WHERE id=?", (person_id,))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Person not found")
