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

# Set sheet name
SHEET_NAME = "PrizePicks Sheet"

# Load main sheet data
sheet = client.open(SHEET_NAME).sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Streamlit App UI
st.title("📊 PrizePicks Tracker Dashboard")

# Today's Picks (from Main Sheet)
st.subheader("📌 Today's Picks")
today_str = date.today().strftime("%Y-%m-%d")
#if "Date" in df.columns:
 #   today_picks_main = df[df["Date"] == today_str]
  #  if not today_picks_main.empty:
   #     st.table(today_picks_main)
    # else:
      #  st.info("No picks logged for today.")
#else:
 #   st.warning("No 'Date' column in main data.")

# Performance Summary
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
        st.warning("No completed results to show.")
else:
    st.warning("Missing 'Result' column for summary.")

# Full Entry History
st.subheader("📚 Full Entry History")
st.dataframe(df)

# Load Daily Picks from 'Daily Picks' tab
try:
    daily_sheet = client.open(SHEET_NAME).worksheet("Daily Picks")
    daily_data = daily_sheet.get_all_records()
    daily_df = pd.DataFrame(daily_data)

    # Normalize columns
    daily_df.columns = [str(col).strip().title() for col in daily_df.columns]

    # Debug: Show column headers
    st.write("📋 Daily Picks Columns:", daily_df.columns.tolist())

    # Full list
    st.subheader("📅 Daily Recommendations (Full List)")
    st.dataframe(daily_df)

    # Filter today's recommendations
    if "Date" in daily_df.columns:
        today_recs = daily_df[daily_df["Date"] == today_str]
        st.subheader("✅ Today's Daily Recommendations")
        if not today_recs.empty:
            st.table(today_recs)
        else:
            st.info("No recommendations for today.")
    else:
        st.warning("❗ 'Date' column not found in Daily Picks tab.")

except Exception as e:
    st.error(f"❌ Could not load Daily Picks sheet: {e}")
