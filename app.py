import os
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import date
import streamlit.components.v1 as components
import random
import itertools
from prizepicks_client import get_account_balance, get_current_board

# ─── 1) Load ENV & Authenticate Google Sheets ──────────────────────────────────
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
client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope))

# ─── 2) Constants ───────────────────────────────────────────────────────────────
SHEET_NAME      = "PrizePicks Sheet"
DAILY_TAB       = "Daily Picks"
MULTI_TAB       = "MultiSport Picks"
today_str       = date.today().strftime("%Y-%m-%d")
SPORTS_LIST     = ["Soccer","NBA","Baseball","NFL","NHL"]

# ─── 3) Helpers ─────────────────────────────────────────────────────────────────
def ensure_headers(ws, expected):
    """Ensure worksheet ws has header row matching expected list."""
    current = ws.row_values(1)
    if current != expected:
        try:
            ws.delete_row(1)
        except:
            pass
        ws.insert_row(expected, 1)

def load_df(tab=None):
    sheet = client.open(SHEET_NAME)
    ws = sheet.worksheet(tab) if tab else sheet.sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def save_daily_picks(picks: pd.DataFrame):
    ws = client.open(SHEET_NAME).worksheet(DAILY_TAB)
    # ensure headers
    ensure_headers(ws, ["Date","Sport","Player","Prop","Line","Recommendation","Probability"])
    # remove existing today
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c:c.row, reverse=True):
        if cell.row>1:
            ws.delete_rows(cell.row)
    # append new
    for _, r in picks.iterrows():
        ws.append_row([
            today_str,
            r["Sport"],
            r["Player"],
            r["Prop"],
            r["Line"],
            r["Recommendation"],
            r["Probability"]
        ])

def save_multisport(combos: dict):
    ws = client.open(SHEET_NAME).worksheet(MULTI_TAB)
    # ensure headers
    ensure_headers(ws, ["Date","Type","Legs","Payout","Probability"])
    # remove existing today
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c:c.row, reverse=True):
        if cell.row>1:
            ws.delete_rows(cell.row)
    # append parlays
    for p in combos["parlays"]:
        ws.append_row([
            today_str,
            "Parlay",
            "; ".join(p["legs"]),
            p["payout"],
            p["probability"]
        ])
    # append moonshots
    for m in combos["moonshots"]:
        ws.append_row([
            today_str,
            "Moonshot",
            "; ".join(m["legs"]),
            m["payout"],
            m["probability"]
        ])

# ─── 4) Recommendation Logic (stubs) ────────────────────────────────────────────
def fetch_prizepicks_board():
    sample = [
        {"Player":"Lionel Messi","Prop":"Goals","Line":1.5,"Sport":"Soccer"},
        {"Player":"LeBron James","Prop":"Points","Line":28.5,"Sport":"NBA"},
        {"Player":"Mookie Betts","Prop":"Hits","Line":1.5,"Sport":"Baseball"},
        {"Player":"Patrick Mahomes","Prop":"Passing Yds","Line":275.5,"Sport":"NFL"},
        {"Player":"Connor McDavid","Prop":"Assists","Line":1.5,"Sport":"NHL"},
    ]
    return pd.DataFrame(sample)

def score_and_select(df_board: pd.DataFrame) -> pd.DataFrame:
    df = df_board.copy()
    df["Recommendation"] = "Over"
    df["Probability"]   = [round(random.uniform(0.55,0.85),2) for _ in range(len(df))]
    df["Sport"]         = df["Sport"].str.strip().str.title()
    return df

