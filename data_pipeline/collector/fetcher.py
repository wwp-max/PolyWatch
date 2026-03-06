# data_pipeline/collector/fetcher.py
import json
import ast
import requests
from datetime import datetime, timezone

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL  = "https://clob.polymarket.com"

HEADERS = {
    "User-Agent": "PolyWatch/2.0",
    "Accept": "application/json",
}


def resolve_token_id(slug: str) -> tuple[str, str] | tuple[None, None]:
    """
    Resolve market slug -> (token_id, question).
    Returns (None, None) if not found.
    """
    try:
        resp = requests.get(
            f"{GAMMA_API_URL}/events",
            params={"slug": slug},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data or not data[0].get("markets"):
            return None, None

        market = data[0]["markets"][0]
        question = market["question"]

        clob_ids = market.get("clobTokenIds")
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except json.JSONDecodeError:
                clob_ids = ast.literal_eval(clob_ids)

        if not clob_ids or not isinstance(clob_ids, list):
            return None, None

        return clob_ids[0], question

    except Exception as e:
        print(f"[fetcher] resolve_token_id error for {slug}: {e}")
        return None, None


def fetch_price_history(token_id: str, start_ts: int, end_ts: int) -> list[dict]:
    """
    Fetch price history for token_id between start_ts and end_ts (Unix timestamps).
    Returns list of {"time": datetime, "price": float} dicts.
    Returns [] on error or empty data.
    """
    try:
        resp = requests.get(
            f"{CLOB_API_URL}/prices-history",
            params={
                "market":   token_id,
                "startTs":  start_ts,
                "endTs":    end_ts,
                "fidelity": 60,
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        history = data.get("history", [])
        return [
            {
                "time":  datetime.fromtimestamp(point["t"], tz=timezone.utc),
                "price": float(point["p"]),
            }
            for point in history
        ]

    except Exception as e:
        print(f"[fetcher] fetch_price_history error for {token_id}: {e}")
        return []
