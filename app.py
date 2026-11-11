import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

from vcm.logic import fmt_when, freeze_deadline, kickoff, opponent, schedule_status, title
from vcm.config import TZ

LOGO = Path(__file__).parent / "assets" / "logo.png"
st.set_page_config(page_title="Feel Alcobendas · Liga VCM", page_icon=str(LOGO), layout="centered")

STATE = Path(__file__).parent / "data" / "state.json"
BADGE = {
    "provisional": ":orange-badge[Horario orientativo]",
    "confirmado": ":green-badge[Horario confirmado]",
    "sin_hora": ":gray-badge[Sin hora]",
    "jugado": ":blue-badge[Jugado]",
}


@st.cache_data(ttl=300)
def load() -> dict | None:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None


data = load()
logo_col, title_col = st.columns([1, 2], vertical_alignment="center")
logo_col.image(str(LOGO), width="stretch")
title_col.title("Liga VCM")
title_col.caption("Femenino · Oro")
if not data:
    st.warning("Aún no hay datos. Ejecuta `python check.py` o espera a la primera comprobación automática.")
    st.stop()

now = datetime.now(TZ)
team = data["team"]
matches = data["matches"]
st.caption(f"{data['group']} · actualizado {datetime.fromisoformat(data['fetched_at']):%d/%m/%Y %H:%M}")

played = [m for m in matches if m.get("result")]
upcoming = [m for m in matches if not m.get("result")]
upcoming.sort(key=lambda m: (m["date"] or "9999", m["time"] or ""))
me = next(s for s in data["standings"] if s["team"] == team)

c1, c2, c3 = st.columns(3)
c1.metric("Puesto", f"{me['pos']}º")
c2.metric("Puntos", me["pts"])
c3.metric("Partidos jugados", me["pj"])

nxt = upcoming[0] if upcoming else None
with st.container(border=True):
    st.subheader("Próximo partido")
    if nxt:
        st.markdown(f"**{title(nxt)}**  \n{fmt_when(nxt)}" + (f" · {nxt['court']}" if nxt["court"] else ""))
        st.markdown(BADGE[schedule_status(nxt, now)])
        ko, dl = kickoff(nxt), freeze_deadline(nxt)
        if ko:
            left = ko - now
            st.write(f"Faltan {left.days} d {left.seconds // 3600} h")
            if now < dl:
                st.caption(f"Puede cambiar hasta el martes {dl:%d/%m %H:%M}")
    else:
        st.write("No hay más partidos programados.")

tab_next, tab_res, tab_class = st.tabs(["Calendario", "Resultados", "Clasificación"])

with tab_next:
    for m in upcoming:
        with st.container(border=True):
            st.markdown(f"**{opponent(m)}** · {'🏠' if m['home'] == team else '✈️'}  \n{fmt_when(m)}"
                        + (f" · {m['court']}" if m["court"] else ""))
            st.markdown(BADGE[schedule_status(m, now)])
    st.markdown("[📅 Calendario .ics](https://raw.githubusercontent.com/ramonsierrarey/liga_vcm/main/data/feel_alcobendas.ics)")

with tab_res:
    for m in reversed(played):
        r = m["result"]
        mine = r["home"] if m["home"] == team else r["away"]
        theirs = r["away"] if m["home"] == team else r["home"]
        icon = "✅" if mine > theirs else "❌"
        with st.container(border=True):
            st.markdown(f"{icon} **{title(m)}**  {r['home']}–{r['away']}  \n{fmt_when(m)} · {', '.join(r['sets'])}")

with tab_class:
    df = pd.DataFrame(data["standings"]).rename(
        columns={"pos": "#", "team": "Equipo", "pj": "PJ", "g3": "G3", "g2": "G2", "p1": "P1", "p0": "P0",
                 "sf": "SF", "sc": "SC", "pf": "PF", "pc": "PC", "pts": "Pts"}
    )
    st.dataframe(
        df.style.apply(lambda r: ["background-color: #ffe9a8; color: #000" if r["Equipo"] == team else "" for _ in r], axis=1),
        hide_index=True,
        width="stretch",
    )
