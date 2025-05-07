import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# ─── AUTH ───────────────────────────────────────────────────────────────────────
load_dotenv()
creds_dict = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n","\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL"),
}
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))

SHEET_NAME = "PrizePicks Sheet"
today_str = date.today().strftime("%Y-%m-%d")


# ─── HELPERS ────────────────────────────────────────────────────────────────────
def find_date_column(cols):
    variants = {"date","day","pick date","game date"}
    for c in cols:
        if str(c).strip().lower() in variants:
            return c
    return None

def load_df(tab=None):
    ws = client.open(SHEET_NAME).worksheet(tab) if tab else client.open(SHEET_NAME).sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def save_picks_to_sheet(picks: pd.DataFrame):
    """Remove existing today rows, append new ones"""
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    existing = ws.findall(today_str, in_column=1)
    for cell in sorted(existing, key=lambda c: c.row, reverse=True):
        ws.delete_row(cell.row)
    for _, r in picks.iterrows():
        ws.append_row([
            today_str,
            r["Player"],
            r["Prop"],
            r["Line"],
            r.get("Recommendation",""),
            # leave Status blank for now
        ])

def update_status_in_sheet(row_idx:int, status:str):
    """Write back the Status for the given row index (1-based in sheet)"""
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    # assuming Status is column F (6th column) – adjust if needed
    ws.update_cell(row_idx+1, 6, status)


# ─── STUBS YOU MUST IMPLEMENT ──────────────────────────────────────────────────
def fetch_prizepicks_board():
    """
    Pull today’s PrizePicks board (via API or scraping)  
    Return a DataFrame with columns: Player, Prop, Line, Sport, Game
    """
    raise NotImplementedError

def score_and_select(df_board:pd.DataFrame) -> pd.DataFrame:
    """
    Apply your value model / tier logic to pick top N props.  
    Return a DataFrame with Player, Prop, Line, Recommendation, Sport, Game.
    """
    raise NotImplementedError

def lookup_final_stat(player:str, prop:str, game:str) -> float:
    """
    After games finish: look up the actual stat (e.g. points, K’s).  
    Return the numeric result; if DNP, return None.
    """
    raise NotImplementedError


# ─── UI ────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
st.title("📊 PrizePicks Tracker Dashboard")

# ─── 1) Refresh & Generate Picks ────────────────────────────────────────────────
st.subheader("🔄 Generate & Save Today’s Picks")
if st.button("Generate & Save Picks Now"):
    # 1) Pull the board
    board = fetch_prizepicks_board()
    # 2) Score & pick
    picks = score_and_select(board)
    # 3) Annotate date
    picks.insert(0, "Date", today_str)
    # 4) Save to Google Sheet
    save_picks_to_sheet(picks)
    st.success(f"✅ {len(picks)} picks generated and saved to sheet.")

# ─── 2) Check Results ───────────────────────────────────────────────────────────
st.subheader("🏁 Check Results for Completed Games")
if st.button("Check All Results Now"):
    daily_df = load_df("Daily Picks")
    date_col = find_date_column(daily_df.columns)
    status_col = "Status"
    if status_col not in daily_df.columns:
        # add a Status column header if missing
        ws = client.open(SHEET_NAME).worksheet("Daily Picks")
        ws.add_cols(1)
        ws.update_cell(1, len(daily_df.columns)+1, status_col)

    for idx, row in daily_df.iterrows():
        if row.get("Status") in ("Hit","Miss","DNP"):
            continue  # already checked
        actual = lookup_final_stat(row["Player"], row["Prop"], row["Game"])
        if actual is None:
            status = "DNP"
        else:
            # assume row["Recommendation"] is like "Over" or "Under"
            line = row["Line"]
            if row["Prop"].lower() in row["Recommendation"].lower():
                # simplistic: Over → actual >= line
                hit = actual >= line if row["Recommendation"].startswith("Over") else actual <= line
                status = "Hit" if hit else "Miss"
            else:
                status = "Miss"
        update_status_in_sheet(idx, status)
    st.success("✅ All results checked and updated.")

# ─── 3) View Today’s Picks ───────────────────────────────────────────────────────
st.subheader("📅 Today’s Picks (Sheet View)")
today_df = load_df("Daily Picks")
date_col = find_date_column(today_df.columns)
if date_col:
    view = today_df[today_df[date_col]==today_str]
    st.dataframe(view, use_container_width=True)
else:
    st.warning("❗ No 'Date' column in Daily Picks sheet.")
