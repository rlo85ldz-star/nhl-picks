import streamlit as st
import requests
from datetime import datetime
import pytz
import datetime as dt

st.set_page_config(page_title="NHL Goal Probabilities", page_icon="🏒", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Bebas+Neue&display=swap');
  html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace; background-color: #0a0c10; color: #e0e0e0; }
  .main, .block-container { background-color: #0a0c10; padding-top: 1.5rem; max-width: 900px; }
  h1 { font-family: 'Bebas Neue', sans-serif; color: #00ff9d; letter-spacing: 4px; font-size: 2.2rem; }
  .stButton>button { background: #00ff9d; color: #000; font-weight: 700; border: none; border-radius: 8px; width: 100%; }
  .stButton>button:hover { background: #00cc7a; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #16213e; color: #00ff9d; padding: 10px 14px; text-align: left; font-size: 0.7rem; letter-spacing: 1px; border-bottom: 1px solid rgba(0,255,157,0.2); }
  td { padding: 9px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: middle; }
  tr:hover td { background: rgba(255,255,255,0.03); }
  .bar-wrap { background: rgba(255,255,255,0.07); border-radius: 3px; height: 6px; width: 100px; display: inline-block; vertical-align: middle; margin-left: 8px; }
  .bar-fill  { height: 6px; border-radius: 3px; }
  footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("# NHL GOAL PROBABILITIES")
st.markdown("<p style='color:#555;font-size:0.75rem;letter-spacing:2px;margin-top:-12px'>FANDUEL · PLAYER_GOALS · OVER 0.5 · VIG REMOVED</p>", unsafe_allow_html=True)

# ── Sidebar
with st.sidebar:
    st.markdown("### Settings")
    api_key = st.text_input("Odds API Key", type="password", placeholder="the-odds-api.com key")
    quota_used = st.session_state.get("quota_used")
    quota_rem  = st.session_state.get("quota_remaining")
    if quota_used is not None:
        pct = quota_used / 500
        col = "#00ff9d" if pct < 0.6 else ("#FFE066" if pct < 0.85 else "#ff6b6b")
        bar = "#" * int(pct * 20) + "." * (20 - int(pct * 20))
        st.markdown("---")
        st.markdown("**API Quota**")
        st.markdown(f"<div style='font-family:monospace;color:{col};font-size:0.75rem'>{bar}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<span style='color:{col};font-weight:700'>{quota_used}</span>"
            f"<span style='color:#555'> / 500 &nbsp;·&nbsp; </span>"
            f"<span style='color:#00ff9d;font-weight:700'>{quota_rem} left</span>",
            unsafe_allow_html=True
        )
        if quota_rem and quota_rem <= 50:
            st.warning(f"Only {quota_rem} requests left!")

# ── Date picker
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

st.markdown("---")

# ── Helpers
def american_to_implied(a):
    return 1 / ((a / 100 + 1) if a > 0 else (100 / abs(a) + 1))

def remove_vig(yes_p, no_p):
    return yes_p / (yes_p + no_p)

def fmt_odds(o):
    return f"+{o}" if o > 0 else str(o)

# ── Fetch & parse
def fetch_data(api_key, target_date):
    tz = pytz.timezone("America/Toronto")

    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events?apiKey={api_key}",
        timeout=60
    )
    r.raise_for_status()
    events = r.json()

    try:
        st.session_state["quota_used"]      = int(r.headers.get("x-requests-used", 0))
        st.session_state["quota_remaining"] = int(r.headers.get("x-requests-remaining", 500))
    except Exception:
        pass

    # Filter to selected ET date
    today_events = []
    for e in events:
        utc_dt  = dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        et_date = utc_dt.astimezone(tz).strftime("%Y-%m-%d")
        if et_date == target_date:
            today_events.append(e)

    all_et_dates = sorted(set(
        dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=pytz.utc).astimezone(tz).strftime("%Y-%m-%d")
        for e in events
    ))

    if not today_events:
        return [], 1, all_et_dates

    players   = {}
    req_count = 1
    progress  = st.progress(0, text="Fetching props...")

    for idx, event in enumerate(today_events):
        away = event["away_team"]
        home = event["home_team"]

        url = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}&regions=us,eu,uk,au"
            f"&markets=player_goals"
            f"&oddsFormat=american&bookmakers=fanduel"
        )
        resp = requests.get(url, timeout=30)
        req_count += 1
        progress.progress((idx + 1) / len(today_events), text=f"{away} @ {home}...")

        try:
            st.session_state["quota_used"]      = int(resp.headers.get("x-requests-used", 0))
            st.session_state["quota_remaining"] = int(resp.headers.get("x-requests-remaining", 500))
        except Exception:
            pass

        if resp.status_code != 200:
            continue

        data = resp.json()

        for bm in data.get("bookmakers", []):
            if bm["key"] != "fanduel":
                continue
            for mkt in bm.get("markets", []):
                if mkt["key"] != "player_goals":
                    continue

                # Structure: name = "Over"/"Under", description = player name, point = 0.5
                by_player = {}
                for outcome in mkt.get("outcomes", []):
                    player_name = outcome.get("description", "")
                    price       = outcome["price"]
                    side        = outcome["name"].lower()  # "over" or "under"

                    if not player_name:
                        continue
                    if player_name not in by_player:
                        by_player[player_name] = {}
                    by_player[player_name][side] = price

                for player_name, odds in by_player.items():
                    if "over" not in odds:
                        continue
                    raw_yes = american_to_implied(odds["over"])
                    if "under" in odds:
                        prob = remove_vig(raw_yes, american_to_implied(odds["under"]))
                    else:
                        prob = raw_yes

                    players[player_name] = {
                        "name":  player_name,
                        "away":  away,
                        "home":  home,
                        "date":  target_date,
                        "prob":  prob,
                        "over":  fmt_odds(odds["over"]),
                        "under": fmt_odds(odds["under"]) if "under" in odds else "—",
                    }

    progress.empty()
    results = sorted(players.values(), key=lambda x: x["prob"], reverse=True)
    return results, req_count, all_et_dates

# ── Main
if not api_key:
    st.info("Add your the-odds-api.com key in the sidebar, then click FETCH.")
    st.stop()

if fetch_btn or "fd_results" in st.session_state:
    if fetch_btn:
        st.session_state.pop("fd_results", None)
        try:
            results, reqs, all_dates = fetch_data(api_key, selected_date)
            st.session_state["fd_results"]  = results
            st.session_state["fd_reqs"]     = reqs
            st.session_state["fd_dates"]    = all_dates
            st.session_state["fd_date_sel"] = selected_date
        except Exception as e:
            import traceback
            st.error(f"Error: {e}\n\n{traceback.format_exc()}")
            st.stop()

    results   = st.session_state.get("fd_results", [])
    reqs      = st.session_state.get("fd_reqs", 0)
    all_dates = st.session_state.get("fd_dates", [])
    date_sel  = st.session_state.get("fd_date_sel", selected_date)

    if not all_dates or date_sel not in all_dates:
        st.warning(f"No NHL games found for **{date_sel}**. Available dates: {all_dates}")
        st.stop()

    if not results:
        st.warning(f"No FanDuel player_goals props found for **{date_sel}**. Props usually post 2-4 hours before puck drop.")
        st.stop()

    st.markdown(f"**{len(results)} players** · FanDuel · **{date_sel}** · sorted by probability")
    st.markdown("<br>", unsafe_allow_html=True)

    rows = ""
    for i, p in enumerate(results):
        pct      = p["prob"] * 100
        bar_w    = min(int(p["prob"] * 200), 200)
        bar_col  = "#00ff9d" if pct >= 30 else ("#FFE066" if pct >= 20 else ("#FF9933" if pct >= 15 else "#ff6b6b"))
        rank_col = "#00ff9d" if i < 3 else ("#FFE066" if i < 10 else "#444")
        bold     = "700" if i < 5 else "400"

        rows += (
            "<tr>"
            f"<td style='color:{rank_col};font-weight:700;width:40px'>{i+1}</td>"
            f"<td style='color:#f0f0f0;font-weight:{bold}'>{p['name']}</td>"
            f"<td style='color:#aaa;font-size:0.8rem'>{p['away']}</td>"
            f"<td style='color:#555;font-size:0.75rem;text-align:center'>@</td>"
            f"<td style='color:#aaa;font-size:0.8rem'>{p['home']}</td>"
            f"<td style='color:#555;font-size:0.75rem'>{p['date']}</td>"
            f"<td style='font-weight:700;color:{bar_col};white-space:nowrap'>{pct:.1f}%"
            f"<span class='bar-wrap'><span class='bar-fill' style='width:{bar_w}px;background:{bar_col}'></span></span></td>"
            f"<td style='color:#aaa;font-family:monospace;font-size:0.8rem'>{p['over']}</td>"
            f"<td style='color:#555;font-family:monospace;font-size:0.8rem'>{p['under']}</td>"
            "</tr>"
        )

    st.markdown(
        "<table><thead><tr>"
        "<th>#</th><th>PLAYER</th><th>AWAY</th><th></th><th>HOME</th><th>DATE</th>"
        "<th>PROBABILITY</th><th>OVER 0.5</th><th>UNDER 0.5</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Source: FanDuel · Market: player_goals · Requests used: {reqs} · Not gambling advice")
