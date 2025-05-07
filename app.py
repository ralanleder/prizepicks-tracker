import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# ─── Load ENV & Authenticate ────────────────────────────────────────────────────
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

# ─── Helpers ────────────────────────────────────────────────────────────────────
def find_date_column(cols):
    """
    Return the first column name matching 'date' (case-insensitive),
    or common variants ('day','pick date','game date').
    """
    variants = {"date", "day", "pick date", "game date"}
    for c in cols:
        if str(c).strip().lower() in variants:
            return c
    return None

def load_sheet_dataframe(sheet_name, worksheet_name=None):
    """
    Load a gspread worksheet as a DataFrame with cleaned headers.
    If worksheet_name is None, load the first sheet.
    """
    if worksheet_name:
        sheet = client.open(sheet_name).worksheet(worksheet_name)
    else:
        sheet = client.open(sheet_name).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Clean up header names
    df.columns = [str(c).strip() for c in df.columns]
    return df

# ─── Constants ─────────────────────────────────────────────────────────────────
SHEET_NAME = "PrizePicks Sheet"
today_str = date.today().strftime("%Y-%m-%d")

st.title("📊 PrizePicks Tracker Dashboard")

# ─── Main Tracker ───────────────────────────────────────────────────────────────
try:
    main_df = load_sheet_dataframe(SHEET_NAME)
    st.subheader("📚 Full Entry History")
    st.dataframe(main_df, use_container_width=True)

    st.subheader("📈 Performance Summary")
    if "Result" in main_df.columns:
        hits = main_df[main_df["Result"].str.lower() == "hit"]
        misses = main_df[main_df["Result"].str.lower() == "miss"]
        total = len(hits) + len(misses)
        if total:
            st.metric("✅ Total Logged", total)
            st.metric("🎯 Hit Rate", f"{len(hits)/total*100:.1f}%")
        else:
            st.info("No completed entries yet.")
    else:
        st.warning("Missing `Result` column in main tracker.")

    st.subheader("📌 Today's Picks (Main Sheet)")
    date_col = find_date_column(main_df.columns)
    if date_col:
        today_main = main_df[main_df[date_col] == today_str]
        if not today_main.empty:
            st.table(today_main)
        else:
            st.info("No main-sheet picks logged for today.")
    else:
        st.warning("No date-like column found in main tracker.")

except Exception as e:
    st.error(f"Error loading main tracker sheet: {e}")

# ─── Daily Recommendations ────────────────────────────────────────────────────
try:
    daily_df = load_sheet_dataframe(SHEET_NAME, worksheet_name="Daily Picks")
    st.subheader("📅 Daily Picks – Full List")
    st.dataframe(daily_df, use_container_width=True)

    st.subheader("🗓️ Today's Daily Recommendations")
    date_col = find_date_column(daily_df.columns)
    if date_col:
        today_daily = daily_df[daily_df[date_col] == today_str]
        if not today_daily.empty:
            st.table(today_daily)
        else:
            st.info("No daily picks for today.")
    else:
        st.warning("No date-like column found in Daily Picks tab.")

except Exception as e:
    st.error(f"Error loading Daily Picks tab: {e}")
