import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import os
import streamlit.components.v1 as components

# ─── PrizePicks Client (Diagnostics) ───────────────────────────────────────────
from prizepicks_client import get_account_balance, get_current_board

# ─── 1) Load ENV & Authenticate Google Sheets ─────────────────────────────────
load_dotenv()
creds_dict = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n","\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_CERT_URL"),
}
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ─── 2) Constants ──────────────────────────────────────────────────────────────
SHEET_NAME = "PrizePicks Sheet"
today_str  = date.today().strftime("%Y-%m-%d")

# ─── 3) Page Layout & Nav ──────────────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker", layout="wide")
page = st.sidebar.radio("Navigate to", ["Dashboard", "Recommendations", "Diagnostics"])

# ─── 4) Helpers ─────────────────────────────────────────────────────────────────
def fetch_prizepicks_board():
    """DEMO STUB: replace with real board-fetching logic."""
    sample = [
        {"Player":"Lionel Messi",           "Prop":"Goals",          "Line":1.5,  "Sport":"Soccer"},
        {"Player":"LeBron James",           "Prop":"Points",         "Line":28.5, "Sport":"NBA"},
        {"Player":"Mookie Betts",           "Prop":"Hits",           "Line":1.5,  "Sport":"Baseball"},
        {"Player":"Tom Brady",              "Prop":"Passing Yards",  "Line":250.5,"Sport":"NFL"},
        {"Player":"Connor McDavid",         "Prop":"Assists",        "Line":1.5,  "Sport":"NHL"},
    ]
    return pd.DataFrame(sample)

def score_and_select(df_board: pd.DataFrame) -> pd.DataFrame:
    """DEMO STUB: tag all as 'Over' and assign random win prob."""
    import random
    df = df_board.copy()
    df["Recommendation"] = "Over"
    df["Probability"]   = [round(random.uniform(0.55, 0.85), 2) for _ in range(len(df))]
    return df

def generate_parlay_recs(picks: pd.DataFrame):
    """DEMO STUB: returns sample parlays & moonshots."""
    # example combo structures
    return {
        "parlays": [
            {"legs":[f"{picks.iloc[0]['Player']} {picks.iloc[0]['Prop']} Over"], 
             "payout":"6×", "probability":0.60},
            {"legs":[f"{picks.iloc[1]['Player']} {picks.iloc[1]['Prop']} Over",
                     f"{picks.iloc[2]['Player']} {picks.iloc[2]['Prop']} Over"], 
             "payout":"12×", "probability":0.45},
        ],
        "moonshots": [
            {"legs":[
                f"{picks.iloc[0]['Player']} O",
                f"{picks.iloc[1]['Player']} O",
                f"{picks.iloc[2]['Player']} O"
              ],
             "payout":"20×", "probability":0.30},
        ]
    }

# ─── 5) Dashboard Screen ─────────────────────────────────────────────────────────
if page == "Dashboard":
    st.title("📊 Dashboard")
    # Load your historical tracker
    try:
        df = pd.DataFrame(client.open(SHEET_NAME).sheet1.get_all_records())
        st.subheader("📚 Full Entry History")
        st.dataframe(df, use_container_width=True)
        # (Your existing summary/stats here…)
    except Exception as e:
        st.error(f"Error loading main sheet: {e}")

# ─── 6) Recommendations Screen ───────────────────────────────────────────────────
elif page == "Recommendations":
    st.title("🎯 Recommendations")

    # Refresh button
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔄 REFRESH PROPS"):
            components.html("<script>window.location.reload()</script>")

    # Generate single-leg recs
    st.subheader("🚀 Single-Leg Picks by Sport")
    board = fetch_prizepicks_board()
    picks = score_and_select(board)

    for sport in ["Soccer","NBA","Baseball","NFL","NHL"]:
        st.markdown(f"**{sport}**")
        df_s = picks[picks["Sport"]==sport]
        if df_s.empty:
            st.info(f"No recs available for {sport}.")
        else:
            for i, row in df_s.iterrows():
                st.markdown(
                    f"- {row['Player']} | {row['Prop']} Over {row['Line']} "
                    f"— {row['Probability']*100:.0f}% chance"
                )

    # Multi-leg parlays & moonshots
    st.subheader("🎲 Parlays & Moonshots")
    if st.button("Generate Parlays & Moonshots"):
        combos = generate_parlay_recs(picks)
        st.markdown("**Parlays (up to 15×)**")
        for combo in combos["parlays"]:
            legs = "; ".join(combo["legs"])
            st.markdown(f"- {legs} → {combo['payout']} ({combo['probability']*100:.0f}% combo win rate)")

        st.markdown("**Moonshots (up to 25×)**")
        for combo in combos["moonshots"]:
            legs = "; ".join(combo["legs"])
            st.markdown(f"- {legs} → {combo['payout']} ({combo['probability']*100:.0f}% combo win rate)")

# ─── 7) Diagnostics Screen ───────────────────────────────────────────────────────
elif page == "Diagnostics":
    st.title("🛠 Diagnostics")

    st.subheader("🔑 SESSION TOKEN (truncated)")
    token = os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
    st.write(token[:8] + "…" if token else "None")

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