def generate_multisport_combos(picks: pd.DataFrame):
    available = picks.groupby("Sport").first().reset_index()
    sports = available["Sport"].tolist()
    parlays, moonshots = [], []
    # 3-leg parlays ≤15×
    for combo in itertools.combinations(sports, 3):
        prob, legs = 1.0, []
        for s in combo:
            r = picks[picks["Sport"]==s].iloc[0]
            legs.append(f"{r['Player']} O{r['Line']}")
            prob *= r["Probability"]
        payout = f"{round(min(15,1/prob),1)}×"
        parlays.append({"legs":legs,"payout":payout,"probability":prob})
    # 4-leg moonshots ≤25×
    for combo in itertools.combinations(sports, 4):
        prob, legs = 1.0, []
        for s in combo:
            r = picks[picks["Sport"]==s].iloc[0]
            legs.append(f"{r['Player']} O{r['Line']}")
            prob *= r["Probability"]
        payout = f"{round(min(25,1/prob),1)}×"
        moonshots.append({"legs":legs,"payout":payout,"probability":prob})
    return {"parlays":parlays,"moonshots":moonshots}

# ─── 5) Page Layout & Navigation ───────────────────────────────────────────────
st.set_page_config(page_title="PrizePicks Tracker",layout="wide")
page = st.sidebar.radio("Navigate to", ["Dashboard","Recommendations","Multi-Sport","Diagnostics"])

# ─── 6) Dashboard ───────────────────────────────────────────────────────────────
if page=="Dashboard":
    st.title("📊 Dashboard")
    try:
        df = load_df()
        st.subheader("📚 Full Entry History")
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading main sheet: {e}")

# ─── 7) Single-Sport Recommendations ─────────────────────────────────────────────
elif page=="Recommendations":
    st.title("🎯 Single-Sport Picks")
    if st.button("🔄 Generate & Save Single-Sport Picks"):
        board = fetch_prizepicks_board()
        picks = score_and_select(board)
        save_daily_picks(picks)
        st.success(f"{len(picks)} picks saved to '{DAILY_TAB}'")

    try:
        picks = load_df(DAILY_TAB)
        col = find_date_column(picks.columns)
        today_picks = picks[picks[col]==today_str] if col else pd.DataFrame()
        for sport in SPORTS_LIST:
            st.markdown(f"**{sport}**")
            df_s = today_picks[today_picks["Sport"]==sport]
            if df_s.empty:
                st.info(f"No recs available for {sport}.")
            else:
                for _,r in df_s.iterrows():
                    st.markdown(
                        f"- {r['Player']} | {r['Prop']} O {r['Line']} "
                        f"— {r['Probability']*100:.0f}%"
                    )
    except Exception as e:
        st.error(f"Error loading single-sport picks: {e}")

# ─── 8) Multi-Sport Parlays & Moonshots ─────────────────────────────────────────
elif page=="Multi-Sport":
    st.title("🔗 Multi-Sport Parlays & Moonshots")
    if st.button("🔄 Generate & Save Multi-Sport Combos"):
        board = fetch_prizepicks_board()
        picks = score_and_select(board)
        combos = generate_multisport_combos(picks)
        save_multisport(combos)
        st.success(f"Combos saved to '{MULTI_TAB}'")

    try:
        dfm = load_df(MULTI_TAB)
        col = find_date_column(dfm.columns)
        today_m = dfm[dfm[col]==today_str] if col else pd.DataFrame()
        if today_m.empty:
            st.info("No multi-sport combos for today.")
        else:
            for _,r in today_m.iterrows():
                st.markdown(
                    f"- [{r['Type']}] {r['Legs']} → {r['Payout']} "
                    f"({r['Probability']*100:.1f}% win)"
                )
    except Exception as e:
        st.error(f"Error loading multi-sport combos: {e}")

# ─── 9) Diagnostics ─────────────────────────────────────────────────────────────
elif page=="Diagnostics":
    st.title("🛠 Diagnostics")
    token = os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
    st.write("🔑 Token:", token[:8]+"…" if token else "None")
    st.subheader("💰 Account Balance")
    try:
        bal = get_account_balance()
        st.metric("Balance",f"${bal:,.2f}")
    except Exception as e:
        st.error(f"Balance error: {e}")
    st.subheader("🔎 Current Board Sample")
    try:
        board = get_current_board()
        st.write(board[:3])
    except Exception as e:
        st.error(f"Board error: {e}")
