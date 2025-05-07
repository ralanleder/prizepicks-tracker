import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os
import streamlit.components.v1 as components

# ─── PrizePicks Client ─────────────────────────────────────────────────────────
from prizepicks_client import SESSION_TOKEN, get_account_balance, get_current_board

# ─── AUTH & SHEET SETUP ─────────────────────────────────────────────────────────
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

SHEET_NAME = "PrizePicks Sheet"
today_str  = date.today().strftime("%Y-%m-%d")

# ─── PAGE NAVIGATION ────────────────────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
page = st.sidebar.radio("Navigate to", ["Dashboard", "Diagnostics"])

# ─── DASHBOARD SCREEN ──────────────────────────────────────────────────────────
if page == "Dashboard":
    st.title("📊 PrizePicks Tracker Dashboard")

    # Refresh button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔄 **Refresh Props**")
        if st.button("🔄 REFRESH NOW", key="refresh-main"):
            components.html("<script>window.location.reload()</script>")

    # ... put all your existing Dashboard code here ...
    # e.g. load main_df, show metrics, daily picks, etc.

    st.subheader("📚 Full Entry History")
    main_df = pd.DataFrame()  # placeholder—replace with your load code
    st.dataframe(main_df)

    # etc.

# ─── DIAGNOSTICS SCREEN ─────────────────────────────────────────────────────────
elif page == "Diagnostics":
    st.title("🛠 PrizePicks Client Diagnostics")

    st.subheader("💰 Account Balance")
    try:
        balance = get_account_balance()
        st.metric("Balance", f"${balance:,.2f}")
    except Exception as e:
        st.error(f"Error fetching balance: {e}")

    st.subheader("🔎 Current Board Sample")
    try:
        board = get_current_board()
        st.write(board[:3])
    except Exception as e:
        st.error(f"Error fetching board: {e}")

st.write("🔑 SESSION TOKEN (truncated):", SESSION_TOKEN[:8] + "…")

