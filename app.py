import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="NHL Goal Probabilities", page_icon="🏒", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Bebas+Neue&display=swap');
  html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace; background-color: #0a0c10; color: #e0e0e0; }
  .main, .block-container { background-color: #0a0c10; padding-top: 1.5rem; max-width: 800px; }
  h1 { font-family: 'Bebas Neue', sans-serif; color: #00ff9d; letter-spacing: 4px; font-size: 2.2rem; }
  .stButton>button { background: #00ff9d; color: #000; font-weight: 700; border: none; border-radius: 8px; width: 100%; }
  .stButton>button:hover { background: #00cc7a; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #16213e; color: #00ff9d; padding: 10px 14px; text-align: left; font-size: 0.7rem; letter-spacing: 1px; }
  td { padding: 9px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }
  tr:hover td { background: rgba(255,255,255,0.03); }
  .bar-wrap { background: rgba(255,255,255,0.07); border-radius: 3px; height: 6px; width: 120px; display: inline-block; vertical-align: middle; margin-left: 8px; }
  .bar-fill  { height: 6px; border-radius: 3px; }
  footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("# NHL GOAL PROBABILITIES")
st.markdown("<p style='color:#555;font-size:0.75rem;letter-spacing:2px;margin-top:-12px'>FANDUEL · PLAYER_GOALS MARKET · OVER 0.5</p>", unsafe_allow_html=True)

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
        st.markdown(f"<span style='color:{col};font-weight:700'>{quota_used}</span><span style='color:#555'> / 500 &nbsp;·&nbsp; </span><span style='color:#00ff9d;font-weight:700'>{quota_rem} left</span>", unsafe_allow_html=True)
        if quota_rem <= 50: st.warning(f"Only {quota_rem} requests left!")

# ── Date picker
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

st.markdown("---")

# ── Fetch
def american_to_implied(a):
    dec = (a / 100 + 1) if a > 0 else (100 / abs(a) + 1)
    return 1 / dec

def remove_vig(yes_p, no_p):
    return yes_p / (yes_p + no_p)

def fetch_data(api_key, target_date):
    import datetime as dt
    tz = pytz.timezone("America/Toronto")

    # Get all NHL events
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
        import datetime as dt2
        utc_t    = dt2.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        et_date  = utc_t.astimezone(tz).strftime("%Y-%m-%d")
        if et_date == target_date:
            today_events.append(e)

    all_dates = sorted(set(
        dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=pytz.utc).astimezone(tz).strftime("%Y-%m-%d")
        for e in events
    ))

    if not today_events:
        return [], 1, all_dates, []

    players   = {}
    req_count = 1
    raw       = []

    # Track all bookmakers and markets seen across all responses
    seen_bookmakers = []
    seen_markets    = []

    for event in today_events:
        # Step A: fetch with NO bookmaker filter and ALL regions to see everything available
        url_discover = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}&regions=us,eu,uk,au"
            f"&markets=player_goals,player_goal_scorer,player_goals_scored,player_anytime_goal_scorer,player_to_score"
            f"&oddsFormat=american"
        )
        resp = requests.get(url_discover, timeout=30)
        req_count += 1
        if resp.status_code != 200:
            continue

        data = resp.json()
        raw.append(data)
        game = f"{event['away_team']} @ {event['home_team']}"

        # Catalog every bookmaker and market key we receive
        for bm in data.get("bookmakers", []):
            bk = bm["key"]
            if bk not in seen_bookmakers:
                seen_bookmakers.append(bk)
            for mkt in bm.get("markets", []):
                mk = mkt["key"]
                entry = f"{bk}:{mk}"
                if entry not in seen_markets:
                    seen_markets.append(entry)

        # Now extract Pinnacle goal props (try all goal market keys)
        goal_market_keys = {
            "player_goals", "player_goal_scorer", "player_goals_scored",
            "player_anytime_goal_scorer", "player_to_score",
        }
        for bm in data.get("bookmakers", []):
            if bm["key"] != "fanduel":
                continue
            for mkt in bm.get("markets", []):
                if mkt["key"] not in goal_market_keys:
                    continue
                by_player = {}
                for outcome in mkt.get("outcomes", []):
                    name  = outcome["name"]
                    price = outcome["price"]
                    desc  = (outcome.get("description") or "").lower()
                    point = outcome.get("point", None)
                    if name not in by_player:
                        by_player[name] = {}
                    if desc == "over":
                        by_player[name]["over"] = price
                    elif desc == "under":
                        by_player[name]["under"] = price
                    elif desc in ("yes", "scorer", "to score", "anytime"):
                        by_player[name]["over"] = price
                    elif desc == "no":
                        by_player[name]["under"] = price

                for name, odds in by_player.items():
                    if "over" not in odds:
                        continue
                    raw_yes = american_to_implied(odds["over"])
                    if "under" in odds:
                        prob = remove_vig(raw_yes, american_to_implied(odds["under"]))
                    else:
                        prob = raw_yes
                    players[name] = {
                        "name":  name,
                        "game":  game,
                        "prob":  prob,
                        "over":  odds["over"],
                        "under": odds.get("under"),
                    }

    st.session_state["debug_seen_bookmakers"] = seen_bookmakers
    st.session_state["debug_seen_markets"]    = seen_markets

    results = sorted(players.values(), key=lambda x: x["prob"], reverse=True)
    return results, req_count, all_dates, raw

# ── Main display
if not api_key:
    st.info("Add your the-odds-api.com key in the sidebar, then click FETCH.")
    st.stop()

if fetch_btn or "pin_results" in st.session_state:
    if fetch_btn:
        st.session_state.pop("pin_results", None)
        with st.spinner("Fetching Pinnacle player_goals odds..."):
            try:
                results, reqs, all_dates, raw = fetch_data(api_key, selected_date)
                st.session_state["pin_results"]  = results
                st.session_state["pin_reqs"]     = reqs
                st.session_state["pin_dates"]    = all_dates
                st.session_state["pin_raw"]      = raw
                st.session_state["pin_date_sel"] = selected_date
            except requests.HTTPError as e:
                st.error(f"API error: {e} — check your key")
                st.stop()
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

    results     = st.session_state.get("pin_results", [])
    reqs        = st.session_state.get("pin_reqs", 0)
    all_dates   = st.session_state.get("pin_dates", [])
    date_sel    = st.session_state.get("pin_date_sel", selected_date)

    # ── Debug expander
    with st.expander("Debug info — open this if no players appear"):
        st.write(f"**Selected date (ET):** `{date_sel}`")
        st.write(f"**Dates with NHL games in API:** {all_dates}")
        st.write(f"**Players found:** {len(results)}")
        st.write(f"**API requests used this fetch:** {reqs}")
        st.markdown("---")
        st.markdown("**Bookmakers that returned ANY data:**")
        st.write(st.session_state.get("debug_seen_bookmakers", []))
        st.markdown("**All bookmaker:market combinations returned:**")
        st.write(st.session_state.get("debug_seen_markets", []))
        st.caption("If 'pinnacle' is not in the bookmakers list above, the API does not have Pinnacle props for this sport/market. Share this with Claude to diagnose.")
        if st.checkbox("Show full raw JSON"):
            st.json(st.session_state.get("pin_raw", []))

    if not results:
        st.warning(f"No Pinnacle player_goals props found for **{date_sel}**. Either no games are scheduled, or Pinnacle hasn't posted lines yet (usually 2-4 hrs before puck drop).")
        st.stop()

    st.markdown(f"**{len(results)} players** found for **{date_sel}** — sorted by goal probability")
    st.markdown("<br>", unsafe_allow_html=True)

    # Build HTML table
    rows = ""
    for i, p in enumerate(results):
        pct      = p["prob"] * 100
        bar_w    = min(int(p["prob"] * 240), 240)
        bar_col  = "#00ff9d" if pct >= 30 else ("#FFE066" if pct >= 20 else ("#FF9933" if pct >= 15 else "#ff6b6b"))
        over_str = f"+{p['over']}" if p["over"] > 0 else str(p["over"])
        under_str = (f"+{p['under']}" if p["under"] and p["under"] > 0 else str(p["under"])) if p["under"] else "—"
        rank_col = "#00ff9d" if i < 3 else "#444"

        rows += f"""
        <tr>
          <td style='color:{rank_col};font-weight:700'>{i+1}</td>
          <td style='font-weight:{"700" if i < 5 else "400"};color:#f0f0f0'>{p['name']}</td>
          <td style='color:#888;font-size:0.78rem'>{p['game']}</td>
          <td style='font-weight:700;color:{bar_col}'>{pct:.1f}%
            <span class='bar-wrap'><span class='bar-fill' style='width:{bar_w}px;background:{bar_col}'></span></span>
          </td>
          <td style='color:#aaa;font-family:monospace'>{over_str}</td>
          <td style='color:#555;font-family:monospace'>{under_str}</td>
        </tr>"""

    st.markdown(f"""
    <table>
      <thead><tr>
        <th>#</th><th>PLAYER</th><th>GAME</th>
        <th>PROB (vig-removed)</th>
        <th>OVER 0.5</th><th>UNDER 0.5</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Source: FanDuel · Market: player_goals · Requests used: {reqs} · Not gambling advice")
