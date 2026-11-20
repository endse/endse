"""Shared GitHub helpers for the profile graphics generators (stdlib only)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date

USERNAME = os.getenv("PROFILE_USER", "endse")
ORG = os.getenv("PROFILE_ORG", "Endsett")

_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": f"{USERNAME}-profile-graphics",
}
if _TOKEN:
    _HEADERS["Authorization"] = f"Bearer {_TOKEN}"

_RETRY_CODES = {403, 429, 500, 502, 503, 504}


def _request(url: str, *, headers: dict | None = None, data: bytes | None = None, attempts: int = 5) -> bytes:
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=headers or _HEADERS, data=data)
            with urllib.request.urlopen(req, timeout=25) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRY_CODES or attempt == attempts - 1:
                raise
            reset = exc.headers.get("X-RateLimit-Reset")
            delay = min(30, max(2, int(reset) - int(time.time()))) if reset else 2 ** attempt
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not fetch {url}")


def get_json(url: str):
    return json.loads(_request(url).decode("utf-8"))


def get_paginated(url: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        data = get_json(f"{url}?per_page=100&page={page}")
        if not isinstance(data, list) or not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items


# --------------------------------------------------------------------------- contributions


@dataclass(frozen=True)
class Day:
    week: int      # column (0 = oldest week)
    weekday: int   # row (0 = Sunday)
    date: date
    level: int     # 0..4, same buckets GitHub uses for colouring


_TD = re.compile(r"<td[^>]*?data-date=\"(?P<date>\d{4}-\d{2}-\d{2})\"[^>]*>", re.S)
_ATTR_ID = re.compile(r"id=\"contribution-day-component-(\d+)-(\d+)\"")
_ATTR_LEVEL = re.compile(r"data-level=\"(\d)\"")


def _parse_calendar_html(html: str) -> list[Day]:
    days = []
    for match in _TD.finditer(html):
        tag = match.group(0)
        ident, level = _ATTR_ID.search(tag), _ATTR_LEVEL.search(tag)
        if not ident or not level:
            continue
        days.append(Day(week=int(ident.group(2)), weekday=int(ident.group(1)),
                        date=date.fromisoformat(match.group("date")), level=int(level.group(1))))
    return days


_LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
_GQL = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
weeks{contributionDays{date weekday contributionLevel}}}}}}"""


def _calendar_graphql() -> list[Day]:
    body = json.dumps({"query": _GQL, "variables": {"login": USERNAME}}).encode()
    payload = json.loads(_request("https://api.github.com/graphql", data=body).decode())
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [Day(week=w, weekday=d["weekday"], date=date.fromisoformat(d["date"]), level=_LEVELS[d["contributionLevel"]])
            for w, week in enumerate(weeks) for d in week["contributionDays"]]


_TOTAL = re.compile(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", re.I)


def contribution_calendar() -> tuple[list[Day], int | None]:
    """Last-year contribution grid + total count.

    Public HTML first (no token needed, matches what visitors see), GraphQL as fallback.
    """
    try:
        html = _request(f"https://github.com/users/{USERNAME}/contributions",
                        headers={"User-Agent": _HEADERS["User-Agent"]}).decode("utf-8")
        days = _parse_calendar_html(html)
        if days:
            total = _TOTAL.search(html)
            return days, int(total.group(1).replace(",", "")) if total else None
        print("Contribution HTML had no cells, falling back to GraphQL")
    except Exception as error:  # noqa: BLE001 - any failure -> try the API
        print(f"Contribution HTML fetch failed ({error}), falling back to GraphQL")
    if not _TOKEN:
        raise RuntimeError("No contribution data: HTML scrape failed and no GH_TOKEN for GraphQL")
    return _calendar_graphql(), None
