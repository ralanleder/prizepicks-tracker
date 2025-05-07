import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# Load environment variables
load_dotenv()

# Credentials from .env
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

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Set sheet and date
SHEET_NAME = "PrizePicks Sheet"
today_str = date.today().strftime("%Y-%m-%d")

st.title("📊 PrizePicks Tracker Dashboard")

# ----------- Helper: Rename close matches to 'Date' in Daily Picks ------------
def standardize_date_column(sheet):
    raw_headers = sheet.row_values(1)
    cleaned_headers = [str(h).strip() for h in raw_headers]
    
    alt_names = ["Day", "Pick Date", " Game Date", "Date "]

    if "Date" not in [col.title() for col in cleaned_headers]:
        for i, col in enumerate(cleaned_headers):
            if col.strip().title() in alt_names:
                st.warning(f"🛠 Renaming column '{col}' to 'Date'")
                cleaned_headers[i] = "Date"
                break

    # Rewrite headers if modified
    if cleaned_headers != raw_headers:
        sheet.delete_row(1)
        sheet.insert_row(cleaned_headers, 1)
        st.success("✅ Column headers updated.")

# ---------------- Load and display main picks tracker ----------------
try:
    sheet = client.open(SHEET_NAME).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

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
    if "Date" in df.columns:
        today_main = df[df["Date"] == today_str]
        st.table(today_main if not today_main.empty else "No picks for today.")
    else:
        st.warning("❗ 'Date' column not found in main tracker.")

except Exception as e:
    st.error(f"❌ Error loading main sheet: {e}")

# ---------------- Load and display Daily Picks tab ----------------
try:
    daily_sheet = client.open(SHEET_NAME).worksheet("Daily Picks")
    standardize_date_column(daily_sheet)

    daily_data = daily_sheet.get_all_records()
    daily_df = pd.DataFrame(daily_data)

    # Normalize column names
    daily_df.columns = [str(col).strip() for col in daily_df.columns]
    st.subheader("📅 Daily Picks – Full List")
    st.dataframe(daily_df)

    # ✅ Dynamic lookup of 'Date' column
    date_col = next((col for col in daily_df.columns if col.lower() == "date"), None)

    if date_col:
        today_recs = daily_df[daily_df[date_col] == today_str]
        st.subheader("✅ Today's Daily Recommendations")
        st.table(today_recs if not today_recs.empty else "No daily picks for today.")
    else:
        st.warning("❗ 'Date' column not found in Daily Picks tab, even after cleanup.")

except Exception as e:
    st.error(f"❌ Error loading Daily Picks tab: {e}")
