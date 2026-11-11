# Feel Alcobendas · Liga VCM (Femenino · Oro)

- `check.py`: lee la web con Playwright, avisa por Telegram y guarda `data/state.json` + `data/feel_alcobendas.ics`.
- `app.py`: web Streamlit que lee `data/state.json`.
- `.github/workflows/check.yml`: ejecuta `check.py` cada hora.

## Puesta en marcha
1. Sube el proyecto a un repo de GitHub.
2. Telegram: crea un bot con @BotFather (token), escríbele un mensaje y obtén tu chat id en
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Repo > Settings > Secrets > Actions: `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
4. Actions > "Comprobar liga VCM" > Run workflow (la primera vez solo manda "Vigilancia activada").
5. share.streamlit.io: nueva app con `app.py` de ese repo.
6. El repositorio es privado, así que el .ics (`data/feel_alcobendas.ics`) no tiene URL pública de suscripción.

Local: `pip install -r requirements.txt -r requirements-check.txt; python -m playwright install chromium; python check.py; streamlit run app.py`

Un horario es orientativo hasta el martes 05:00 (Madrid) de la semana del partido; después se marca como confirmado.
