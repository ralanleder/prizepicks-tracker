import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os

# ─── 1) Load ENV & Authenticate ────────────────────────────────────────────────
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

# ─── 2) Constants ───────────────────────────────────────────────────────────────
SHEET_NAME = "PrizePicks Sheet"
today_str = date.today().strftime("%Y-%m-%d")

# ─── 3) Page Setup & Refresh Button ─────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
st.title("📊 PrizePicks Tracker Dashboard")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🔄 **Refresh Props**")
    st.button(
        "🔄 REFRESH NOW",
        key="refresh-main",
        help="Click to reload all data",
        on_click=st.experimental_rerun
    )

# ─── 4) Helper Functions ────────────────────────────────────────────────────────
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

# ─── 5) Main Tracker Section ───────────────────────────────────────────────────
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

# ─── 6) Daily Recommendations Section ──────────────────────────────────────────
try:
    daily_df = load_sheet_dataframe(SHEET_NAME, worksheet_name="Daily Picks")
    st.subheader("📅 Daily Picks – Full List")
    st.dataframe(daily_df, use_container_width=True)

    st.subheader("✅ Today's Daily Recommendations")
    daily_date_col = find_date_column(daily_df.columns)
    if daily_date_col:
        picks = daily_df[daily_df[daily_date_col] == today_str]
        if not picks.empty:
            for idx, row in picks.reset_index(drop=True).iterrows():
                st.markdown(
                    f"**{idx+1}. {row['Player']}**  \n"
                    f"- **Prop:** {row['Prop']}  \n"
                    f"- **Line:** {row['Line']}  \n"
                    f"- **Recommendation:** {row.get('Recommendation','N/A')}"
                )
                st.markdown("---")
        else:
            st.info("No daily picks for today.")
    else:
        st.warning("No date-like column found in Daily Picks tab.")

    # ─── Save Today's Picks Button ───────────────────────────────────────────────
    if 'picks' in locals() and not picks.empty:
        if st.button("💾 Save Today's Picks to Google Sheet"):
            try:
                ws = client.open(SHEET_NAME).worksheet("Daily Picks")
                existing = ws.findall(today_str, in_column=1)
                for cell in sorted(existing, key=lambda c: c.row, reverse=True):
                    ws.delete_row(cell.row)
                for _, r in picks.iterrows():
                    ws.append_row([
                        today_str, r["Player"], r["Prop"],
                        r["Line"], r.get("Recommendation","")
                    ])
                st.success("✅ Today’s picks saved!")
            except Exception as err:
                st.error(f"Failed to save picks: {err}")

except Exception as e:
    st.error(f"Error loading Daily Picks tab: {e}")
