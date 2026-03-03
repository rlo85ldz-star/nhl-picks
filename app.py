import streamlit as st
import requests
from datetime import datetime
import pytz
import datetime as dt

st.set_page_config(page_title="NHL Raw Debug", page_icon="🏒", layout="wide")

st.title("NHL FanDuel Raw Debug")

with st.sidebar:
    api_key = st.text_input("Odds API Key", type="password", placeholder="the-odds-api.com key")

import datetime as _dt
_et  = pytz.timezone("America/Toronto")
_now = datetime.now(_et)
_d0  = _now.strftime("%Y-%m-%d")
_d1  = (_now + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
_d2  = (_now + _dt.timedelta(days=2)).strftime("%Y-%m-%d")
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

    # Step 1: get events
    with st.spinner("Fetching events..."):
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events?apiKey={api_key}",
            timeout=60
        )
    st.write(f"Events response code: `{r.status_code}`")
    events = r.json()
    st.write(f"Total events returned: `{len(events)}`")

    # Show all events with their ET dates
    all_et = []
    for e in events:
        utc_dt  = dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        et_date = utc_dt.astimezone(tz).strftime("%Y-%m-%d")
        all_et.append({"id": e["id"], "game": f"{e['away_team']} @ {e['home_team']}", "et_date": et_date, "utc": e["commence_time"]})

    st.write("**All events and their ET dates:**")
    st.dataframe(all_et)

    # Filter to selected date
    today_events = [e for e in all_et if e["et_date"] == selected_date]
    st.write(f"**Events on {selected_date}:** {len(today_events)}")

    if not today_events:
        st.warning(f"No games on {selected_date}. Pick a date from the list above.")
        st.stop()

    # Step 2: fetch FanDuel props for first game only to see raw JSON
    first = next(e for e in events if e["id"] == today_events[0]["id"])
    st.markdown(f"---\n**Fetching FanDuel props for: {today_events[0]['game']}**")

    url = (
        f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{first['id']}/odds"
        f"?apiKey={api_key}&regions=us,eu,uk,au"
        f"&markets=player_goals,player_goal_scorer,player_goals_scored,player_anytime_goal_scorer,player_to_score"
        f"&oddsFormat=american&bookmakers=fanduel"
    )
    st.write(f"URL (key hidden): `...events/{first['id']}/odds?regions=us,eu,uk,au&markets=player_goals,...&bookmakers=fanduel`")

    with st.spinner("Fetching props..."):
        resp = requests.get(url, timeout=30)

    st.write(f"Props response code: `{resp.status_code}`")
    st.write(f"Remaining requests: `{resp.headers.get('x-requests-remaining', 'N/A')}`")

    st.markdown("**Raw JSON from FanDuel:**")
    st.json(resp.json())
