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
st.markdown("<p style='color:#555;font-size:0.75rem;letter-spacing:2px;margin-top:-12px'>PINNACLE · PLAYER_GOALS MARKET · OVER 0.5</p>", unsafe_allow_html=True)

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
        if quota_rem is not None and quota_rem <= 50:
            st.warning(f"Only {quota_rem} requests left!")

# ── Date picker
TZ = pytz.timezone("America/Toronto")
now_et = datetime.now(TZ)
d0 = now_et.strftime("%Y-%m-%d")
d1 = (now_et + dt.timedelta(days=1)).strftime("%Y-%m-%d")
d2 = (now_et + dt.timedelta(days=2)).strftime("%Y-%m-%d")
date_options = {f"Today ({d0})": d0, d1: d1, d2: d2}

col_date, col_btn = st.columns([3, 1])
with col_date:
    selected_label = st.selectbox("Game Date", list(date_options.keys()), index=0)
    selected_date  = date_options[selected_label]
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("FETCH", use_container_width=True)

st.markdown("---")

# ── Helper functions
def american_to_implied(a):
    dec = (a / 100 + 1) if a > 0 else (100 / abs(a) + 1)
    return 1 / dec

def remove_vig(yes_p, no_p):
    return yes_p / (yes_p + no_p)

def utc_str_to_et_date(utc_str):
    """Convert '2026-03-03T23:00:00Z' to ET date string 'YYYY-MM-DD'."""
    utc_dt = dt.datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
    return utc_dt.astimezone(TZ).strftime("%Y-%m-%d")

# ── Main fetch function
def fetch_data(api_key, target_date):

    # Step 1: get all upcoming NHL events
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

    # Step 2: show ALL ET dates available so we can debug
    all_et_dates = sorted(set(utc_str_to_et_date(e["commence_time"]) for e in events))

    # Step 3: filter to selected ET date
    today_events = [e for e in events if utc_str_to_et_date(e["commence_time"]) == target_date]

    if not today_events:
        return [], 1, all_et_dates, [], []

    # Step 4: fetch props — no bookmaker filter so we can see ALL books + markets
    players    = {}
    req_count  = 1
    raw        = []
    seen_books = []
    seen_mkts  = []

    for event in today_events:
        url = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}"
            f"&regions=us,eu,uk,au"
            f"&markets=player_goals,player_goal_scorer,player_goals_scored,player_anytime_goal_scorer,player_to_score"
            f"&oddsFormat=american"
        )
        resp = requests.get(url, timeout=30)
        req_count += 1
        if resp.status_code != 200:
            continue

        data = resp.json()
        raw.append(data)
        game = f"{event['away_team']} @ {event['home_team']}"

        # Catalog everything returned
        for bm in data.get("bookmakers", []):
            bk = bm["key"]
            if bk not in seen_books:
                seen_books.append(bk)
            for mkt in bm.get("markets", []):
                entry = f"{bk}:{mkt['key']}"
                if entry not in seen_mkts:
                    seen_mkts.append(entry)

        # Extract Pinnacle only
        for bm in data.get("bookmakers", []):
            if bm["key"] != "pinnacle":
                continue
            for mkt in bm.get("markets", []):
                by_player = {}
                for outcome in mkt.get("outcomes", []):
                    name  = outcome["name"]
                    price = outcome["price"]
                    desc  = (outcome.get("description") or "").lower()
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

    results = sorted(players.values(), key=lambda x: x["prob"], reverse=True)
    return results, req_count, all_et_dates, seen_books, seen_mkts

# ── Display
if not api_key:
    st.info("Add your the-odds-api.com key in the sidebar, then click FETCH.")
    st.stop()

