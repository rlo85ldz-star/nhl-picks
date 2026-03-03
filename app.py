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
  .bar-fill { height: 6px; border-radius: 3px; }
  .pick-card { background: linear-gradient(135deg, rgba(0,255,157,0.07), rgba(0,255,157,0.02)); border: 1px solid rgba(0,255,157,0.25); border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; }
  .pick-label { font-size: 0.65rem; color: #00ff9d; letter-spacing: 3px; margin-bottom: 6px; }
  .pick-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.6rem; color: #fff; letter-spacing: 2px; }
  .pick-meta { font-size: 0.75rem; color: #888; margin-top: 4px; }
  .pick-prob { font-size: 1.1rem; font-weight: 700; margin-top: 6px; }
  .no-match { background: rgba(255,80,80,0.06); border: 1px solid rgba(255,80,80,0.2); border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; color: #ff8888; font-size: 0.85rem; }
  footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("# NHL GOAL PROBABILITIES")
st.markdown("<p style='color:#555;font-size:0.75rem;letter-spacing:2px;margin-top:-12px'>FANDUEL · PLAYER_GOALS · TIM HORTONS PICKS OPTIMIZER</p>", unsafe_allow_html=True)

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
    st.markdown("---")
    st.markdown("**How to use**")
    st.markdown("""
1. Select game date  
2. Click **FETCH** to load FanDuel odds  
3. Go to [hockeychallengehelper.com](https://hockeychallengehelper.com)  
4. Paste the eligible players for each pick slot below  
5. App picks the highest-probability player per slot
""")

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
    fetch_btn = st.button("FETCH ODDS", use_container_width=True)

st.markdown("---")

# ── Helpers
def american_to_implied(a):
    return 1 / ((a / 100 + 1) if a > 0 else (100 / abs(a) + 1))

def remove_vig(yes_p, no_p):
    return yes_p / (yes_p + no_p)

def fmt_odds(o):
    return f"+{o}" if o > 0 else str(o)

# ── Fetch
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
        return {}, 1, all_et_dates

    players   = {}
    req_count = 1
    progress  = st.progress(0, text="Fetching props...")

    for idx, event in enumerate(today_events):
        away = event["away_team"]
        home = event["home_team"]
        url  = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            # f"?apiKey={api_key}&regions=us,eu,uk,au"
            f"?apiKey={api_key}&regions=us"
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
            # st.warning(f"Failed to fetch {away} @ {home}: status {resp.status_code}")
            continue

        for bm in resp.json().get("bookmakers", []):
            if bm["key"] != "fanduel":
                continue
            for mkt in bm.get("markets", []):
                if mkt["key"] != "player_goals":
                    continue
                by_player = {}
                for outcome in mkt.get("outcomes", []):
                    name  = outcome.get("description", "")
                    price = outcome["price"]
                    side  = outcome["name"].lower()
                    if not name:
                        continue
                    if name not in by_player:
                        by_player[name] = {}
                    by_player[name][side] = price

                for name, odds in by_player.items():
                    if "over" not in odds:
                        continue
                    raw_yes = american_to_implied(odds["over"])
                    prob    = remove_vig(raw_yes, american_to_implied(odds["under"])) if "under" in odds else raw_yes
                    # Store keyed by lowercase name for fuzzy matching
                    players[name.lower()] = {
                        "name":  name,
                        "away":  away,
                        "home":  home,
                        "date":  target_date,
                        "prob":  prob,
                        "over":  fmt_odds(odds["over"]),
                        "under": fmt_odds(odds["under"]) if "under" in odds else "—",
                    }

    progress.empty()
    return players, req_count, all_et_dates

def initial_last(full_name):
    """Convert 'David Pastrnak' -> 'd. pastrnak'"""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + ". " + " ".join(parts[1:])).lower()
    return full_name.strip().lower()

def find_player(players_dict, candidate):
    """Match a candidate like 'D. Pastrnak' against full names in players_dict."""
    candidate = candidate.strip().lower()
    # Build a lookup of initial.lastname -> player for every player we have
    for full_key, player in players_dict.items():
        if initial_last(player["name"]) == candidate:
            return player
        # Also try direct match in case full name was pasted
        if full_key == candidate:
            return player
    return None

def find_best(players_dict, candidates):
    """Given a list of candidate names, return the one with highest probability."""
    best = None
    for raw_name in candidates:
        match = find_player(players_dict, raw_name)
        if match and (best is None or match["prob"] > best["prob"]):
            best = match
    return best

# ── Main
if not api_key:
    st.info("Add your the-odds-api.com key in the sidebar, then click FETCH ODDS.")
    st.stop()

if fetch_btn or "fd_players" in st.session_state:
    if fetch_btn:
        st.session_state.pop("fd_players", None)
        try:
            players, reqs, all_dates = fetch_data(api_key, selected_date)
            st.session_state["fd_players"]  = players
            st.session_state["fd_reqs"]     = reqs
            st.session_state["fd_dates"]    = all_dates
            st.session_state["fd_date_sel"] = selected_date
        except Exception as e:
            import traceback
            st.error(f"Error: {e}\n\n{traceback.format_exc()}")
            st.stop()

    players   = st.session_state.get("fd_players", {})
    reqs      = st.session_state.get("fd_reqs", 0)
    all_dates = st.session_state.get("fd_dates", [])
    date_sel  = st.session_state.get("fd_date_sel", selected_date)

    if not all_dates or date_sel not in all_dates:
        st.warning(f"No NHL games found for **{date_sel}**. Available dates: {all_dates}")
        st.stop()

    if not players:
        st.warning(f"No FanDuel player_goals props found for **{date_sel}**. Props usually post 2-4 hours before puck drop.")
        st.stop()

    results = sorted(players.values(), key=lambda x: x["prob"], reverse=True)
    st.success(f"Loaded **{len(results)} players** from FanDuel for **{date_sel}**")

    # ── Section 1: Tim Hortons Pick Optimizer
    st.markdown("## TIM HORTONS PICK OPTIMIZER")
    st.markdown(
        "Go to [hockeychallengehelper.com](https://hockeychallengehelper.com), "
        "then paste the eligible players for each pick slot below (one name per line)."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        pick1_raw = st.text_area("Pick #1 — eligible players", height=160, placeholder="Sidney Crosby\nDavid Pastrnak\nConnor McDavid")
    with c2:
        pick2_raw = st.text_area("Pick #2 — eligible players", height=160, placeholder="Auston Matthews\nLeon Draisaitl\nNathan MacKinnon")
    with c3:
        pick3_raw = st.text_area("Pick #3 — eligible players", height=160, placeholder="Nikita Kucherov\nBrayden Point\nSam Reinhart")

    suggest_btn = st.button("SUGGEST PICKS", use_container_width=True)

    if suggest_btn or any([pick1_raw, pick2_raw, pick3_raw]):
        st.markdown("---")
        st.markdown("### SUGGESTED PICKS")

        for pick_num, raw_text in enumerate([pick1_raw, pick2_raw, pick3_raw], start=1):
            candidates = [n.strip() for n in raw_text.strip().splitlines() if n.strip()]
            if not candidates:
                st.markdown(f"<div class='no-match'>Pick #{pick_num} — no players entered</div>", unsafe_allow_html=True)
                continue

            best = find_best(players, candidates)
            if not best:
                names_tried = ", ".join(candidates)
                st.markdown(
                    f"<div class='no-match'>Pick #{pick_num} — none of these players found in FanDuel props: {names_tried}</div>",
                    unsafe_allow_html=True
                )
                continue

            pct     = best["prob"] * 100
            bar_col = "#00ff9d" if pct >= 30 else ("#FFE066" if pct >= 20 else "#FF9933")
            bar_w   = min(int(best["prob"] * 260), 260)

            st.markdown(f"""
<div class='pick-card'>
  <div class='pick-label'>PICK #{pick_num} &nbsp;·&nbsp; BEST OPTION</div>
  <div class='pick-name'>{best['name']}</div>
  <div class='pick-meta'>{best['away']} @ {best['home']} &nbsp;·&nbsp; {best['date']}</div>
  <div class='pick-prob' style='color:{bar_col}'>{pct:.1f}% chance of scoring
    <span class='bar-wrap'><span class='bar-fill' style='width:{bar_w}px;background:{bar_col}'></span></span>
  </div>
  <div style='font-size:0.75rem;color:#555;margin-top:6px'>FanDuel Over 0.5: {best['over']} &nbsp;·&nbsp; Under: {best['under']}</div>
</div>
""", unsafe_allow_html=True)

            # Show all candidates ranked
            ranked = []
            for raw_name in candidates:
                match = find_player(players, raw_name)
                if match:
                    ranked.append(match)
                else:
                    ranked.append({"name": raw_name.strip(), "prob": None, "over": "—", "under": "—", "away": "—", "home": "—"})
            ranked.sort(key=lambda x: x["prob"] if x["prob"] else -1, reverse=True)

            with st.expander(f"All candidates for Pick #{pick_num}"):
                rows = ""
                for i, p in enumerate(ranked):
                    if p["prob"] is None:
                        rows += f"<tr><td style='color:#444'>{i+1}</td><td style='color:#666'>{p['name']}</td><td colspan='3' style='color:#444'>not found in FanDuel props</td></tr>"
                    else:
                        pc  = p["prob"] * 100
                        bc  = "#00ff9d" if pc >= 30 else ("#FFE066" if pc >= 20 else "#FF9933")
                        bw  = min(int(p["prob"] * 160), 160)
                        bold = "700" if i == 0 else "400"
                        rows += (
                            "<tr>"
                            f"<td style='color:#444;width:30px'>{i+1}</td>"
                            f"<td style='color:#f0f0f0;font-weight:{bold}'>{p['name']}{' ✓' if i == 0 else ''}</td>"
                            f"<td style='color:#aaa;font-size:0.78rem'>{p['away']} @ {p['home']}</td>"
                            f"<td style='font-weight:700;color:{bc};white-space:nowrap'>{pc:.1f}%"
                            f"<span class='bar-wrap'><span class='bar-fill' style='width:{bw}px;background:{bc}'></span></span></td>"
                            f"<td style='color:#aaa;font-family:monospace'>{p['over']}</td>"
                            "</tr>"
                        )
                st.markdown(
                    "<table><thead><tr><th>#</th><th>PLAYER</th><th>GAME</th><th>PROB</th><th>OVER</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>",
                    unsafe_allow_html=True
                )

    # ── Section 2: Full player table
    st.markdown("---")
    st.markdown("## ALL PLAYERS")
    st.markdown(f"**{len(results)} players** sorted by goal probability")
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
