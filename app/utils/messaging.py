import datetime
from typing import Optional

DEFAULTS = {
    ("birthday", "advance", False):    "NoorFamily Reminder: {name}'s birthday is in {days} day(s)! Don't forget to wish them!",
    ("birthday", "same_day", True):    "Happy Birthday, {name}! Wishing you joy and happiness today!",
    ("anniversary", "advance", False): "NoorFamily Reminder: {name} & {spouse}'s anniversary is in {days} day(s)!",
    ("anniversary", "same_day", True): "Happy Anniversary, {name} & {spouse}! Wishing you many more years of happiness together!",
}

def get_default_message(event_type: str, trigger_type: str, for_person: bool) -> str:
    category = "same_day" if trigger_type == "same_day" else "advance"
    return DEFAULTS.get((event_type, category, for_person), "")

def render_message(template: str, person: dict, days: int) -> str:
    today = datetime.date.today()
    variables = {
        "name": person.get("name", ""),
        "spouse": person.get("spouse_name", ""),
        "day_of_week": today.strftime("%A"),
        "days": str(days),
    }
    birth_year = person.get("birth_year")
    if birth_year:
        variables["age"] = str(today.year - int(birth_year))
    else:
        template = template.replace("{age}", "")

    ann_year = person.get("anniversary_year")
    if ann_year:
        variables["years_married"] = str(today.year - int(ann_year))
    else:
        template = template.replace("{years_married}", "")

    for key, value in variables.items():
        template = template.replace("{" + key + "}", value)
    return template
