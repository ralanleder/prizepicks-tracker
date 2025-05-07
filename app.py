import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os
import streamlit.components.v1 as components

# ─── PrizePicks Client (for Diagnostics) ────────────────────────────────────────
from prizepicks_client import get_account_balance, get_current_board

# ─── 1) Load ENV & Authenticate Google Sheets ──────────────────────────────────
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
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ─── 2) Constants ───────────────────────────────────────────────────────────────
SHEET_NAME = "PrizePicks Sheet"
today_str  = date.today().strftime("%Y-%m-%d")

# ─── 3) Page Layout & Navigation ───────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
page = st.sidebar.radio("Navigate to", ["Dashboard", "Recommendations", "Diagnostics"])

# ─── 4) Helpers ─────────────────────────────────────────────────────────────────
def find_date_column(columns):
    variants = {"date", "day", "pick date", "game date"}
    for c in columns:
        if str(c).strip().lower() in variants:
            return c
    return None

def load_sheet_dataframe(sheet_name, worksheet_name=None):
    ws = client.open(sheet_name).worksheet(worksheet_name) if worksheet_name else client.open(sheet_name).sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def save_picks_to_sheet(picks: pd.DataFrame):
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    # delete old today rows
    date_cells = ws.findall(today_str, in_column=1)
    for cell in sorted(date_cells, key=lambda c: c.row, reverse=True):
        if cell.row > 1:
            ws.delete_rows(cell.row)
    # append new picks
    for _, r in picks.iterrows():
        ws.append_row([today_str, r["Player"], r["Prop"], r["Line"], r.get("Recommendation","")])

def update_status_in_sheet(row_idx: int, status: str):
    ws = client.open(SHEET_NAME).worksheet("Daily Picks")
    ws.update_cell(row_idx + 2, 6, status)  # header + zero-based

# ─── 5) Stub Recommendation Logic ───────────────────────────────────────────────
# Replace these with your real implementations
def fetch_prizepicks_board():
    sample = [
        {"Player":"LeBron James","Prop":"Points","Line":28.5,"Game":"Lakers vs Heat"},
        {"Player":"Stephen Curry","Prop":"3PT Made","Line":4.5,"Game":"Warriors vs Suns"},
        {"Player":"Mookie Betts","Prop":"Total Bases","Line":2.5,"Game":"Dodgers vs Braves"},
    ]
    return pd.DataFrame(sample)

def score_and_select(df_board: pd.DataFrame) -> pd.DataFrame:
    df = df_board.copy()
    df["Recommendation"] = "Over"
    return df

def lookup_final_stat(player: str, prop: str, game: str):
    return None  # DNP

# ─── 6) Page: Dashboard ─────────────────────────────────────────────────────────
if page == "Dashboard":
    st.title("📊 Dashboard")
    # Load and display main history
    main_df = load_sheet_dataframe(SHEET_NAME)
    st.subheader("📚 Full Entry History")
    st.dataframe(main_df, use_container_width=True)

    # Performance summary
    st.subheader("📈 Performance Summary")
    if "Result" in main_df.columns:
        hits   = main_df[main_df["Result"].str.lower()=="hit"]
        misses = main_df[main_df["Result"].str.lower()=="miss"]
        total  = len(hits) + len(misses)
        if total:
            st.metric("✅ Total Logged", total)
            st.metric("🎯 Hit Rate", f"{len(hits)/total*100:.1f}%")
        else:
            st.info("No completed entries.")
    else:
        st.warning("Missing `Result` column.")

    # Today's picks from main sheet
    st.subheader("📌 Today's Picks (Main Sheet)")
    main_date_col = find_date_column(main_df.columns)
    if main_date_col:
        today_main = main_df[main_df[main_date_col]==today_str]
        if not today_main.empty:
            st.table(today_main)
        else:
            st.info("No picks logged for today in main sheet.")
    else:
        st.warning("No date column found.")

# ─── 7) Page: Recommendations ───────────────────────────────────────────────────
elif page == "Recommendations":
    st.title("🎯 Recommendations")

    # Refresh button
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔄 REFRESH NOW"):
            components.html("<script>window.location.reload()</script>")

    # 1) Generate & Save
    st.subheader("🔄 Generate & Save Today's Picks")
    if st.button("Generate & Save Picks Now"):
        board = fetch_prizepicks_board()
        picks = score_and_select(board)
        picks.insert(0, "Date", today_str)
        save_picks_to_sheet(picks)
        st.success(f"{len(picks)} picks generated and saved.")

    # 2) Check Results
    st.subheader("🏁 Check Results for Completed Games")
    if st.button("Check All Results Now"):
        daily_df = load_sheet_dataframe(SHEET_NAME, "Daily Picks")
        date_col = find_date_column(daily_df.columns)
        # ensure Status column
        if "Status" not in daily_df.columns:
            ws = client.open(SHEET_NAME).worksheet("Daily Picks")
            ws.add_cols(1)
            ws.update_cell(1, len(daily_df.columns)+1, "Status")
            daily_df["Status"] = ""
        # update each row
        for idx, row in daily_df.iterrows():
            if row.get("Status") in ("Hit","Miss","DNP"):
                continue
            actual = lookup_final_stat(row["Player"], row["Prop"], row["Game"])
            if actual is None:
                status = "DNP"
            else:
                line = row["Line"]; rec = row["Recommendation"].lower()
                status = ("Hit" if (actual>=line if rec.startswith("over") else actual<=line) else "Miss")
            update_status_in_sheet(idx, status)
        st.success("All results updated.")

    # 3) View Today's Picks
    st.subheader("📅 Today's Picks")
    today_df = load_sheet_dataframe(SHEET_NAME, "Daily Picks")
    date_col = find_date_column(today_df.columns)
    if date_col:
        view = today_df[today_df[date_col]==today_str]
        if not view.empty:
            st.dataframe(view)
        else:
            st.info("No picks for today. Generate above.")
    else:
        st.warning("No date column in Daily Picks.")

# ─── 8) Page: Diagnostics ───────────────────────────────────────────────────────
elif page == "Diagnostics":
    st.title("🛠 Diagnostics")

    st.subheader("🔑 SESSSION TOKEN (truncated)")
    token = os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
    st.write(token[:8]+"…" if token else "None")

    st.subheader("💰 Account Balance")
    try:
        bal = get_account_balance()
        st.metric("Balance", f"${bal:,.2f}")
    except Exception as e:
        st.error(f"Error fetching balance: {e}")

    st.subheader("🔎 Current Board Sample")
    try:
        board = get_current_board()
        st.write(board[:3])
    except Exception as e:
        st.error(f"Error fetching board: {e}")
