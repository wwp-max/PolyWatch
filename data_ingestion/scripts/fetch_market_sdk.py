import requests
import pandas as pd
import json
from py_clob_client.client import ClobClient
from datetime import datetime, timezone

# --- Configuration ---
MARKET_SLUG = "presidential-election-winner-2024"

# Election Week 2024 (Nov 1 - Nov 7)
# We MUST use specific timestamps because the market is closed/old.
START_DATE = datetime(2024, 11, 1, tzinfo=timezone.utc)
END_DATE = datetime(2024, 11, 7, tzinfo=timezone.utc)

# API Constants
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"

def get_token_id_from_slug(slug):
    """Resolve Slug -> Token ID (YES Token)"""
    print(f"🔎 Resolving Slug: {slug}...")
    try:
        url = f"{GAMMA_API_URL}/events"
        params = {"slug": slug}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        if not data: return None
        if not data[0].get('markets'): return None
             
        market = data[0]['markets'][0]
        question = market['question']
        
        # Parse clobTokenIds
        clob_ids = market.get('clobTokenIds')
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except json.JSONDecodeError:
                import ast
                clob_ids = ast.literal_eval(clob_ids)
        
        if not clob_ids or not isinstance(clob_ids, list):
            return None
            
        clob_token_id = clob_ids[0] # Index 0 is YES
        
        print(f"✅ Found Market: {question}")
        print(f"🔑 Token ID: {clob_token_id}")
        return clob_token_id
        
    except Exception as e:
        print(f"❌ Resolution Error: {e}")
        return None

def fetch_history_rest(token_id):
    """
    Fetch History with EXPLICIT timestamps.
    Crucial for older/closed markets.
    """
    print(f"\n📜 Fetching Price History ({START_DATE.date()} to {END_DATE.date()})...")
    url = f"{CLOB_API_HOST}/prices-history"
    
    params = {
        "market": token_id,
        "startTs": int(START_DATE.timestamp()),
        "endTs": int(END_DATE.timestamp()),
        "fidelity": 60 # Hourly
    }
    
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        if not data or 'history' not in data:
            print(f"⚠️ No history data found.")
            return None
            
        df = pd.DataFrame(data['history'])
        
        if df.empty:
            print("⚠️ History DataFrame is empty.")
            return None

        # Clean Data
        df['timestamp'] = pd.to_datetime(df['t'], unit='s')
        df['price'] = df['p']
        df = df[['timestamp', 'price']]
        
        print(f"✅ Fetched {len(df)} data points.")
        return df
        
    except Exception as e:
        print(f"❌ History API Error: {e}")
        if 'resp' in locals():
            print(f"   Response: {resp.text[:200]}")
        return None

def analyze_pump_dump(df):
    """Analyze for Anomalies"""
    if df is None or df.empty: return
    
    df['pct_change'] = df['price'].pct_change()
    anomalies = df[df['pct_change'].abs() > 0.05]
    
    print("\n🚨 --- Analysis Report ---")
    print(f"Total Anomalies Detected: {len(anomalies)}")
    
    if not anomalies.empty:
        print("\nTop 5 Volatility Events:")
        top = anomalies.sort_values('pct_change', key=abs, ascending=False).head(5)
        for _, row in top.iterrows():
            print(f"  ⏰ {row['timestamp']} | 💲 {row['price']:.3f} | 📈 Change: {row['pct_change']*100:.1f}%")

if __name__ == "__main__":
    token_id = get_token_id_from_slug(MARKET_SLUG)
    if token_id:
        df = fetch_history_rest(token_id)
        if df is not None:
            analyze_pump_dump(df)
            print("\n[SUCCESS] M1 Evidence Generated.")
