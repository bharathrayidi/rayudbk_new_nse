"""
NSE Capital Market Data Collector
----------------------------------
Pulls live NSE Capital Market sections and stores each one
into its own table in a SQLite database (capital_market.db).
Uses db_engine.py for incremental saving logic.

Install first:
    pip install nsepython pandas
"""

import pandas as pd
from datetime import datetime
from nsepython import (
    nsefetch,
    nse_most_active,
    nse_price_band_hitters,
    nse_largedeals,
)
import os
import sys
# Ensure both the ingestion dir (for db_engine) and the project root (for config) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_engine import save_to_db
from config import CAPITAL_MARKET_DB
DB_NAME = CAPITAL_MARKET_DB

# ---------------------- Capital Market Fetchers ----------------------

def fetch_top_gainers_losers():
    """
    Fetches Nifty 50 top gainers and losers.
    """
    gainers_data = nsefetch("https://www.nseindia.com/api/live-analysis-variations?index=gainers")
    g_records = gainers_data.get("NIFTY", {}).get("data", [])
    gainers = pd.DataFrame(g_records)
    if not gainers.empty:
        gainers["type"] = "gainer"
        
    losers_data = nsefetch("https://www.nseindia.com/api/live-analysis-variations?index=loosers")
    l_records = losers_data.get("NIFTY", {}).get("data", [])
    losers = pd.DataFrame(l_records)
    if not losers.empty:
        losers["type"] = "loser"
        
    if not gainers.empty or not losers.empty:
        return pd.concat([gainers, losers], ignore_index=True)
    return pd.DataFrame()


def fetch_most_active_equities():
    return nse_most_active(type="securities", sort="value")


def fetch_index_performances():
    data = nsefetch("https://www.nseindia.com/api/allIndices")
    return pd.DataFrame(data.get("data", []))


def fetch_price_band_hitters():
    return nse_price_band_hitters(bandtype="both", view="AllSec")


def fetch_volume_gainers():
    data = nsefetch("https://www.nseindia.com/api/live-analysis-volume-gainers")
    return pd.DataFrame(data.get("data", []))


def fetch_52_week_high_low():
    high_data = nsefetch("https://www.nseindia.com/api/live-analysis-data-52weekhighstock")
    low_data = nsefetch("https://www.nseindia.com/api/live-analysis-data-52weeklowstock")
    df_high = pd.DataFrame(high_data.get("data", []))
    df_high["type"] = "52w_high"
    df_low = pd.DataFrame(low_data.get("data", []))
    df_low["type"] = "52w_low"
    return pd.concat([df_high, df_low], ignore_index=True)


def fetch_large_deals():
    bulk = nse_largedeals(mode="bulk_deals")
    bulk["deal_type"] = "bulk"
    block = nse_largedeals(mode="block_deals")
    block["deal_type"] = "block"
    return pd.concat([bulk, block], ignore_index=True)


def fetch_advances_declines():
    data = nsefetch("https://www.nseindia.com/api/live-analysis-advance")
    records = data.get("advance", {}).get("data", [])
    if not records:
        records = data.get("data", [])
    return pd.DataFrame(records)


def fetch_stocks_traded():
    return nse_most_active(type="securities", sort="volume")


# =======================================================================
# REGISTRY -- Capital Market Data Sources
# =======================================================================
DATA_SOURCES = [
    {"table": "top_gainers_losers",    "fetch": fetch_top_gainers_losers,    "key_cols": "symbol"},
    {"table": "most_active_equities",  "fetch": fetch_most_active_equities,  "key_cols": "symbol"},
    {"table": "index_performances",    "fetch": fetch_index_performances,    "key_cols": "index"},
    {"table": "price_band_hitters",    "fetch": fetch_price_band_hitters,    "key_cols": "symbol"},
    {"table": "volume_gainers",        "fetch": fetch_volume_gainers,        "key_cols": "symbol"},
    {"table": "week_52_high_low",      "fetch": fetch_52_week_high_low,      "key_cols": ["symbol", "type"]},
    {"table": "large_deals",           "fetch": fetch_large_deals,           "key_cols": ["symbol", "deal_type", "clientName"]},
    {"table": "advances_declines",     "fetch": fetch_advances_declines,     "key_cols": "symbol"},
    {"table": "stocks_traded",         "fetch": fetch_stocks_traded,         "key_cols": "symbol"},
]

def run_all():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Starting NSE Capital Market data pull at {timestamp}\n")

    for source in DATA_SOURCES:
        table = source["table"]
        try:
            df = source["fetch"]()
            save_to_db(DB_NAME, df, table, timestamp, source["key_cols"])
        except Exception as e:
            print(f"[{table}] ERROR: {e}")

    print(f"\nDone. Capital Market data saved to {DB_NAME}")

if __name__ == "__main__":
    run_all()
