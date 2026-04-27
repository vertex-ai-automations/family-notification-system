import datetime
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from app.models import PersonCreate, PersonUpdate, PersonPartialUpdate
from app.utils.phone import normalize_phone
from app.api.deps import get_db

router = APIRouter(prefix="/api/members", tags=["members"])


# --- Relationship helpers ---------------------------------------------------

def _validate_relationship_ids(person_id: int | None, data: dict, db: sqlite3.Connection):
    """Reject self-references and IDs that don't exist."""
    for key in ("mother_id", "father_id", "spouse_id"):
        ref = data.get(key)
        if ref is None:
            continue
        if person_id is not None and ref == person_id:
            raise HTTPException(400, f"{key} cannot reference the same person")
        if not db.execute("SELECT 1 FROM people WHERE id=?", (ref,)).fetchone():
            raise HTTPException(400, f"{key} references a non-existent person (id={ref})")


def _sync_spouse(db: sqlite3.Connection, person_id: int, new_spouse_id: int | None, old_spouse_id: int | None):
    """Maintain mutual spouse_id pointers across the two rows.
    - If the partner changed, clear the previous partner's pointer.
    - Set the new partner's pointer to this person.
    - Clearing both works automatically (new=None, old=value -> clear only old)."""
    if old_spouse_id and old_spouse_id != new_spouse_id:
        db.execute("UPDATE people SET spouse_id=NULL WHERE id=?", (old_spouse_id,))
    if new_spouse_id:
        db.execute("UPDATE people SET spouse_id=? WHERE id=?", (person_id, new_spouse_id))


# --- Endpoints --------------------------------------------------------------

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
    _validate_relationship_ids(None, data, db)  # no self-ID yet on create
    cursor = db.execute(
        """INSERT INTO people (name,phone,email,whatsapp,birthday,birth_year,married,spouse_name,
           anniversary,anniversary_year,custom_birthday_message,custom_anniversary_message,
           notifications_paused,mother_id,father_id,spouse_id)
           VALUES (:name,:phone,:email,:whatsapp,:birthday,:birth_year,:married,:spouse_name,
           :anniversary,:anniversary_year,:custom_birthday_message,:custom_anniversary_message,
           :notifications_paused,:mother_id,:father_id,:spouse_id)""",
        data
    )
    new_id = cursor.lastrowid
    _sync_spouse(db, new_id, data.get("spouse_id"), None)
    db.commit()
    row = db.execute("SELECT * FROM people WHERE id=?", (new_id,)).fetchone()
    return dict(row)


@router.put("/{person_id}")
def update_member(person_id: int, person: PersonUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "Person not found")
    data = person.model_dump()
    data["phone"] = normalize_phone(data.get("phone"))
    data["whatsapp"] = normalize_phone(data.get("whatsapp"))
    if data["whatsapp"] and data["whatsapp"] == data["phone"]:
        data["whatsapp"] = None
    _validate_relationship_ids(person_id, data, db)
    data["id"] = person_id
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        """UPDATE people SET name=:name,phone=:phone,email=:email,whatsapp=:whatsapp,birthday=:birthday,
           birth_year=:birth_year,married=:married,spouse_name=:spouse_name,anniversary=:anniversary,
           anniversary_year=:anniversary_year,custom_birthday_message=:custom_birthday_message,
           custom_anniversary_message=:custom_anniversary_message,notifications_paused=:notifications_paused,
           mother_id=:mother_id,father_id=:father_id,spouse_id=:spouse_id,
           updated_at=:updated_at WHERE id=:id""",
        data
    )
    _sync_spouse(db, person_id, data.get("spouse_id"), existing["spouse_id"])
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())


@router.patch("/{person_id}")
def patch_member(person_id: int, person: PersonPartialUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "Person not found")
    data = person.model_dump(exclude_unset=True)
    if "phone" in data:
        data["phone"] = normalize_phone(data.get("phone"))
    if "whatsapp" in data:
        data["whatsapp"] = normalize_phone(data.get("whatsapp"))
        compare_phone = data["phone"] if "phone" in data else existing["phone"]
        if data["whatsapp"] and data["whatsapp"] == compare_phone:
            data["whatsapp"] = None
    _validate_relationship_ids(person_id, data, db)
    spouse_changed = "spouse_id" in data
    if not data:
        return dict(existing)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fragments = ", ".join(f"{k}=:{k}" for k in data)
    data["id"] = person_id
    db.execute(f"UPDATE people SET {fragments} WHERE id=:id", data)
    if spouse_changed:
        _sync_spouse(db, person_id, data.get("spouse_id"), existing["spouse_id"])
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())


@router.delete("/{person_id}", status_code=204)
def delete_member(person_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "Person not found")
    # Manually clear partner's spouse_id (FK ON DELETE SET NULL only works on
    # fresh DBs created by CREATE TABLE; old DBs upgraded via ALTER TABLE
    # don't have the constraint).
    if existing["spouse_id"]:
        db.execute("UPDATE people SET spouse_id=NULL WHERE id=?", (existing["spouse_id"],))
    # Clear references from children too
    db.execute("UPDATE people SET mother_id=NULL WHERE mother_id=?", (person_id,))
    db.execute("UPDATE people SET father_id=NULL WHERE father_id=?", (person_id,))
    db.execute("DELETE FROM people WHERE id=?", (person_id,))
    db.commit()
