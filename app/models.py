from pydantic import BaseModel
from typing import Optional

class PersonCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    birthday: str
    birth_year: Optional[int] = None
    married: bool = False
    spouse_name: Optional[str] = None
    anniversary: Optional[str] = None
    anniversary_year: Optional[int] = None
    custom_birthday_message: str = ""
    custom_anniversary_message: str = ""
    notifications_paused: bool = False

class PersonUpdate(PersonCreate):
    pass
