import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# Load environment variables from .env
load_dotenv()

# Build credentials dictionary from environment variables
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

# Step 1: Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Step 2: Load data from your Google Sheet
SHEET_NAME = "PrizePicks Sheet"  # Replace with your sheet's name
sheet = client.open(SHEET_NAME).sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Step 3: Streamlit App UI
st.title("📊 PrizePicks Tracker Dashboard")

# Today's Picks
st.subheader("📌 Today's Picks")
today = date.today().strftime("%Y-%m-%d")
today_picks = df[df["Date"] == today]
if not today_picks.empty:
    st.table(today_picks)
else:
    st.info("No picks logged for today.")

# Performance Summary
st.subheader("📈 Performance Summary")
hits = df[df["Result"].str.lower() == "hit"]
misses = df[df["Result"].str.lower() == "miss"]
total_logged = len(df[df["Result"].str.lower().isin(["hit", "miss"])])

if total_logged > 0:
    hit_rate = len(hits) / total_logged * 100
    st.metric("✅ Total Logged", total_logged)
    st.metric("🎯 Hit Rate", f"{hit_rate:.1}%")
else:
    st.warning("No hit/miss data to summarize yet.")

# Full History
st.subheader("📚 Full Entry History")
st.dataframe(df)
