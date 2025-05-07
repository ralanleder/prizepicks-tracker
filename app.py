import os
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
from dotenv import load_dotenv
from datetime import date, datetime
import streamlit.components.v1 as components
import random
import itertools
from prizepicks_client import get_account_balance, get_current_board

load_dotenv()
creds = {
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
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, scope))

SHEET_NAME  = "PrizePicks Sheet"
DAILY_TAB   = "Daily Picks"
MULTI_TAB   = "MultiSport Picks"
LOG_TAB     = "Recommendation Log"
BANK_TAB    = "Bankroll"
WATCH_TAB   = "Watchlist"
today_str   = date.today().strftime("%Y-%m-%d")
SPORTS_LIST = ["Soccer","NBA","Baseball","NFL","NHL"]

BET_TEMPLATES = {
    "Points":   "points",
    "Rebounds": "rebounds",
    "Assists":  "assists",
    "Pts+Reb":  "points & rebounds",
    "3PT Made":"three-pointers made",
}

def format_pick(player, prop, line, rec):
    human = BET_TEMPLATES.get(prop, prop.lower())
    return f"{player} — {rec} {line} {human}"

def find_date_column(cols):
    for c in cols:
        if str(c).strip().lower() in ("date","day","pick date","game date"):
            return c
    return None

def ensure_ws(title, headers, rows=1000, cols=20):
    ss = client.open(SHEET_NAME)
    try: ws = ss.worksheet(title)
    except WorksheetNotFound: ws = ss.add_worksheet(title=title, rows=str(rows), cols=str(cols))
    curr = ws.row_values(1)
    if curr != headers:
        try: ws.delete_row(1)
        except: pass
        ws.insert_row(headers,1)
    return ws

def load_df(tab=None):
    ss = client.open(SHEET_NAME)
    ws = ss.worksheet(tab) if tab else ss.sheet1
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [str(c).strip() for c in df.columns]
    return df

def lookup_final_stat(player, prop, game):
    # stub: implement actual retrieval of final stat
    return None

def get_bankroll():
    ws = ensure_ws(BANK_TAB, ["Date","Balance"], rows=100, cols=5)
    df = pd.DataFrame(ws.get_all_records())
    if df.empty:
        ws.append_row([today_str,20.0])
        return 20.0
    return float(df.iloc[-1]["Balance"])

def map_units(prob):
    if prob>=0.8: return 2
    if prob>=0.7: return 1
    if prob>=0.6: return 0.5
    return 0.25

def save_daily(picks):
    ws = ensure_ws(DAILY_TAB,
        ["Date","Sport","Player","Prop","Line","Recommendation","Probability","Units","Stake","Status"]
    )
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c:c.row, reverse=True):
        if cell.row>1: ws.delete_rows(cell.row)
    bal=get_bankroll(); unit_val=bal*0.05
    for _,r in picks.iterrows():
        units=map_units(r["Probability"])
        stk=round(units*unit_val,2)
        ws.append_row([
            today_str,r["Sport"],r["Player"],r["Prop"],r["Line"],r["Recommendation"],r["Probability"],units,stk,""
        ])

def save_multi(cmb):
    ws = ensure_ws(MULTI_TAB,
        ["Date","Type","Legs","Payout","Probability","Units","Stake","Status"]
    )
    for cell in sorted(ws.findall(today_str, in_column=1), key=lambda c:c.row, reverse=True):
        if cell.row>1: ws.delete_rows(cell.row)
    bal=get_bankroll(); unit_val=bal*0.05
    for p in cmb["parlays"]:
        prob=p["probability"]; units=map_units(prob); stk=round(units*unit_val,2)
        ws.append_row([today_str,"Parlay","; ".join(p["legs"]),p["payout"],prob,units,stk,""])
    for m in cmb["moonshots"]:
        prob=m["probability"]; units=map_units(prob); stk=round(units*unit_val,2)
        ws.append_row([today_str,"Moonshot","; ".join(m["legs"]),m["payout"],prob,units,stk,""])

def save_log(rt,cmb):
    ws = ensure_ws(LOG_TAB,
        ["Run Timestamp","Pick Type","Details","Num Legs","Combined Probability","Units"]
    )
    ts=datetime.utcnow().isoformat()
    for kind in ("parlays","moonshots"):
        for c in cmb[kind]:
            units=map_units(c["probability"])
            ws.append_row([ts,kind.title(),"; ".join(c["legs"]),len(c["legs"]),c["probability"],units])

def check_all_results():
    df=load_df(DAILY_TAB)
    ws = client.open(SHEET_NAME).worksheet(DAILY_TAB)
    date_col=find_date_column(df.columns)
    for idx,r in df.iterrows():
        if r[date_col]!=today_str or r.get("Status"): continue
        actual=lookup_final_stat(r["Player"],r["Prop"],"")
        status="DNP" if actual is None else ("Hit" if actual>=r["Line"] else "Miss")
        ws.update_cell(idx+2, df.columns.get_loc("Status")+1, status)

def update_bankroll():
    prev=get_bankroll(); change=0
    for tab in (DAILY_TAB,MULTI_TAB):
        df=load_df(tab); date_col=find_date_column(df.columns)
        today=df[df[date_col]==today_str] if date_col else pd.DataFrame()
        for r in today.itertuples():
            stake=getattr(r,"Stake",0); status=getattr(r,"Status",
                            "")
            change += stake if status=="Hit" else -stake if status=="Miss" else 0
    new=prev+change
    ws=ensure_ws(BANK_TAB,["Date","Balance"]); ws.append_row([today_str,new])

def retrain_model():
    pass

def update_questionable_watchlist():
    ws=ensure_ws(WATCH_TAB,["Date","Player","Prop","Game","Status"])


