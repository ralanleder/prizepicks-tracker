import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# Load environment variables
load_dotenv()

# Build credentials dictionary from .env
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

# Authorize Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Constants
SHEET_NAME = "PrizePicks Sheet"
today_str = date.today().strftime("%Y-%m-%d")

st.title("📊 PrizePicks Tracker Dashboard")

# Helper to normalize and find a 'Date' column
def get_date_column(columns):
    for col in columns:
        if str(col).strip().lower() == "date":
            return col
    for col in columns:
        if str(col).strip().lower() in ["day", "pick date", "game date", "date "]:
            return col
    return None

# --- Load and display main picks tracker ---
try:
    sheet = client.open(SHEET_NAME).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [str(col).strip() for col in df.columns]

    st.subheader("📚 Full Entry History")
    st.dataframe(df)

    st.subheader("📈 Performance Summary")
    if "Result" in df.columns:
        hits = df[df["Result"].str.lower() == "hit"]
        misses = df[df["Result"].str.lower() == "miss"]
        total_logged = len(hits) + len(misses)
        if total_logged > 0:
            hit_rate = len(hits) / total_logged * 100
            st.metric("✅ Total Logged", total_logged)
            st.metric("🎯 Hit Rate", f"{hit_rate:.1f}%")
        else:
            st.info("No completed results yet.")
    else:
        st.warning("Missing 'Result' column in tracker.")

    st.subheader("📌 Today's Picks (Main Sheet)")
    main_date_col = get_date_column(df.columns)
    if main_date_col:
        today_main = df[df[main_date_col] == today_str]
        st.table(today_main if not today_main.empty else "No picks for today.")
    else:
        st.warning("❗ 'Date' column not found in main sheet.")

except Exception as e:
    st.error(f"❌ Error loading main sheet: {e}")

# --- Load and display Daily Picks tab ---
try:
    daily_sheet = client.open(SHEET_NAME).worksheet("Daily Picks")
    daily_data = daily_sheet.get_all_records()
    daily_df = pd.DataFrame(daily_data)
    daily_df.columns = [str(col).strip() for col in daily_df.columns]

    st.subheader("📅 Daily Picks – Full List")
    st.dataframe(daily_df)

    daily_date_col = get_date_column(daily_df.columns)
    if daily_date_col:
        today_daily = daily_df[daily_df[daily_date_col] == today_str]
        st.subheader("✅ Today's Daily Recommendations")
        st.table(today_daily if not today_daily.empty else "No daily picks for today.")
    else:
        st.warning("❗ 'Date' column not found in Daily Picks tab.")

except Exception as e:
    st.error(f"❌ Error loading Daily Picks tab: {e}")
