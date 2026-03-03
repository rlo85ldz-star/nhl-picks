import streamlit as st
import requests
from datetime import datetime, timezone
import pytz

# ─── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    page_title="NHL Goalscorer Picks",
    page_icon="🏒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CUSTOM CSS ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Bebas+Neue&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace;
    background-color: #0a0c10;
    color: #e0e0e0;
  }
  .main { background-color: #0a0c10; }
  .block-container { padding-top: 1.5rem; max-width: 900px; }

  .title-block {
    background: linear-gradient(135deg, #0d1117 0%, #0a0c10 100%);
    border: 1px solid rgba(0,255,157,0.2);
    border-radius: 12px;
    padding: 20px 24px 14px;
    margin-bottom: 20px;
  }
  .title-text {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.4rem;
    letter-spacing: 4px;
    color: #00ff9d;
    text-shadow: 0 0 30px rgba(0,255,157,0.3);
    margin: 0;
  }
  .subtitle-text {
    font-size: 0.75rem;
    color: #555;
    letter-spacing: 2px;
    margin-top: 2px;
  }

  .top-picks-bar {
    background: linear-gradient(135deg, rgba(0,255,157,0.08), rgba(126,255,245,0.04));
    border: 1px solid rgba(0,255,157,0.2);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 16px;
  }
  .top-picks-label {
    font-size: 0.7rem;
    color: #00ff9d;
    letter-spacing: 2px;
    margin-bottom: 10px;
  }

  .player-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
  }
  .player-card:hover { border-color: rgba(0,255,157,0.3); }

  .grade-aplus { color: #00ff9d; font-weight: 700; }
  .grade-a     { color: #00ff9d; font-weight: 700; }
  .grade-bplus { color: #FFE066; font-weight: 700; }
  .grade-b     { color: #FFE066; font-weight: 700; }
  .grade-c     { color: #FF9933; font-weight: 700; }
  .grade-d     { color: #FF6666; font-weight: 700; }

  .pct-high  { color: #00ff9d; font-weight: 700; font-size: 1.1rem; }
  .pct-mid   { color: #FFE066; font-weight: 700; font-size: 1.1rem; }
  .pct-low   { color: #FF9933; font-weight: 700; font-size: 1.1rem; }

  div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 10px 14px;
  }
  div[data-testid="metric-container"] label { color: #555 !important; font-size: 0.7rem !important; }
  div[data-testid="metric-container"] div   { color: #e0e0e0 !important; }

  .stButton>button {
    background: #00ff9d;
    color: #000;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 1px;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    width: 100%;
  }
  .stButton>button:hover { background: #00cc7a; color: #000; }

  .stSelectbox label, .stSlider label { color: #555 !important; font-size: 0.75rem !important; }

  .book-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    margin: 2px;
    font-family: monospace;
  }
  .book-sharp  { background: rgba(0,255,157,0.12); border: 1px solid rgba(0,255,157,0.3); color: #00ff9d; }
  .book-normal { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #888; }

  .warning-box {
    background: rgba(255,209,0,0.08);
    border: 1px solid rgba(255,209,0,0.25);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.8rem;
    color: #FFE066;
    margin-bottom: 12px;
  }
  .error-box {
    background: rgba(255,80,80,0.08);
    border: 1px solid rgba(255,80,80,0.25);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.8rem;
    color: #ff6b6b;
    margin-bottom: 12px;
  }
  hr { border-color: rgba(255,255,255,0.07); }
  footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ───────────────────────────────────────────────
BOOK_WEIGHTS = {
    "pinnacle":        1.00,
    "betonlineag":     0.80,
    "lowvig":          0.85,
    "draftkings":      0.75,
    "fanduel":         0.75,
    "betmgm":          0.65,
    "caesars":         0.65,
    "pointsbetus":     0.60,
    "betrivers":       0.60,
    "williamhill_us":  0.60,
    "mybookieag":      0.55,
    "unibet_us":       0.60,
}

SHARP_BOOKS = {"pinnacle", "betonlineag", "lowvig"}

PLAYER_STATS = {
    "Auston Matthews":   0.58,
    "Leon Draisaitl":    0.52,
    "David Pastrnak":    0.50,
    "Nathan MacKinnon":  0.48,
    "Connor McDavid":    0.45,
    "Tage Thompson":     0.45,
    "Nikita Kucherov":   0.42,
    "Brayden Point":     0.41,
    "Kirill Kaprizov":   0.40,
    "Sam Reinhart":      0.39,
    "Jason Robertson":   0.38,
    "Matthew Tkachuk":   0.37,
    "William Nylander":  0.36,
    "Brady Tkachuk":     0.30,
    "Nico Hischier":     0.28,
    "Sebastian Aho":     0.32,
    "Elias Pettersson":  0.33,
    "Jack Hughes":       0.34,
    "Cole Caufield":     0.35,
    "Tim Stutzle":       0.31,
}

# ─── MATH ────────────────────────────────────────────────────
def american_to_decimal(a):
    return (a / 100) + 1 if a > 0 else (100 / abs(a)) + 1

def american_to_implied(a):
    return 1 / american_to_decimal(a)

def remove_vig(yes_p, no_p):
    total = yes_p + no_p
    return yes_p / total

def compute_consensus(book_odds):
    w_sum, w_total = 0.0, 0.0
    for b in book_odds:
        w = BOOK_WEIGHTS.get(b["book"], 0.5)
        raw_yes = american_to_implied(b["yes_odds"])
        raw_no  = american_to_implied(b["no_odds"]) if b.get("no_odds") else (1 - raw_yes) * 1.05
        clean_yes = remove_vig(raw_yes, raw_no)
        w_sum   += clean_yes * w
        w_total += w
    return w_sum / w_total if w_total > 0 else 0.0

def compute_sharp(book_odds):
    sharp = [b for b in book_odds if b["book"] in SHARP_BOOKS]
    return compute_consensus(sharp) if sharp else None

def ml_score(consensus, sharp, name):
    gpg   = PLAYER_STATS.get(name)
    stats = min(gpg / 0.5, 1.4) * 0.15 if gpg else 0.10
    sw    = 0.25 if sharp is not None else 0.0
    cw    = 1.0 - sw - 0.15
    score = consensus * cw + (sharp or consensus) * sw + stats
    return min(score, 0.95)

def grade(p):
    if p >= 0.35: return "A+"
    if p >= 0.30: return "A"
    if p >= 0.25: return "B+"
    if p >= 0.20: return "B"
    if p >= 0.15: return "C"
    return "D"

def grade_color(p):
    if p >= 0.30: return "#00ff9d"
    if p >= 0.20: return "#FFE066"
    if p >= 0.15: return "#FF9933"
    return "#FF6666"

def fmt_american(a):
    return f"+{a}" if a > 0 else str(a)

# ─── API ─────────────────────────────────────────────────────
def fetch_picks(api_key: str, target_date: str):
    """target_date: YYYY-MM-DD in EST."""
    import datetime as dt
    import requests
    
    # 1. SETUP TIMEZONE BOUNDARIES
    tz_est = pytz.timezone("America/Toronto")
    try:
        est_start = tz_est.localize(dt.datetime.strptime(target_date, "%Y-%m-%d"))
        est_end = est_start + dt.timedelta(hours=23, minutes=59, seconds=59)
        utc_start = est_start.astimezone(pytz.utc)
        utc_end = est_end.astimezone(pytz.utc)
    except Exception as e:
        return [], target_date, 0

    # 2. FETCH EVENTS
    events_url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events?apiKey={api_key}"
    r = requests.get(events_url, timeout=60)
    r.raise_for_status()
    events = r.json()

    st.session_state["raw_events_json"] = events

    # --- DEBUG SECTION: POPULATE THE BOXES ---
    # This captures EVERY date the API is offering before we filter them
    all_api_dates = sorted(set(e["commence_time"][:10] for e in events)) if events else []
    st.session_state["debug_dates"] = all_api_dates 
    st.session_state["debug_today"] = target_date
    st.session_state["debug_total_events_raw"] = len(events)
    # -----------------------------------------

    # Quota tracking
    try:
        st.session_state["quota_used"] = int(r.headers.get("x-requests-used", 0))
        st.session_state["quota_remaining"] = int(r.headers.get("x-requests-remaining", 500))
    except: pass

    # 3. FILTER EVENTS FOR THE EST DAY
    today_events = []
    for e in events:
        event_time_utc = dt.datetime.strptime(e["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        if utc_start <= event_time_utc <= utc_end:
            today_events.append(e)

    st.session_state["debug_total_events"] = len(today_events)

    if not today_events:
        return [], target_date, 1

    # 4. FETCH ODDS
    books = ",".join(BOOK_WEIGHTS.keys())
    all_players = {}
    requests_used = 1

    for event in today_events:
        url = (
            f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event['id']}/odds"
            f"?apiKey={api_key}&regions=us,eu&markets=player_goal_scorer"
            f"&oddsFormat=american&bookmakers={books}"
        )
        resp = requests.get(url, timeout=15)
        requests_used += 1
        if resp.status_code != 200: continue
        
        data = resp.json()
        game_label = f"{event['away_team']} @ {event['home_team']}"

        for bm in data.get("bookmakers", []):
            book = bm["key"]
            for mkt in bm.get("markets", []):
                if mkt["key"] != "player_goal_scorer": continue
                for outcome in mkt.get("outcomes", []):
                    name = outcome["name"]
                    price = outcome["price"]
                    desc = (outcome.get("description") or "yes").lower()
                    is_yes = desc in ("yes", "over", "scorer", "to score")

                    if name not in all_players:
                        all_players[name] = {"name": name, "game": game_label, "book_odds": {}}
                    if book not in all_players[name]["book_odds"]:
                        all_players[name]["book_odds"][book] = {}
                    
                    if is_yes:
                        all_players[name]["book_odds"][book]["yes_odds"] = price
                    else:
                        all_players[name]["book_odds"][book]["no_odds"] = price

    # 5. PROCESS RESULTS
    results = []
    for p in all_players.values():
        book_list = [
            {"book": bk, "yes_odds": v["yes_odds"], "no_odds": v.get("no_odds")}
            for bk, v in p["book_odds"].items() if "yes_odds" in v
        ]
        if not book_list: continue

        cons = compute_consensus(book_list)
        sharp = compute_sharp(book_list)
        score = ml_score(cons, sharp, p["name"])
        best = max(book_list, key=lambda b: american_to_decimal(b["yes_odds"]))
        
        results.append({
            "name": p["name"], "game": p["game"], "score": score,
            "consensus": cons, "sharp": sharp, "grade": grade(score),
            "gpg": PLAYER_STATS.get(p["name"]), "books": len(book_list),
            "book_list": book_list, "best_odds": fmt_american(best["yes_odds"]),
            "best_book": best["book"], "value": score - cons,
        })

    st.session_state["raw_odds_json"] = raw_odds_data
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results, target_date, requests_used

# ─── UI ──────────────────────────────────────────────────────
st.markdown("""
<div class="title-block">
  <div class="title-text">NHL GOALSCORER ML</div>
  <div class="subtitle-text">TIM HORTONS GAME OPTIMIZER · WEIGHTED CONSENSUS MODEL</div>
</div>
""", unsafe_allow_html=True)

# Sidebar / API key
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input(
        "Odds API Key",
        type="password",
        placeholder="Paste key from the-odds-api.com",
        help="Free at the-odds-api.com — 500 requests/month",
    )
    st.markdown("---")

    # ── API Quota tracker
    quota_used      = st.session_state.get("quota_used", None)
    quota_remaining = st.session_state.get("quota_remaining", None)
    if quota_used is not None:
        used      = quota_used
        remaining = quota_remaining
        total     = 500
        pct_used  = used / total
        bar_color = "#00ff9d" if pct_used < 0.6 else ("#FFE066" if pct_used < 0.85 else "#FF6666")
        bar_filled = int(pct_used * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        st.markdown("**📊 API Quota (this month)**")
        st.markdown(
            f"<div style='font-family:monospace;font-size:0.75rem;color:{bar_color}'>{bar}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.8rem'>"
            f"<span style='color:{bar_color};font-weight:700'>{used}</span>"
            f"<span style='color:#555'> / {total} used &nbsp;·&nbsp; </span>"
            f"<span style='color:#00ff9d;font-weight:700'>{remaining} left</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if remaining <= 50:
            st.warning(f"⚠️ Only {remaining} requests left this month!")
        elif remaining <= 100:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#FFE066'>⚡ {remaining} requests remaining</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown("**📊 API Quota**")
        st.caption("Fetch once to see quota")

    st.markdown("---")
    st.markdown("**How the model works**")
    st.markdown("""
- **60%** Weighted consensus  
  *(Pinnacle 1.0x, DK/FD 0.75x)*
- **25%** Sharp-book only signal  
  *(Pinnacle + BetOnline)*
- **15%** Historical G/GP rate

**Grades**  
🟢 A+/A = ≥30% — Strong pick  
🟡 B+/B = 20–30% — Solid  
🟠 C = 15–20% — Marginal  
🔴 D = <15% — Skip
""")
    st.markdown("---")
    st.markdown("**Tim Hortons Strategy**")
    st.markdown("Single pick → A or A+ only  \nMulti-pick → mix 3–4 B+ or higher")
    st.markdown("---")
    st.caption("Not gambling advice. Use responsibly.")

# ── Date options
import datetime as _dt
_et   = pytz.timezone("America/Toronto")
_now  = datetime.now(_et)
_d0   = _now.strftime("%Y-%m-%d")
_d1   = (_now + _dt.timedelta(days=1)).strftime("%Y-%m-%d")
_d2   = (_now + _dt.timedelta(days=2)).strftime("%Y-%m-%d")

_date_labels = {
    f"Today ({_d0})": _d0,
    f"{_d1}": _d1,
    f"{_d2}": _d2,
}

# Controls row
col0, col1, col2, col3 = st.columns([2, 2, 2, 1])
with col0:
    selected_date_label = st.selectbox(
        "Game Date",
        list(_date_labels.keys()),
        index=0,
    )
    selected_date = _date_labels[selected_date_label]
with col1:
    min_grade = st.selectbox(
        "Minimum Grade",
        ["All", "B (≥20%)", "B+ (≥25%)", "A (≥30%)", "A+ (≥35%)"],
        index=0,
    )
with col2:
    sort_by = st.selectbox(
        "Sort By",
        ["ML Score", "Consensus Probability", "Value Edge"],
        index=0,
    )
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("🏒 FETCH", use_container_width=True)

# Grade threshold map
grade_thresh = {
    "All": 0.0,
    "B (≥20%)": 0.20,
    "B+ (≥25%)": 0.25,
    "A (≥30%)": 0.30,
    "A+ (≥35%)": 0.35,
}
thresh = grade_thresh[min_grade]

sort_key = {"ML Score": "score", "Consensus Probability": "consensus", "Value Edge": "value"}[sort_by]

# ── Main content
if not api_key:
    st.markdown("""
<div class="warning-box">
  👆 Add your <strong>Odds API key</strong> in the sidebar to fetch live odds.<br>
  Get a free key at <strong>the-odds-api.com</strong> (500 requests/month — enough for daily use).
</div>
""", unsafe_allow_html=True)

    st.markdown("#### What this app does")
    c1, c2, c3 = st.columns(3)
    c1.metric("Books Tracked", "12+", "Pinnacle, DK, FD & more")
    c2.metric("Model Type", "Weighted Consensus", "Vig-removed blend")
    c3.metric("Refresh Rate", "30 min cache", "Auto-updates")

elif fetch_btn or "results" in st.session_state:
    if fetch_btn:
        for _k in ["results","today_str","reqs"]:
            st.session_state.pop(_k, None)
        with st.spinner("Fetching odds from Pinnacle, DraftKings, FanDuel... (30–60 sec)"):
            try:
                results, today_str, reqs = fetch_picks(api_key, selected_date)
                st.session_state["results"]   = results
                st.session_state["today_str"] = today_str
                st.session_state["reqs"]      = reqs
            except requests.HTTPError as e:
                st.markdown(f'<div class="error-box">API Error: {e}<br>Check your API key is correct.</div>', unsafe_allow_html=True)
                st.stop()
            except Exception as e:
                st.markdown(f'<div class="error-box">Error: {e}</div>', unsafe_allow_html=True)
                st.stop()

    results   = st.session_state.get("results", [])
    today_str = st.session_state.get("today_str", "")
    reqs      = st.session_state.get("reqs", 0)

    if not results:
        debug_dates = st.session_state.get("debug_dates", [])
        debug_today = st.session_state.get("debug_today", "")
        debug_total = st.session_state.get("debug_total_events", 0)
        st.markdown('<div class="warning-box">⚠️ No NHL games found for today. Props usually post 2-4 hours before puck drop.</div>', unsafe_allow_html=True)
        with st.expander("🔍 Debug info — click to diagnose"):
            st.write(f"**App thinks today is:** `{debug_today}` (Eastern Time)")
            st.write(f"**Total events returned by API:** {debug_total}")
            st.write(f"**Game dates in API response:** {debug_dates}")
            st.info("If your date is missing above, share this info so we can fix it.")
        st.stop()

    # Filter + sort
    filtered = [p for p in results if p["score"] >= thresh]
    filtered.sort(key=lambda x: x[sort_key], reverse=True)

    # ── Top picks banner
    top3 = filtered[:3]
    picks_html = "  |  ".join([
        f"<strong style='color:#f0f0f0'>#{i+1} {p['name']}</strong> "
        f"<span style='color:{grade_color(p['score'])}'>{p['score']*100:.1f}% · {p['grade']}</span>"
        for i, p in enumerate(top3)
    ])
    st.markdown(f"""
<div class="top-picks-bar">
  <div class="top-picks-label">⚡ TODAY'S TIM HORTONS PICKS — {today_str}</div>
  <div style="font-size:0.9rem">{picks_html}</div>
</div>
""", unsafe_allow_html=True)

    # ── Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Players Found", len(results))
    m2.metric("After Filter", len(filtered))
    m3.metric("Top Pick", top3[0]["name"].split()[-1] if top3 else "—")
    m4.metric("Top Score", f"{top3[0]['score']*100:.1f}%" if top3 else "—")

    st.markdown("---")

    # ── Player cards
    for i, p in enumerate(filtered):
        col = grade_color(p["score"])
        pct_class = "pct-high" if p["score"] >= 0.30 else ("pct-mid" if p["score"] >= 0.20 else "pct-low")
        sharp_str = f"{p['sharp']*100:.1f}%" if p["sharp"] else "N/A"
        gpg_str   = f"{p['gpg']:.2f}" if p["gpg"] else "—"
        val_str   = f"+{p['value']*100:.1f}%" if p["value"] > 0.02 else (f"{p['value']*100:.1f}%" if p["value"] < -0.02 else "~fair")

        with st.expander(
            f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'#{i+1}'}  "
            f"{p['name']}  ·  {p['score']*100:.1f}%  ·  Grade {p['grade']}  ·  {p['game']}",
            expanded=(i < 3),
        ):
            r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
            r1c1.metric("ML Score",   f"{p['score']*100:.1f}%")
            r1c2.metric("Consensus",  f"{p['consensus']*100:.1f}%")
            r1c3.metric("Sharp",      sharp_str)
            r1c4.metric("G/GP",       gpg_str)
            r1c5.metric("Value Edge", val_str)

            st.markdown("**Book Lines**")
            badges = ""
            for b in sorted(p["book_list"], key=lambda x: -(BOOK_WEIGHTS.get(x["book"], 0.5))):
                cls   = "book-sharp" if b["book"] in SHARP_BOOKS else "book-normal"
                label = b["book"].replace("_us","").replace("williamhill","wh")
                odds  = fmt_american(b["yes_odds"])
                badges += f'<span class="book-badge {cls}">{label}: {odds}</span>'
            st.markdown(badges, unsafe_allow_html=True)

            bc1, bc2 = st.columns(2)
            bc1.markdown(f"**Best Available:** `{p['best_odds']}` @ {p['best_book']}")
            bc2.markdown(f"**Books Covering:** {p['books']} sportsbooks")

    st.markdown("---")
    st.caption(f"Data cached 30 min · API requests used this session: {reqs} · Not gambling advice")


# ─── INVESTIGATION PANEL ─────────────────────────────────────
st.markdown("---")
with st.expander("🛠️ API INVESTIGATION & RAW DATA"):
    st.write("Use this section to see exactly what the API sent back.")
    
    if "raw_events_json" not in st.session_state:
        st.info("No data fetched yet. Click 'FETCH' to see raw API responses.")
    else:
        tab1, tab2 = st.tabs(["📅 Raw Events (Schedule)", "🏒 Raw Odds (Player Props)"])
        
        with tab1:
            st.markdown("**All events returned for the NHL:**")
            st.json(st.session_state["raw_events_json"])
            
        with tab2:
            st.markdown("**Player prop data for filtered games:**")
            if not st.session_state.get("raw_odds_json"):
                st.warning("No player props found. This usually means the books haven't posted them yet.")
            else:
                st.json(st.session_state["raw_odds_json"])
