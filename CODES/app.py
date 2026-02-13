import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np


# ==========================================
# 1. Advanced Data Generator (Simulate Realistic Trends)
# ==========================================
def generate_realistic_market_data(market_slug, base_price, volatility, trend_strength, anomalies_config):
    """
    Generates realistic financial time series data using Random Walk.

    :param volatility: Volatility (higher values mean more jagged lines)
    :param trend_strength: Trend strength (positive for upward, negative for downward)
    :param anomalies_config: List of anomaly events to inject
    """
    points = 150
    base_time = datetime.utcnow() - timedelta(hours=6)
    timestamps = [base_time + timedelta(minutes=i * 2) for i in range(points)]

    # --- Core Algorithm: Random Walk ---
    # 1. Generate random noise (Normal Distribution)
    noise = np.random.normal(0, volatility, points)
    # 2. Generate trend line
    trend = np.linspace(0, trend_strength, points)
    # 3. Accumulate to get price curve (Random Walk)
    # Price = Base + Cumulative Noise + Trend
    price_changes = np.cumsum(noise) + trend
    prices = base_price + price_changes

    # Clip prices between 0.01 and 0.99 (Prediction Market Characteristics)
    prices = np.clip(prices, 0.01, 0.99)

    # --- Construct JSON Structure (Time Series) ---
    time_series = []
    for i in range(points):
        time_series.append({
            "timestamp": timestamps[i].isoformat() + "Z",
            "price": round(prices[i], 3),
            "volume": int(np.random.randint(1000, 50000) * (1 + abs(noise[i]) * 10)),  # Higher volatility implies higher volume
            "liquidity_depth": int(np.random.randint(20000, 80000))
        })

    # --- Construct Anomalies ---
    # Automatically calculate anomaly timeframes based on config
    detected_anomalies = []
    for anomaly in anomalies_config:
        # Simple logic: Place anomaly at specific percentage of timeline (e.g., 20%)
        start_idx = int(points * anomaly['pos_pct'])
        end_idx = start_idx + anomaly['duration']

        detected_anomalies.append({
            "event_id": f"evt_{np.random.randint(1000, 9999)}",
            "type": anomaly['type'],
            "severity": anomaly['severity'],
            "confidence": anomaly['confidence'],
            "start_time": timestamps[start_idx].isoformat() + "Z",
            "end_time": timestamps[end_idx].isoformat() + "Z",  # Ensure no out-of-bounds
            "description": anomaly['desc']
        })

    # --- Return Complete JSON Payload ---
    return {
        "meta": {
            "market_id": f"0x{hash(market_slug) & 0xFFFFFF:06x}",
            "market_slug": market_slug,
            "outcome_token": "YES",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        },
        "summary_stats": {
            "current_price": round(prices[-1], 2),
            "24h_volume_usd": int(np.sum([x['volume'] for x in time_series])),
            "volatility_score": round(volatility * 100, 2),  # Simple volatility score
            "risk_level": "HIGH" if volatility > 0.02 else "LOW"
        },
        "time_series": time_series,
        "detected_anomalies": detected_anomalies
    }


# ==========================================
# 2. Mock Backend Database (Multiple Event Sources)
# ==========================================
# Simulates backend storage of analysis results for different markets
MOCK_DATABASE = {
    "US_ELECTION_2024": generate_realistic_market_data(
        market_slug="Trump vs Harris 2024",
        base_price=0.45,
        volatility=0.015,  # High Volatility
        trend_strength=0.2,  # Clear Upward Trend
        anomalies_config=[
            {"type": "WASH_TRADING", "severity": "CRITICAL", "confidence": 0.98, "pos_pct": 0.2, "duration": 5,
             "desc": "Circular trading detected"},
            {"type": "WHALE_DUMP", "severity": "HIGH", "confidence": 0.85, "pos_pct": 0.7, "duration": 3,
             "desc": "Large holder exit"}
        ]
    ),
    "FED_RATE_DEC": generate_realistic_market_data(
        market_slug="Fed Rate Cut Dec 2024",
        base_price=0.80,
        volatility=0.005,  # Low Volatility (Macroeconomics are usually stable)
        trend_strength=-0.05,  # Slight Downward Trend
        anomalies_config=[
            {"type": "LIQUIDITY_GAP", "severity": "MEDIUM", "confidence": 0.75, "pos_pct": 0.5, "duration": 8,
             "desc": "Thin orderbook depth"}
        ]
    ),
    "SUPER_BOWL_LIX": generate_realistic_market_data(
        market_slug="Super Bowl: Chiefs vs 49ers",
        base_price=0.50,
        volatility=0.025,  # Extreme Volatility (Sports Events)
        trend_strength=0.0,  # Oscillating/Choppy
        anomalies_config=[
            {"type": "SPOOFING", "severity": "LOW", "confidence": 0.60, "pos_pct": 0.1, "duration": 4,
             "desc": "Fake buy orders cancelled"},
            {"type": "WASH_TRADING", "severity": "MEDIUM", "confidence": 0.88, "pos_pct": 0.8, "duration": 6,
             "desc": "Volume padding"}
        ]
    )
}

