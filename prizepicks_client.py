import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env or secrets.toml
load_dotenv()

# Use RL_SESSION instead of PRIZEPICKS_SESSION
SESSION_TOKEN = os.getenv("RL_SESSION")
if not SESSION_TOKEN:
    raise ValueError("RL_SESSION environment variable not set")

HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "Content-Type": "application/json",
}

GRAPHQL_URL = "https://production.prizepicks.com/graphql"

def graphql_query(query: str, variables: dict = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    response = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()["data"]

def get_account_balance() -> float:
    query = """
    query {
      me {
        id
        balance {
          total_balance
        }
      }
    }"""
    data = graphql_query(query)
    return data["me"]["balance"]["total_balance"]

def get_user_history(limit: int = 50) -> list[dict]:
    query = """
    query($limit:Int!) {
      me {
        picks(limit:$limit) {
          edges {
            node {
              id
              spread
              stake
              payout
              result     # WIN, LOSS, CANCELLED
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
