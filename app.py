import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os
import streamlit.components.v1 as components

# ─── 1) Load ENV & Authenticate ───────────────────────────────────────────────
load_dotenv()
creds_dict = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL")
}
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ─── 2) Constants ──────────────────────────────────────────────────────────────
SHEET_NAME = "PrizePicks Sheet"
today_str  = date.today().strftime("%Y-%m-%d")

# ─── 3) Page Setup & Refresh Button ─────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
st.title("📊 PrizePicks Tracker Dashboard")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🔄 **Refresh Props**")
    if st.button("🔄 REFRESH NOW", key="refresh-main"):
        components.html("<script>window.location.reload()</script>")

# ─── 4) Helpers ─────────────────────────────────────────────────────────────────
def find_date_column(columns):
    variants = {"date", "day", "pick date", "game date"}
    for c in columns:
        if str(c).strip().lower() in variants:
            return c
    return None

def load_sheet_dataframe(sheet_name, worksheet_name=None):
    if worksheet_name:
        ws = client.open(sheet_name).worksheet(worksheet_name)
    else:
        ws = client.open(sheet_name).sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def save_picks_to_sheet(picks: pd.DataFrame):
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    # Delete existing today rows
    date_cells = ws.findall(today_str, in_column=1)
    for cell in sorted(date_cells, key=lambda c: c.row, reverse=True):
        if cell.row > 1:
            try:
                ws.delete_rows(cell.row)
            except Exception:
                pass
    # Append new
    for _, r in picks.iterrows():
        ws.append_row([
            today_str,
            r["Player"],
            r["Prop"],
            r["Line"],
            r.get("Recommendation", "")
        ])

def update_status_in_sheet(row_idx: int, status: str):
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    # Status is in column 6 (F), row index + 2 (1-based + header)
    ws.update_cell(row_idx + 2, 6, status)

# ─── 5) Demo Stubs ───────────────────────────────────────────────────────────────
def fetch_prizepicks_board():
    sample = [
        {"Player":"LeBron James","Prop":"Points","Line":28.5,"Game":"Lakers vs Heat"},
        {"Player":"Stephen Curry","Prop":"3PT Made","Line":4.5,"Game":"Warriors vs Suns"},
        {"Player":"Mookie Betts","Prop":"Total Bases","Line":2.5,"Game":"Dodgers vs Braves"},
        {"Player":"Aaron Judge","Prop":"Home Runs","Line":0.5,"Game":"Yankees vs Red Sox"},
        {"Player":"Giannis Antetokounmpo","Prop":"Rebounds","Line":11.5,"Game":"Bucks vs Nets"},
    ]
    return pd.DataFrame(sample)

def score_and_select(df_board: pd.DataFrame) -> pd.DataFrame:
    df = df_board.copy()
    df["Recommendation"] = "Over"
    return df

def lookup_final_stat(player: str, prop: str, game: str):
    return None

# ─── 6) Generate & Save Picks ────────────────────────────────────────────────────
st.subheader("🔄 Generate & Save Today’s Picks")
if st.button("Generate & Save Picks Now"):
    board = fetch_prizepicks_board()
    picks = score_and_select(board)
    picks.insert(0, "Date", today_str)
    save_picks_to_sheet(picks)
    st.success(f"✅ {len(picks)} picks generated and saved.")

# ─── 7) Check Results ───────────────────────────────────────────────────────────
st.subheader("🏁 Check Results for Completed Games")
if st.button("Check All Results Now"):
    daily_df = load_sheet_dataframe(SHEET_NAME, worksheet_name="Daily Picks")
    date_col = find_date_column(daily_df.columns)

    if "Status" not in daily_df.columns:
        ws = client.open(SHEET_NAME).worksheet("Daily Picks")
        ws.add_cols(1)
        ws.update_cell(1, len(daily_df.columns) + 1, "Status")
        daily_df["Status"] = ""

    for idx, row in daily_df.iterrows():
        if row.get("Status") in ("Hit", "Miss", "DNP"):
            continue
        actual = lookup_final_stat(row["Player"], row["Prop"], row["Game"])
        if actual is None:
            status = "DNP"
        else:
            line = row["Line"]
            rec  = row["Recommendation"].lower()
            if rec.startswith("over"):
                status = "Hit" if actual >= line else "Miss"
            else:
                status = "Hit" if actual <= line else "Miss"
        update_status_in_sheet(idx, status)
    st.success("✅ All results checked and updated.")

# ─── 8) View Today’s Picks ───────────────────────────────────────────────────────
st.subheader("📅 Today’s Picks (Sheet View)")
today_df = load_sheet_dataframe(SHEET_NAME, worksheet_name="Daily Picks")
date_col = find_date_column(today_df.columns)
if date_col:
    view = today_df[today_df[date_col] == today_str]
    st.dataframe(view, use_container_width=True)
else:
    st.warning("❗ No 'Date' column in Daily Picks sheet.")
