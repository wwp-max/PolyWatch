import requests
import json
import time
import ast
from datetime import datetime

# Simulate Browser Header
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json'
}


def print_separator(title):
    print(f"\n{'=' * 10} {title} {'=' * 10}")


def safe_parse_list(data_field):
    if isinstance(data_field, list):
        return data_field
    if isinstance(data_field, str):
        try:
            return ast.literal_eval(data_field)
        except:
            return []
    return []


# ==========================================
# 1. Gamma API (Filter High Liquidity Markets)
# ==========================================
def run_gamma_demo():
    print_separator("1. Gamma API (Find High Liquidity Markets)")

    # Get top 20 active markets
    url = "https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false"

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        events = response.json()

        all_markets = []
        for event in events:
            if 'markets' in event:
                for m in event['markets']:
                    m['parent_event_title'] = event.get('title', 'Unknown')
                    all_markets.append(m)

        # Sort by volume descending
        all_markets.sort(key=lambda x: float(x.get('volume', 0)), reverse=True)

        target_market = None
        for m in all_markets:
            outcomes = safe_parse_list(m.get('outcomes'))
            token_ids = safe_parse_list(m.get('clobTokenIds'))

            if len(outcomes) >= 2 and len(token_ids) >= 2:
                target_market = m
                target_market['parsed_outcomes'] = outcomes
                target_market['parsed_token_ids'] = token_ids
                break

        if not target_market:
            print("No valid market found.")
            return None

        yes_token_id = target_market['parsed_token_ids'][0]
        outcome_label = target_market['parsed_outcomes'][0]
        volume = target_market.get('volume', 0)

        print(f"🔥 [Top Market Locked] Question: {target_market['question']}")
        print(f"💰 [Total Volume] ${float(volume):,.2f}")
        print(f"📄 [Metadata] Token ID for option '{outcome_label}': {yes_token_id}")

        return yes_token_id

    except Exception as e:
        print(f"Gamma API Error: {e}")
        return None


# ==========================================
# 2. CLOB API (Get Full History)
# ==========================================
def run_clob_demo(token_id):
    print_separator("2. CLOB API (Get Price History)")

    if not token_id:
        return

    # --- Key Change: interval=max ---
    # Changed to 'max' (all history) or '30d' (last 30 days) to ensure data retrieval
    # Fidelity lowered slightly to reduce data size, set to 1000 minute aggregation here
    url = f"https://clob.polymarket.com/prices-history?interval=max&market={token_id}&fidelity=1000"

    try:
        print(f"🌍 Requesting [Full History Data] for this market (interval=max)...")
        response = requests.get(url, headers=HEADERS)
        data = response.json()

        if 'history' not in data or not data['history']:
            print("⚠️ Still no data: API might be under maintenance or ID has no trades.")
            # Fallback: Try orderbook
            run_orderbook_demo(token_id)
            return

        history = data['history']
        latest = history[-1]
        start = history[0]

        # Timestamp conversion
        start_time = datetime.fromtimestamp(start['t']).strftime('%Y-%m-%d %H:%M')
        end_time = datetime.fromtimestamp(latest['t']).strftime('%Y-%m-%d %H:%M')

        print(f"✅ [Success] Retrieved {len(history)} historical candlestick data points")
        print(f"---------- Data Snapshot ----------")
        print(f"📅 Start Time: {start_time} | Price: {start['p']} ({float(start['p']) * 100:.1f}%)")
        print(f"📅 End Time:   {end_time} | Price: {latest['p']} ({float(latest['p']) * 100:.1f}%)")
        print(f"-----------------------------------")

        change = float(latest['p']) - float(start['p'])
        direction = "🔺 UP" if change > 0 else "🔻 DOWN"
        print(f"📊 [Long-term Trend] All-time {direction} {abs(change) * 100:.2f}%")

    except Exception as e:
        print(f"CLOB API Error: {e}")


# ==========================================
# 3. Fallback: Orderbook (If no trades, check open orders)
# ==========================================
def run_orderbook_demo(token_id):
    print(f"\n🔄 Attempting to fetch real-time Orderbook...")
    url = f"https://clob.polymarket.com/book?token_id={token_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        data = response.json()

        bids = data.get('bids', [])
        asks = data.get('asks', [])

        if not bids and not asks:
            print("⚠️ No orders found, this might be a dead market.")
            return

        print(f"✅ [Order Data] Bids: {len(bids)} | Asks: {len(asks)}")
        if bids:
            best_bid = bids[0]
            print(f"💰 [Best Bid] Price: {best_bid['price']} | Size: {best_bid['size']}")
        if asks:
            best_ask = asks[0]
            print(f"💸 [Best Ask] Price: {best_ask['price']} | Size: {best_ask['size']}")

    except Exception as e:
        print(f"Orderbook request failed: {e}")


# ==========================================
# Main Program
# ==========================================
if __name__ == "__main__":
    print("🚀 Running Final Fixed Version (Interval=MAX)...")
    token_id = run_gamma_demo()
    time.sleep(1)
    run_clob_demo(token_id)