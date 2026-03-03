import streamlit as st
import requests
from datetime import datetime
import pytz
import datetime as dt

st.set_page_config(page_title="NHL pinnacle Props", page_icon="🏒", layout="wide")
st.title("NHL pinnacle - player_goals Props")

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

    # Step 1: get all events
    with st.spinner("Fetching events..."):
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events?apiKey={api_key}",
            timeout=60
        )
    events = r.json()

    # Filter to selected ET date
    today_events = []
    for e in events:
        utc_dt  = dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        et_date = utc_dt.astimezone(tz).strftime("%Y-%m-%d")
        if et_date == selected_date:
            today_events.append(e)

    st.write(f"**Games on {selected_date}:** {len(today_events)}")
    if not today_events:
        all_dates = sorted(set(
            dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=pytz.utc).astimezone(tz).strftime("%Y-%m-%d")
            for e in events
        ))
        st.warning(f"No games on {selected_date}. Available dates: {all_dates}")
        st.stop()

    # Step 2: fetch player_goals from pinnacle for ALL games today
    st.markdown("---")
    st.write(f"Fetching `player_goals` from pinnacle for {len(today_events)} games...")

    all_raw = []
    req_count = 1
    progress = st.progress(0)

    for i, event in enumerate(today_events):
        url = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}&regions=us,eu,uk,au"
            f"&markets=player_goals"
            f"&oddsFormat=american&bookmakers=pinnacle"
        )
        resp = requests.get(url, timeout=30)
        req_count += 1
        all_raw.append({
            "game": f"{event['away_team']} @ {event['home_team']}",
            "status": resp.status_code,
            "data": resp.json()
        })
        progress.progress((i + 1) / len(today_events))

    st.write(f"Requests used: `{req_count}`  |  Remaining: `{resp.headers.get('x-requests-remaining', 'N/A')}`")

    # Step 3: show raw JSON for each game
    st.markdown("---")
    st.subheader("Raw JSON per game")
    for item in all_raw:
        with st.expander(f"{item['game']} (status {item['status']})"):
            st.json(item["data"])