def run_update_pipeline():
    check_all_results()
    update_bankroll()
    retrain_model()
    update_questionable_watchlist()

# stubs
def fetch_prizepicks_board():
    return pd.DataFrame([
        {"Player":"Lionel Messi","Prop":"Goals","Line":1.5,"Sport":"Soccer"},
        {"Player":"LeBron James","Prop":"Points","Line":28.5,"Sport":"NBA"},
        {"Player":"Mookie Betts","Prop":"Hits","Line":1.5,"Sport":"Baseball"},
        {"Player":"Patrick Mahomes","Prop":"Passing Yds","Line":275.5,"Sport":"NFL"},
        {"Player":"Connor McDavid","Prop":"Assists","Line":1.5,"Sport":"NHL"},
    ])

def score_and_select(df_board):
    df=df_board.copy(); df["Recommendation"]="Over"
    df["Probability"]=[round(random.uniform(0.55,0.85),2)
                         for _ in range(len(df))]
    df["Sport"]=df["Sport"].str.strip().str.title(); return df

def generate_multisport_combos(picks):
    av=picks.groupby("Sport").first().reset_index(); sp=av["Sport"].tolist()
    parl,moon=[],[]
    for combo in itertools.combinations(sp,3):
        prob,legs=1.0,[]
        for s in combo:
            r=picks[picks["Sport"]==s].iloc[0]
            legs.append(format_pick(r["Player"],r["Prop"],r["Line"],r["Recommendation"]))
            prob*=r["Probability"]
        parl.append({"legs":legs,"payout":f"{round(min(15,1/prob),1)}×",
                     "probability":prob})
    for combo in itertools.combinations(sp,4):
        prob,legs=1.0,[]
        for s in combo:
            r=picks[picks["Sport"]==s].iloc[0]
            legs.append(format_pick(r["Player"],r["Prop"],r["Line"],r["Recommendation"]))
            prob*=r["Probability"]
        moon.append({"legs":legs,"payout":f"{round(min(25,1/prob),1)}×",
                     "probability":prob})
    return {"parlays":parl,"moonshots":moon}

st.set_page_config(page_title="PrizePicks Tracker",layout="wide")
page=st.sidebar.radio("Navigate to",
                      ["Dashboard","Recommendations","Multi-Sport",
                       "Bankroll","Diagnostics"])

if page=="Dashboard":
    st.title("📊 Dashboard")
    try:
        df=load_df()
        st.subheader("📚 Full Entry History")
        st.dataframe(df,use_container_width=True)
    except Exception as e:
        st.error(f"Error loading main sheet: {e}")

elif page=="Recommendations":
    st.title("🎯 Single-Sport Picks")
    if st.button("🔄 Generate & Save Single-Sport Picks"):
        picks=score_and_select(fetch_prizepicks_board())
        save_daily(picks); st.success(
            f"{len(picks)} picks saved to '{DAILY_TAB}'"
        )
    try:
        df=load_df(DAILY_TAB); col=find_date_column(df.columns)
        tp=df[df[col]==today_str] if col else pd.DataFrame()
        bal=get_bankroll(); uv=bal*0.05
        for sport in SPORTS_LIST:
            st.markdown(f"**{sport}**")
            sub=tp[tp["Sport"]==sport]
            if sub.empty: st.info(f"No recs for {sport}.")
            else:
                for _,r in sub.iterrows():
                    text=format_pick(
                        r['Player'],r['Prop'],r['Line'],
                        r['Recommendation']
                    )
                    prob=r['Probability']*100
                    units=map_units(r['Probability'])
                    stk=round(units*uv,2)
                    st.markdown(
                        f"- {text} — {prob:.0f}% — {units}u (${stk})"
                    )
    except Exception as e:
        st.error(f"Error loading single-sport picks: {e}")

elif page=="Multi-Sport":
    st.title("🔗 Multi-Sport Parlays & Moonshots")
    if st.button("🔄 Generate & Save Multi-Sport Combos"):
        picks=score_and_select(fetch_prizepicks_board())
        cmb=generate_multisport_combos(picks)
        save_multi(cmb); save_log("Parlay & Moonshot",cmb)
        st.success(
            f"Combos saved to '{MULTI_TAB}' and logged to '{LOG_TAB}'"
        )
    try:
        df=load_df(MULTI_TAB); col=find_date_column(df.columns)
        tm=df[df[col]==today_str] if col else pd.DataFrame()
        bal=get_bankroll(); uv=bal*0.05
        if tm.empty: st.info("No multi-sport combos.")
        else:
            for _,r in tm.iterrows():
                prob=r['Probability']; units=map_units(prob)
                stk=round(units*uv,2)
                st.markdown(
                    f"- [{r['Type']}] {r['Legs']} → {r['Payout']}"
                    f" ({prob*100:.1f}% win) — {units}u (${stk})"
                )
    except Exception as e:
        st.error(f"Error loading multi-sport combos: {e}")

elif page=="Bankroll":
    st.title("💰 Bankroll")
    bal=get_bankroll(); unit=bal*0.05
    st.metric("Current Balance",f"${bal:,.2f}")
    st.metric("1 Unit (5%)",f"${unit:,.2f}")
    st.metric("2 Units (10%)",f"${unit*2:,.2f}")

else:
    st.title("🛠 Diagnostics")
    if st.button("Run Update Pipeline Now"): 
        run_update_pipeline(); st.success("Update pipeline complete.")
    token=os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
    st.write("🔑 Token:",token[:8]+"…" if token else "None")
    try: st.metric("Balance",f"${get_account_balance():,.2f}")
    except Exception as e: st.error(f"Balance error: {e}")
    try: st.write(get_current_board()[:3])
    except Exception as e: st.error(f"Board error: {e}")
