"""Lógica de estado de horarios y detección de cambios."""
from __future__ import annotations

from datetime import datetime, timedelta

from .config import TEAM, TZ

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def kickoff(m: dict) -> datetime | None:
    if not m.get("date") or not m.get("time"):
        return None
    return datetime.fromisoformat(f"{m['date']}T{m['time']}").replace(tzinfo=TZ)


def freeze_deadline(m: dict) -> datetime | None:
    """Martes 05:00 (Madrid) de la semana del partido; hasta entonces el horario es orientativo."""
    ko = kickoff(m)
    if ko is None:
        return None
    monday = ko.date() - timedelta(days=ko.weekday())
    return datetime.fromisoformat(f"{(monday + timedelta(days=1)).isoformat()}T05:00:00").replace(tzinfo=TZ)


def schedule_status(m: dict, now: datetime) -> str:
    if m.get("result"):
        return "jugado"
    ko = kickoff(m)
    if ko is None:
        return "sin_hora"
    return "provisional" if now < freeze_deadline(m) else "confirmado"


def fmt_when(m: dict) -> str:
    if not m.get("date"):
        return "sin fecha"
    d = datetime.fromisoformat(m["date"])
    s = f"{DIAS[d.weekday()]} {d.strftime('%d/%m/%Y')}"
    return f"{s} {m['time']}" if m.get("time") else f"{s} (sin hora)"


def opponent(m: dict) -> str:
    return m["away"] if m["home"] == TEAM else m["home"]


def title(m: dict) -> str:
    return f"{m['home']} – {m['away']}"


def diff(old: dict | None, new: dict, now: datetime) -> list[str]:
    """Devuelve los mensajes a enviar comparando el estado anterior con el nuevo."""
    if old is None:
        return []
    msgs: list[str] = []
    old_m = {m["id"]: m for m in old.get("matches", [])}
    notified = old.get("notified", {})
    new["notified"] = {k: list(v) for k, v in notified.items()}

    def flag(mid: str, name: str) -> bool:
        """True si el aviso aún no se envió; lo marca como enviado."""
        done = new["notified"].setdefault(mid, [])
        if name in done:
            return False
        done.append(name)
        return True

    for m in new["matches"]:
        if TEAM not in (m["home"], m["away"]):
            continue
        mid = m["id"]
        prev = old_m.get(mid)
        status = schedule_status(m, now)
        m["status"] = status
        ko = kickoff(m)
        frozen = status == "confirmado"
        where = f" en {m['court']}" if m.get("court") else ""

        if prev is None:
            if ko:
                msgs.append(f"🆕 Partido publicado (horario orientativo)\n{title(m)}\n{fmt_when(m)}{where}")
            continue

        changed_time = (prev["date"], prev["time"]) != (m["date"], m["time"])
        changed_court = prev["court"] != m["court"]
        if changed_time or changed_court:
            if prev["time"] is None and m["time"]:
                head = "🕒 Ya hay hora para el partido" + (" (orientativa)" if not frozen else "")
            elif frozen:
                head = "🚨 Cambio DESPUÉS de la confirmación"
            else:
                head = "⚠️ Cambio de horario (aún puede cambiar hasta el martes 05:00)"
            before = f"{fmt_when(prev)}" + (f" en {prev['court']}" if prev["court"] else "")
            msgs.append(f"{head}\n{title(m)}\nAntes: {before}\nAhora: {fmt_when(m)}{where}")
            new["notified"][mid] = [f for f in new["notified"].get(mid, []) if f != "reminder"]

        if ko and status == "confirmado" and flag(mid, "confirmed"):
            msgs.append(f"✅ Horario CONFIRMADO\n{title(m)}\n{fmt_when(m)}{where}")

        if ko and not m["result"] and timedelta(0) < ko - now <= timedelta(hours=24) and flag(mid, "reminder"):
            msgs.append(f"⏰ Partido en menos de 24 h\n{title(m)}\n{fmt_when(m)}{where}")

        if m["result"] and not prev.get("result"):
            r = m["result"]
            msgs.append(f"🏐 Resultado\n{title(m)}  {r['home']}–{r['away']}\nSets: {', '.join(r['sets'])}")

    old_pos = {s["team"]: s["pos"] for s in old.get("standings", [])}
    new_pos = {s["team"]: s["pos"] for s in new["standings"]}
    if TEAM in old_pos and TEAM in new_pos and old_pos[TEAM] != new_pos[TEAM]:
        msgs.append(f"📊 Clasificación: {TEAM} pasa del puesto {old_pos[TEAM]} al {new_pos[TEAM]}")
    return msgs
