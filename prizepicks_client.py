import os
import requests
from dotenv import load_dotenv
import streamlit as st

# ─── Load local .env for development ────────────────────────────────────────────
load_dotenv()

# ─── Fetch session token from ENV or Streamlit secrets ──────────────────────────
SESSION_TOKEN = os.getenv("RL_SESSION") or st.secrets.get("RL_SESSION")
if not SESSION_TOKEN:
    raise RuntimeError(
        "RL_SESSION not set! "
        "On Streamlit Cloud go to 'Manage App > Secrets' and add RL_SESSION."
    )

HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "Content-Type": "application/json",
}

GRAPHQL_URL = "https://production.prizepicks.com/graphql"

# ─── Core GraphQL helper ────────────────────────────────────────────────────────
def graphql_query(query: str, variables: dict = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]

# ─── PrizePicks API functions ───────────────────────────────────────────────────
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
    edges = data["me"]["picks"]["edges"]
    return [edge["node"] for edge in edges]

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
                "Group": mg["name"],
                "Player": p["playerName"],
                "Stat": p["statKey"],
                "Line": p["line"],
                "Sport": p["sport"]["name"],
                "Kickoff": p["startsAt"],
            })
    return props
