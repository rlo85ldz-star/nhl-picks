# 🏒 NHL Goalscorer ML — Tim Hortons Optimizer

Weighted consensus model pulling live odds from Pinnacle, DraftKings, FanDuel and 9 other books to predict NHL goalscorers.

## Deploy to Streamlit Cloud (phone-friendly, free)

### Step 1 — GitHub
1. Go to **github.com** → sign in (or create free account)
2. Click **"+"** → **"New repository"**
3. Name it `nhl-picks`, set to **Public**, click **Create**
4. Click **"uploading an existing file"**
5. Upload all 3 files/folders:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
6. Click **Commit changes**

### Step 2 — Streamlit Cloud
1. Go to **share.streamlit.io** → sign in with GitHub
2. Click **"New app"**
3. Select your `nhl-picks` repo
4. Main file path: `app.py`
5. Click **Deploy**
6. Wait ~2 minutes → you get a public URL like `https://yourname-nhl-picks.streamlit.app`

### Step 3 — Add your API Key (secrets)
In Streamlit Cloud dashboard:
1. Click your app → **Settings** → **Secrets**
2. Paste this (replace with your real key):
```
ODDS_API_KEY = "your_key_here"
```
> Or just paste your key directly in the sidebar when the app loads.

### Step 4 — Get your Odds API key
- Go to **theOddsAPI.com**
- Sign up free → copy your API key
- Free tier: **500 requests/month** (plenty for daily use)

---

## Run Locally (optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## How the Model Works

| Component | Weight | Description |
|---|---|---|
| Weighted Consensus | 60% | All books blended, Pinnacle weighted 1.0x |
| Sharp-Only Signal | 25% | Pinnacle + BetOnline only |
| Historical G/GP | 15% | Season goals-per-game rate |

**Book weights:** Pinnacle (1.0) → BetOnline (0.8) → LowVig (0.85) → DraftKings/FanDuel (0.75) → recreational books (0.55–0.65)

## Grade Scale
- **A+ (≥35%)** — Very strong, single pick
- **A (≥30%)** — Strong pick
- **B+ (≥25%)** — Solid, good for multi-pick days
- **B (≥20%)** — Decent
- **C/D** — Skip for Tim Hortons

## Tim Hortons Strategy
- **Single pick days:** Grade A or A+ only
- **Multi-pick days:** Combine 3–4 players graded B+ or higher
- Props usually post **2–4 hours before puck drop**
