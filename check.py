"""Comprueba la liga, avisa por Telegram de los cambios y guarda el estado."""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

from vcm.config import TZ
from vcm.ics import build_ics
from vcm.logic import diff, schedule_status
from vcm.scraper import scrape

DATA = Path(__file__).parent / "data"
STATE = DATA / "state.json"
ICS = DATA / "feel_alcobendas.ics"


def send(text: str) -> None:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    topic = os.getenv("NTFY_TOPIC")
    print(f"[aviso] {text}\n")
    if topic:
        head, _, body = text.partition("\n")
        title = "=?UTF-8?B?" + base64.b64encode(head.encode("utf-8")).decode() + "?="
        r = requests.post(
            f"https://ntfy.sh/{topic}",
            data=(body or head).encode("utf-8"),
            headers={"Title": title, "Priority": "high"},
            timeout=30,
        )
        r.raise_for_status()
    if token and chat:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=30,
        )
        r.raise_for_status()


def load_state() -> dict | None:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None


def save(data: dict) -> None:
    DATA.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    ICS.write_text(build_ics(data, datetime.now(TZ)), encoding="utf-8", newline="")


def main() -> int:
    old = load_state()
    now = datetime.now(TZ)
    try:
        new = scrape()
        if not any(new["team"] in (m["home"], m["away"]) for m in new["matches"]):
            raise RuntimeError("La página no devuelve partidos del equipo")
    except Exception as exc:  # noqa: BLE001
        if old is not None and not old.get("scrape_error"):
            send(f"❗ No he podido leer la web de la liga: {exc}")
            old["scrape_error"] = str(exc)
            save(old)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 0

    for m in new["matches"]:
        m["status"] = schedule_status(m, now)
    msgs = diff(old, new, now)
    if old is None:
        new["notified"] = {
            m["id"]: ["confirmed"]
            for m in new["matches"]
            if new["team"] in (m["home"], m["away"]) and m["status"] == "confirmado"
        }
        msgs.append(
            f"✅ Vigilancia activada para {new['team']} ({new['group']}).\n"
            f"Puesto actual: {next(s['pos'] for s in new['standings'] if s['team'] == new['team'])}º."
        )
    elif old.get("scrape_error"):
        msgs.append("✅ Ya puedo leer de nuevo la web de la liga.")
    for msg in msgs:
        send(msg)
    save(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