# ==========================================
# 3. Streamlit Frontend Logic
# ==========================================
st.set_page_config(page_title="Polymarket Signal Analysis", layout="wide")

# CSS Style Optimization
st.markdown("""
<style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: Event Switcher ---
with st.sidebar:
    st.header("🎛️ Monitor Control")
    selected_event_key = st.selectbox(
        "Select Active Market",
        options=list(MOCK_DATABASE.keys()),
        format_func=lambda x: MOCK_DATABASE[x]['meta']['market_slug']  # Display friendlier names
    )

    st.markdown("---")
    st.info(f"Current Feed: {selected_event_key}")
    st.caption("Data source: Mock JSON API v1.0")

# --- Get Currently Selected Data ---
data = MOCK_DATABASE[selected_event_key]
df = pd.DataFrame(data['time_series'])
df['timestamp'] = pd.to_datetime(df['timestamp'])

# --- Main Dashboard ---
st.title(f"🕵️ Anomaly Detector: {data['meta']['market_slug']}")
st.caption(f"Market ID: {data['meta']['market_id']} | Generated: {data['meta']['generated_at']}")

# Row 1: KPI
stats = data['summary_stats']
c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Price", f"{int(stats['current_price'] * 100)}¢", delta=None)
c2.metric("24h Volume", f"${stats['24h_volume_usd']:,.0f}")
c3.metric("Volatility Score", stats['volatility_score'])
risk_color = "red" if stats['risk_level'] == "HIGH" else "green"
c4.markdown(f"### Risk: :{risk_color}[{stats['risk_level']}]")

# Row 2: Core Chart (Plotly)
st.subheader("📉 Price History & Anomalies")

fig = go.Figure()

# 1. Price Line - Looks more natural now
fig.add_trace(go.Scatter(
    x=df['timestamp'], y=df['price'],
    mode='lines', name='Price',
    line=dict(color='#0052cc', width=2),
    fill='tozeroy',  # Fill bottom color for financial look
    fillcolor='rgba(0, 82, 204, 0.05)'
))

# 2. Dynamically draw anomaly regions
anomaly_colors = {
    "WASH_TRADING": "rgba(255, 50, 50, 0.2)",  # Red
    "LIQUIDITY_GAP": "rgba(255, 165, 0, 0.2)",  # Orange
    "SPOOFING": "rgba(128, 0, 128, 0.2)",  # Purple
    "WHALE_DUMP": "rgba(0, 0, 255, 0.2)"  # Blue
}

for event in data['detected_anomalies']:
    start_dt = pd.to_datetime(event['start_time'])
    end_dt = pd.to_datetime(event['end_time'])
    color = anomaly_colors.get(event['type'], "rgba(128,128,128,0.2)")

    # Draw highlighted rectangle
    fig.add_vrect(
        x0=start_dt, x1=end_dt,
        fillcolor=color, opacity=1, layer="below", line_width=0,
    )
    # Add annotation text (avoid overlap)
    fig.add_annotation(
        x=start_dt, y=df['price'].max(),
        text=event['type'], showarrow=False,
        yshift=10, font=dict(size=10, color="gray")
    )

fig.update_layout(
    height=450,
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis_title=None,
    yaxis_title="Probability (Price)",
    hovermode="x unified",
    plot_bgcolor="white"
)
fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', range=[df['price'].min() * 0.9, df['price'].max() * 1.1])
st.plotly_chart(fig, use_container_width=True)

# Row 3: Event Log & JSON View
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("🛡️ Anomaly Evidence Log")
    anomalies_df = pd.DataFrame(data['detected_anomalies'])
    if not anomalies_df.empty:
        st.dataframe(
            anomalies_df[['start_time', 'type', 'severity', 'confidence', 'description']],
            use_container_width=True,
            column_config={
                "confidence": st.column_config.ProgressColumn("Conf.", format="%.2f", min_value=0, max_value=1)
            }
        )
    else:
        st.info("No anomalies detected in this timeframe.")

with col_right:
    st.subheader("🔧 Spec Validation")
    with st.expander("View JSON Payload"):
        st.json(data)