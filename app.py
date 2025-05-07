import os
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
from dotenv import load_dotenv
from datetime import date, datetime
import random
import itertools
from prizepicks_client import get_account_balance, get_current_board

# Load environment
load_dotenv()

# --- Authentication Setup ---
USER_CREDENTIALS = st.secrets.get("credentials", {})
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
st.sidebar.title("🔒 Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
if st.sidebar.button("Login"):
    if username in USER_CREDENTIALS and password == USER_CREDENTIALS[username]:
        st.session_state.logged_in = True
        st.sidebar.success("Logged in successfully!")
    else:
        st.sidebar.error("Invalid credentials")
if not st.session_state.logged_in:
    st.sidebar.info("Please log in to continue.")
    st.stop()

# --- Google Sheets Auth ---
creds = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL"),
}
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, scope))

# --- Constants ---
SHEET_NAME  = "PrizePicks Sheet"
DAILY_TAB   = "Daily Picks"
MULTI_TAB   = "MultiSport Picks"
LOG_TAB     = "Recommendation Log"
BANK_TAB    = "Bankroll"
WATCH_TAB   = "Watchlist"
today_str   = date.today().strftime("%Y-%m-%d")
SPORTS_LIST = ["Soccer", "NBA", "Baseball", "NFL", "NHL"]

# --- Bet Templates ---
BET_TEMPLATES = {
    "Points":      "points",
    "Rebounds":    "rebounds",
    "Assists":     "assists",
    "Pts+Reb":     "points & rebounds",
    "3PT Made":    "three-pointers made",
}

def format_pick(player, prop, line, rec):
    human = BET_TEMPLATES.get(prop, prop.lower())
    return f"{player} — {rec} {line} {human}"

# --- Helpers ---

def find_date_column(cols):
    for c in cols:
        if str(c).strip().lower() in ("date", "day", "pick date", "game date"):
            return c
    return None

def ensure_ws(title, headers, rows=1000, cols=20):
    ss = client.open(SHEET_NAME)
    try:
        ws = ss.worksheet(title)
    except WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=str(rows), cols=str(cols))
    current = ws.row_values(1)
    if current != headers:
        try: ws.delete_row(1)
        except: pass
        ws.insert_row(headers, 1)
    return ws

def load_df(tab=None):
    ss = client.open(SHEET_NAME)
    ws = ss.worksheet(tab) if tab else ss.sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def get_bankroll():
    ws = ensure_ws(BANK_TAB, ["Date", "Balance"], rows=100, cols=5)
    df = pd.DataFrame(ws.get_all_records())
    if df.empty:
        ws.append_row([today_str, 20.0])
        return 20.0
    return float(df.iloc[-1]["Balance"])

def map_units(prob):
    if prob >= 0.8: return 2
    if prob >= 0.7: return 1
    if prob >= 0.6: return 0.5
    return 0.25

# --- Save Routines ---

def save_daily(picks):
    ws = ensure_ws(DAILY_TAB,
        ["Date","Sport","Player","Prop","Line","Recommendation","Probability","Units","Stake","Status"]
    )
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c: c.row, reverse=True):
        if cell.row > 1: ws.delete_rows(cell.row)
    bal = get_bankroll(); unit_val = bal * 0.05
    for _, r in picks.iterrows():
        units = map_units(r["Probability"])
        stake = round(units * unit_val, 2)
        ws.append_row([today_str, r["Sport"], r["Player"], r["Prop"], r["Line"], r["Recommendation"], r["Probability"], units, stake, ""])

def save_multi(combos):
    ws = ensure_ws(MULTI_TAB,
        ["Date","Type","Legs","Payout","Probability","Units","Stake","Status"]
    )
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c: c.row, reverse=True):
        if cell.row > 1: ws.delete_rows(cell.row)
    bal = get_bankroll(); unit_val = bal * 0.05
    for p in combos["parlays"]:
        units = map_units(p["probability"])
        stake = round(units * unit_val, 2)
        ws.append_row([today_str, "Parlay", "; ".join(p["legs"]), p["payout"], p["probability"], units, stake, ""])
    for m in combos["moonshots"]:
        units = map_units(m["probability"])
        stake = round(units * unit_val, 2)
        ws.append_row([today_str, "Moonshot", "; ".join(m["legs"]), m["payout"], m["probability"], units, stake, ""])

def save_log(run_type, combos):
    ws = ensure_ws(LOG_TAB,
        ["Run Timestamp","Pick Type","Details","Num Legs","Combined Probability","Units"]
    )
    ts = datetime.utcnow().isoformat()
    for kind in ("parlays","moonshots"):
        for combo in combos[kind]:
            units = map_units(combo["probability"])
            ws.append_row([ts, kind.title(), "; ".join(combo["legs"]), len(combo["legs"]), combo["probability"], units])

# --- Pipeline ---

def run_update_pipeline():
    from prizepicks_client import lookup_final_stat
    df = load_df(DAILY_TAB)
    ws = client.open(SHEET_NAME).worksheet(DAILY_TAB)
    dc = find_date_column(df.columns)
    for idx, r in df.iterrows():
        if r[dc] != today_str or r.get("Status"):
            continue
        actual = lookup_final_stat(r["Player"], r["Prop"], "")
        status = "DNP" if actual is None else ("Hit" if actual >= r["Line"] else "Miss")
        ws.update_cell(idx+2, df.columns.get_loc("Status")+1, status)
    prev = get_bankroll()
    change = 0
    for tab in (DAILY_TAB, MULTI_TAB):
        d = load_df(tab)
        dc2 = find_date_column(d.columns)
        today_df = d[d[dc2] == today_str] if dc2 else pd.DataFrame()
        for row in today_df.itertuples():
            stake = getattr(row, "Stake", 0)
            stt = getattr(row, "Status", "")
            change += stake if stt == "Hit" else -stake if stt == "Miss" else 0
    new_bal = prev + change
    ensure_ws(BANK_TAB, ["Date", "Balance"]).append_row([today_str, new_bal])
    # Ensure Watchlist sheet exists with correct headers
    ensure_ws(WATCH_TAB, ["Date", "Player", "Prop", "Game", "Status"])

# --- UI follows ---
