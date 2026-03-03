import streamlit as st
import requests
from datetime import datetime
import pytz
import datetime as dt

st.set_page_config(page_title="NHL Debug", page_icon="🏒", layout="wide")
st.title("NHL FanDuel - Raw JSON All Games")

with st.sidebar:
    api_key = st.text_input("Odds API Key", type="password", placeholder="the-odds-api.com key")

_et  = pytz.timezone("America/Toronto")
_now = datetime.now(_et)
_d0  = _now.strftime("%Y-%m-%d")
_d1  = (_now + dt.timedelta(days=1)).strftime("%Y-%m-%d")
_d2  = (_now + dt.timedelta(days=2)).strftime("%Y-%m-%d")
_date_labels = {f"Today ({_d0})": _d0, _d1: _d1, _d2: _d2}

col_date, col_btn = st.columns([3, 1])
with col_date:
    selected_label = st.selectbox("Game Date", list(_date_labels.keys()), index=0)
    selected_date  = _date_labels[selected_label]
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("FETCH", use_container_width=True)

if not api_key:
    st.info("Add your API key in the sidebar.")
    st.stop()

if fetch_btn:
    tz = pytz.timezone("America/Toronto")

    with st.spinner("Fetching events..."):
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events?apiKey={api_key}",
            timeout=60
        )
    events = r.json()

    today_events = []
    for e in events:
        utc_dt  = dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        et_date = utc_dt.astimezone(tz).strftime("%Y-%m-%d")
        if et_date == selected_date:
            today_events.append(e)

    st.write(f"**Games on {selected_date}:** {len(today_events)}")
    if not today_events:
        st.warning("No games found. Try a different date.")
        st.stop()

    st.markdown("---")

    # Fetch ALL markets (not just player_goals) so we can see exactly what FanDuel offers
    for event in today_events:
        game_label = f"{event['away_team']} @ {event['home_team']}"
        
        # Try player_goals first
        url = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}&regions=us,eu,uk,au"
            f"&markets=player_goals"
            f"&oddsFormat=american&bookmakers=fanduel"
        )
        resp = requests.get(url, timeout=30)
        data = resp.json()

        bookmakers = data.get("bookmakers", [])
        has_data   = len(bookmakers) > 0

        with st.expander(f"{'✅' if has_data else '❌'}  {game_label}  (status {resp.status_code}, bookmakers: {len(bookmakers)})"):
            st.json(data)

    remaining = resp.headers.get("x-requests-remaining", "N/A")
    st.markdown("---")
    st.write(f"Requests remaining: `{remaining}`")
    st.info("Share the JSON from any ✅ game above and I will parse it correctly.")
