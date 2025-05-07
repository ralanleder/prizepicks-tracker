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
def find_date_column(columns):
    """Return the name of the first column matching 'date' or common variants, else None."""
    variants = {"date", "day", "pick date", "game date"}
    for col in columns:
        if str(col).strip().lower() in variants:
            return col
    return None

def load_sheet_dataframe(sheet_name, worksheet_name=None):
    """Load a worksheet (or first sheet) into a DataFrame with cleaned headers."""
    ws = client.open(sheet_name).worksheet(worksheet_name) if worksheet_name else client.open(sheet_name).sheet1
    data = ws.get_all_records()
    df = pd.DataFrame(data)
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
    main_date_col = find_date_column(main_df.columns)
    if main_date_col:
        today_main = main_df[main_df[main_date_col] == today_str]
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

# ─── Imports (add these at the top) ─────────────────────────────────────────────
import matplotlib.pyplot as plt
from datetime import timedelta

# ─── 1. Hit-Rate Chart ─────────────────────────────────────────────────────────
# Only consider completed picks
completed = main_df[ main_df["Result"].str.lower().isin(["hit","miss"]) ]
if not completed.empty:
    # compute daily hit rate
    hr = (completed
          .assign(IsHit = completed["Result"].str.lower()=="hit")
          .groupby("Date")["IsHit"]
          .mean()
          .reset_index())
    fig, ax = plt.subplots()
    ax.plot(hr["Date"], hr["IsHit"])       # matplotlib plot, no colors set
    ax.set_xlabel("Date")
    ax.set_ylabel("Hit Rate")
    ax.set_title("Daily Hit Rate")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.subheader("📈 Hit Rate Over Time")
    st.pyplot(fig)
else:
    st.info("No completed picks to chart.")

# ─── 2. Profit-Rolling Suggestions ──────────────────────────────────────────────
st.subheader("💰 Profit Rolling Suggestions")
# Let user set initial bankroll and fraction per pick
initial_bankroll = st.number_input("Initial Bankroll", min_value=1.0, value=1000.0, step=100.0)
bet_fraction    = st.slider("Risk fraction per pick", min_value=0.01, max_value=0.10, value=0.05, step=0.01)

if not completed.empty:
    # assume a 1:1 payout on hit (win = stake, lose = -stake)
    stake = initial_bankroll * bet_fraction
    # map hits→+stake, misses→–stake
    pnl = completed["IsHit"].map({True: +stake, False: -stake})
    total_profit = pnl.sum()
    next_bankroll = initial_bankroll + total_profit

    st.metric("Total Profit", f"${total_profit:,.2f}")
    st.metric("Next-Day Bankroll", f"${next_bankroll:,.2f}")
    st.write(f"> If you risk **${stake:,.2f}** per pick, you'll have **${next_bankroll:,.2f}** tomorrow.")
else:
    st.info("No results yet to compute profit rolling.")

# ─── 3. Next-Day Plays (3–5 Picks) ──────────────────────────────────────────────
st.subheader("🎯 Tomorrow’s Top 3–5 Plays")
# assume daily_df and date_col already exist from your code above
tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
if date_col in daily_df.columns:
    tomorrow_picks = daily_df[ daily_df[date_col] == tomorrow ]
    if not tomorrow_picks.empty:
        st.table(tomorrow_picks.head(5))
    else:
        st.info("No picks entered for tomorrow yet.")
else:
    st.warning("Cannot find your date column to load tomorrow’s picks.")