if fetch_btn or "pin_results" in st.session_state:
    if fetch_btn:
        st.session_state.pop("pin_results", None)
        with st.spinner("Fetching Pinnacle player_goals odds..."):
            try:
                results, reqs, all_dates, seen_books, seen_mkts = fetch_data(api_key, selected_date)
                st.session_state["pin_results"]   = results
                st.session_state["pin_reqs"]      = reqs
                st.session_state["pin_dates"]     = all_dates
                st.session_state["pin_date_sel"]  = selected_date
                st.session_state["pin_books"]     = seen_books
                st.session_state["pin_mkts"]      = seen_mkts
            except requests.HTTPError as e:
                st.error(f"API error: {e} — check your key")
                st.stop()
            except Exception as e:
                import traceback
                st.error(f"Error: {e}\n\n{traceback.format_exc()}")
                st.stop()

    results    = st.session_state.get("pin_results", [])
    reqs       = st.session_state.get("pin_reqs", 0)
    all_dates  = st.session_state.get("pin_dates", [])
    date_sel   = st.session_state.get("pin_date_sel", selected_date)
    seen_books = st.session_state.get("pin_books", [])
    seen_mkts  = st.session_state.get("pin_mkts", [])

    # Debug panel
    with st.expander("Debug info (open if no players appear)"):
        st.write(f"**Selected date (ET):** `{date_sel}`")
        st.write(f"**All ET dates with games in API:** {all_dates}")
        st.write(f"**Games on selected date:** {len([e for e in st.session_state.get('pin_dates', []) if e == date_sel])}")
        st.write(f"**All bookmakers returned:** {seen_books}")
        st.write(f"**All book:market combinations:** {seen_mkts}")
        st.write(f"**Players parsed:** {len(results)}")
        st.write(f"**API requests used:** {reqs}")
        st.caption("Key check: does 'pinnacle' appear in bookmakers? If not, Pinnacle props may require a paid API tier.")
        if st.checkbox("Show raw JSON"):
            st.json(st.session_state.get("pin_raw", []))

    # No games at all
    games_today = [d for d in all_dates if d == date_sel]
    if not games_today:
        st.warning(f"No NHL games found for **{date_sel}**. Available dates: {all_dates}")
        st.stop()

    # Games found but no props
    if not results:
        st.warning(
            f"Games found for **{date_sel}** but no Pinnacle player props returned.  \n"
            f"Books available: `{seen_books}`  \n"
            f"Markets available: `{seen_mkts}`  \n\n"
            f"If `pinnacle` is not in the books list, the free API tier may not include Pinnacle player props."
        )
        st.stop()

    # Results table
    st.markdown(f"**{len(results)} players** from Pinnacle for **{date_sel}** — sorted by goal probability")
    st.markdown("<br>", unsafe_allow_html=True)

    rows = ""
    for i, p in enumerate(results):
        pct     = p["prob"] * 100
        bar_w   = min(int(p["prob"] * 240), 240)
        bar_col = "#00ff9d" if pct >= 30 else ("#FFE066" if pct >= 20 else ("#FF9933" if pct >= 15 else "#ff6b6b"))
        over_s  = f"+{p['over']}" if p["over"] > 0 else str(p["over"])
        under_s = (f"+{p['under']}" if p["under"] and p["under"] > 0 else str(p["under"])) if p["under"] else "—"
        rank_col = "#00ff9d" if i < 3 else "#444"

        rows += (
            "<tr>"
            f"<td style='color:{rank_col};font-weight:700'>{i+1}</td>"
            f"<td style='font-weight:{'700' if i < 5 else '400'};color:#f0f0f0'>{p['name']}</td>"
            f"<td style='color:#888;font-size:0.78rem'>{p['game']}</td>"
            f"<td style='font-weight:700;color:{bar_col}'>{pct:.1f}%"
            f"<span class='bar-wrap'><span class='bar-fill' style='width:{bar_w}px;background:{bar_col}'></span></span></td>"
            f"<td style='color:#aaa;font-family:monospace'>{over_s}</td>"
            f"<td style='color:#555;font-family:monospace'>{under_s}</td>"
            "</tr>"
        )

    st.markdown(
        "<table><thead><tr>"
        "<th>#</th><th>PLAYER</th><th>GAME</th>"
        "<th>PROB (vig-removed)</th><th>OVER 0.5</th><th>UNDER 0.5</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Source: Pinnacle · Market: player_goals · Requests used: {reqs} · Not gambling advice")
