import calendar
import re
import sys
from datetime import date, timedelta

MONTH_NAMES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

MONTHS = {name: i for i, name in enumerate(MONTH_NAMES, 1)}
MONTHS |= {name[:3]: i for i, name in enumerate(MONTH_NAMES, 1)}
MONTHS["sept"] = 9

WEEKDAYS = {name: i for i, name in enumerate(WEEKDAY_NAMES)}
WEEKDAYS |= {name[:3]: i for i, name in enumerate(WEEKDAY_NAMES)}
WEEKDAYS |= {"tues": 1, "thur": 3, "thurs": 3}

NUMBER_NAMES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
]

NUMBERS = {name: i for i, name in enumerate(NUMBER_NAMES)}
NUMBERS |= {"a": 1, "an": 1, "twenty": 20, "thirty": 30}

UNITS = {
    "day": (0, 1),
    "week": (0, 7),
    "fortnight": (0, 14),
    "month": (1, 0),
    "year": (12, 0),
}

SIMPLE = {
    "today": 0,
    "now": 0,
    "tomorrow": 1,
    "yesterday": -1,
    "day after tomorrow": 2,
    "day before yesterday": -2,
}

MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
WEEKDAY_RE = "|".join(sorted(WEEKDAYS, key=len, reverse=True))
ORD = r"(\d{1,2})(?:st|nd|rd|th)?"
UNIT_RE = "|".join(UNITS)
PART = rf"\b(\d+|[a-z]+) ({UNIT_RE})s?\b"
PART_NC = rf"(?:\d+|[a-z]+) (?:{UNIT_RE})s?"
DURATION = rf"{PART_NC}(?: (?:and )?{PART_NC})*"
BACKWARD = {"before", "prior to", "earlier than", "ago"}


def _shift(d: date, months: int, days: int) -> date:
    year, month = divmod(d.year * 12 + d.month - 1 + months, 12)
    day = min(d.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day) + timedelta(days=days)


def _amount(word: str) -> int:
    if word.isdigit():
        return int(word)
    if word in NUMBERS:
        return NUMBERS[word]
    raise ValueError(f"Unrecognized number: {word!r}")


def _apply(duration: str, sign: int, anchor: date) -> date:
    if m := re.fullmatch(rf"(\d+|[a-z]+) ({WEEKDAY_RE})s?", duration):
        n = _amount(m[1])
        if n < 1:
            raise ValueError(f"Unrecognized duration: {duration!r}")
        first = _weekday("next" if sign > 0 else "last", WEEKDAYS[m[2]], anchor)
        return first + timedelta(weeks=sign * (n - 1))
    if not re.fullmatch(DURATION, duration):
        raise ValueError(f"Unrecognized duration: {duration!r}")
    months = days = 0
    for m in re.finditer(PART, duration):
        n = _amount(m[1])
        unit_months, unit_days = UNITS[m[2]]
        months += n * unit_months
        days += n * unit_days
    return _shift(anchor, sign * months, sign * days)


def _year(text: str | None, today: date) -> int:
    if text is None:
        return today.year
    if len(text) == 2:
        return 2000 + int(text)
    return int(text)


def _weekday(modifier: str | None, weekday: int, today: date) -> date:
    ahead = (weekday - today.weekday()) % 7
    if modifier == "next":
        return today + timedelta(days=ahead or 7)
    if modifier in ("last", "past", "previous"):
        return today - timedelta(days=(today.weekday() - weekday) % 7 or 7)
    return today + timedelta(days=ahead)


def _absolute(s: str, today: date) -> date | None:
    if s in SIMPLE:
        return today + timedelta(days=SIMPLE[s])
    if m := re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s):
        return date(int(m[1]), int(m[2]), int(m[3]))
    if m := re.fullmatch(r"(\d{1,2})[-/](\d{1,2})(?:[-/](\d{4}|\d{2}))?", s):
        return date(_year(m[3], today), int(m[1]), int(m[2]))
    if m := re.fullmatch(rf"({MONTH_RE}) {ORD}(?: (\d{{4}}))?", s):
        return date(_year(m[3], today), MONTHS[m[1]], int(m[2]))
    if m := re.fullmatch(rf"{ORD} (?:of )?({MONTH_RE})(?: (\d{{4}}))?", s):
        return date(_year(m[3], today), MONTHS[m[2]], int(m[1]))
    if m := re.fullmatch(
        rf"(?:(next|last|this|coming|past|previous) )?({WEEKDAY_RE})", s
    ):
        return _weekday(m[1], WEEKDAYS[m[2]], today)
    if m := re.fullmatch(r"(next|last|this) (week|month|year)", s):
        sign = {"next": 1, "last": -1, "this": 0}[m[1]]
        unit_months, unit_days = UNITS[m[2]]
        return _shift(today, sign * unit_months, sign * unit_days)
    return None


def _parse(s: str, today: date) -> date:
    if (d := _absolute(s, today)) is not None:
        return d
    if m := re.fullmatch(r"in (.+?)(?: from now)?", s):
        return _apply(m[1], 1, today)
    if m := re.fullmatch(r"(.+?) (ago|later)", s):
        return _apply(m[1], -1 if m[2] in BACKWARD else 1, today)
    if m := re.fullmatch(
        r"(.+?) (before|after|from|prior to|earlier than|later than) (.+)", s
    ):
        return _apply(m[1], -1 if m[2] in BACKWARD else 1, _parse(m[3], today))
    raise ValueError(f"Unrecognized date: {s!r}")


def parse(s: str, today: date | None = None) -> date:
    if today is None:
        today = date.today()
    text = re.sub(r"['’]s\b", "s", s.lower())
    text = re.sub(r"[,.]", " ", text)
    text = re.sub(r"\b(the|on)\b", " ", text)
    text = " ".join(text.split())
    if not text:
        raise ValueError("Empty date string")
    try:
        return _parse(text, today)
    except OverflowError as e:
        raise ValueError(f"Date out of range: {s!r}") from e


def main() -> None:
    print(parse(" ".join(sys.argv[1:])))
