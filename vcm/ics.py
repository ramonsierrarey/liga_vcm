"""Genera un calendario .ics con los partidos del equipo."""
from __future__ import annotations

from datetime import timedelta, timezone

from .logic import kickoff, schedule_status, title


def build_ics(data: dict, now) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//liga_vcm//Feel Alcobendas//ES",
        f"X-WR-CALNAME:{data['team']} - {data['group']}",
        "X-WR-TIMEZONE:Europe/Madrid",
    ]
    for m in data["matches"]:
        if data["team"] not in (m["home"], m["away"]):
            continue
        ko = kickoff(m)
        if ko is None:
            continue
        st = schedule_status(m, now)
        end = ko + timedelta(hours=2)
        fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = " (horario orientativo)" if st == "provisional" else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:vcm-{m['id']}@liga_vcm",
            f"DTSTAMP:{fmt(now)}",
            f"DTSTART:{fmt(ko)}",
            f"DTEND:{fmt(end)}",
            f"SUMMARY:🏐 {title(m)}{suffix}",
            f"LOCATION:{m['court']}",
            f"DESCRIPTION:{m['url']}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
