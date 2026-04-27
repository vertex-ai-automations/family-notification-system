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

class PersonPartialUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    birthday: Optional[str] = None
    birth_year: Optional[int] = None
    married: Optional[bool] = None
    spouse_name: Optional[str] = None
    anniversary: Optional[str] = None
    anniversary_year: Optional[int] = None
    custom_birthday_message: Optional[str] = None
    custom_anniversary_message: Optional[str] = None
    notifications_paused: Optional[bool] = None
