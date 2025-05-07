import os
import requests
from dotenv import load_dotenv
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Load local .env for development ────────────────────────────────────────────
load_dotenv()

# ─── Fetch session token from ENV or Streamlit secrets ──────────────────────────
SESSION_TOKEN = os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
if not SESSION_TOKEN:
    raise RuntimeError(
        "RL_SESSION not set! On Streamlit Cloud go to 'Manage App > Secrets' and add RL_SESSION."
    )

# ─── Build a requests.Session with retries ──────────────────────────────────────
session = requests.Session()
retries = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))

# ─── Common headers to mimic a real browser ─────────────────────────────────────
HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "Cookie":       f"session={SESSION_TOKEN}",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36",
    "Origin":       "https://app.prizepicks.com",
    "Referer":      "https://app.prizepicks.com/",
    "Content-Type": "application/json",
}

GRAPHQL_URL = "https://production.prizepicks.com/graphql"
TIMEOUT = 30  # seconds

def graphql_query(query: str, variables: dict = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    resp = session.post(
        GRAPHQL_URL,
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]

def get_account_balance() -> float:
    query = """
    query {
      me {
        balance {
          total_balance
        }
      }
    }"""
    data = graphql_query(query)
    return data["me"]["balance"]["total_balance"]

def get_user_history(limit: int = 50) -> list[dict]:
    query = """
    query($limit: Int!) {
      me {
        picks(limit: $limit) {
          edges {
            node {
              id
              spread
              stake
              payout
              result
              createdAt
            }
          }
        }
      }
    }"""
    data = graphql_query(query, {"limit": limit})
    return [edge["node"] for edge in data["me"]["picks"]["edges"]]

def get_current_board() -> list[dict]:
    query = """
    query {
      momentGroups {
        id
        name
        props {
          id
          playerName
          statKey
          line
          sport { id name }
          startsAt
        }
      }
    }"""
    data = graphql_query(query)
    props = []
    for mg in data["momentGroups"]:
        for p in mg["props"]:
            props.append({
                "Group":   mg["name"],
                "Player":  p["playerName"],
                "Stat":    p["statKey"],
                "Line":    p["line"],
                "Sport":   p["sport"]["name"],
                "Kickoff": p["startsAt"],
            })
    return props
