# Data Ingestion Module

This module handles the retrieval of market data from Polymarket APIs.

## Components

- **`scripts/fetch_market_sdk.py`**: A Python script that:
    1.  Resolves a human-readable Market Slug to a CLOB Token ID using the Gamma API.
    2.  Fetches historical price candles (OHLC) from the CLOB REST API.
    3.  Performs basic anomaly detection (e.g., price spikes > 5% per hour).

## Setup & Usage

1.  **Environment**: Ensure you have Python 3.9+ and the dependencies installed.
    ```bash
    pip install -r ../requirements.txt
    ```

2.  **Run the Script**:
    ```bash
    python scripts/fetch_market_sdk.py
    ```

## Logic
The script uses explicit `startTs` and `endTs` to ensure historical data can be retrieved even for closed markets (e.g., 2024 Election).
