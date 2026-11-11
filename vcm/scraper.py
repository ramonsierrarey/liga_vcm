"""Lee la liga pública de VCM con un navegador headless y extrae los datos del equipo."""
from __future__ import annotations

import re
from datetime import datetime

from playwright.sync_api import sync_playwright

from .config import TEAM, TZ

URL = "https://www.voleibolcentromadrid.com/liga?gender=F&level=ORO&status=all"
BASE = "https://www.voleibolcentromadrid.com"

_JS = r"""
() => {
  const out = {groups: []};
  let g = null, round = null;
  for (const el of document.querySelectorAll('*')) {
    const leaf = el.childElementCount === 0;
    const txt = (el.textContent || '').trim();
    if (leaf && /·.*Grupo\s+\S+$/.test(txt) && !/^Clasificación/.test(txt)) {
      g = out.groups.find(x => x.name === txt);
      if (!g) { g = {name: txt, standings: [], matches: []}; out.groups.push(g); }
      round = null;
    } else if (g && leaf && /^Ronda \d+$/.test(txt)) {
      round = parseInt(txt.split(' ')[1]);
    } else if (g && el.tagName === 'TR') {
      const cells = [...el.querySelectorAll('td,th')].map(c => c.innerText.trim());
      if (cells.length >= 10 && /^\d+$/.test(cells[0])) g.standings.push(cells);
    } else if (g && el.tagName === 'LI' && el.querySelector('.public-league-match-schedule')) {
      const clean = n => {
        if (!n) return '';
        const c = n.cloneNode(true);
        c.querySelectorAll('.visually-hidden').forEach(x => x.remove());
        return c.textContent.trim();
      };
      const teams = [...el.querySelectorAll('.public-league-team-link')].map(clean);
      const more = el.querySelector('.public-league-match-more');
      const court = el.querySelector('.public-league-match-court');
      g.matches.push({
        schedule: el.querySelector('.public-league-match-schedule').textContent.trim(),
        teams,
        result: clean(el.querySelector('.public-league-match-result')),
        href: more ? more.getAttribute('href') : null,
        court: clean(court),
        round,
      });
    }
  }
  return out;
}
"""


def _parse_schedule(text: str) -> tuple[str | None, str | None]:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})(?:,\s*(\d{2}):(\d{2}))?$", text)
    if not m:
        return None, None
    d, mo, y, hh, mm = m.groups()
    return f"{y}-{mo}-{d}", (f"{hh}:{mm}" if hh else None)


def _parse_result(text: str) -> dict | None:
    m = re.match(r"(\d+)\s*[–-]\s*(\d+)\s*(?:\((.*)\))?", text)
    if not m:
        return None
    sets = re.findall(r"(\d+)\s*[–-]\s*(\d+)", m.group(3) or "")
    return {"home": int(m.group(1)), "away": int(m.group(2)), "sets": [f"{a}-{b}" for a, b in sets]}


def _num(s: str) -> int:
    return int(s) if re.fullmatch(r"-?\d+", s) else 0


def scrape() -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="es-ES", timezone_id="Europe/Madrid")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(".public-league-match-schedule", timeout=30000)
        raw = page.evaluate(_JS)
        browser.close()

    group = next(
        (g for g in raw["groups"] if any(TEAM == r[1].split("\n")[0].strip() for r in g["standings"])),
        None,
    )
    if group is None:
        raise RuntimeError(f"No encuentro a {TEAM} en ningún grupo de la página")

    standings = [
        {
            "pos": int(r[0]),
            "team": r[1].split("\n")[0].strip(),
            "pj": _num(r[2]),
            "g3": _num(r[3]),
            "g2": _num(r[4]),
            "p1": _num(r[5]),
            "p0": _num(r[6]),
            "sf": _num(r[7]),
            "sc": _num(r[8]),
            "pf": _num(r[9]),
            "pc": _num(r[10]),
            "pts": _num(r[11]) if len(r) > 11 else 0,
        }
        for r in group["standings"]
    ]

    matches = {}
    for m in group["matches"]:
        if len(m["teams"]) != 2 or TEAM not in m["teams"]:
            continue
        date, time = _parse_schedule(m["schedule"])
        mid = m["href"].rsplit("/", 1)[-1] if m["href"] else f'{date}-{"-".join(m["teams"])}'
        matches[mid] = {
            "id": mid,
            "home": m["teams"][0],
            "away": m["teams"][1],
            "date": date,
            "time": time,
            "court": m["court"],
            "round": m["round"],
            "result": _parse_result(m["result"]),
            "url": BASE + m["href"] if m["href"] else URL,
        }

    return {
        "team": TEAM,
        "group": group["name"],
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source": URL,
        "standings": standings,
        "matches": sorted(matches.values(), key=lambda x: (x["date"] or "9999", x["time"] or "")),
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(scrape(), ensure_ascii=False, indent=1))
