"""
NSE Derivatives Market Data Collector
--------------------------------------
Pulls live NSE Derivatives (F&O) Market sections and stores each one
into its own table in a SQLite database (derivatives_market.db).
Uses db_engine.py for incremental saving logic.

Install first:
    pip install nsepython pandas
"""

import sys
import pandas as pd
from datetime import datetime
from functools import lru_cache
from nsepython import (
    nsefetch,
    nse_optionchain_scrapper,
)
import os
# Ensure both the ingestion dir (for db_engine) and the project root (for config) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_engine import save_to_db
from config import DERIVATIVES_MARKET_DB
DB_NAME = DERIVATIVES_MARKET_DB

# Symbols to retrieve option chain data for
OPTION_CHAIN_SYMBOLS = ["NIFTY", "BANKNIFTY"]

# ---------------------- Derivatives Market Fetchers ----------------------

def fetch_fno_gainers_losers():
    """
    Fetches F&O segment top gainers and losers.
    """
    gainers_data = nsefetch("https://www.nseindia.com/api/live-analysis-variations?index=gainers")
    g_records = gainers_data.get("FOSec", {}).get("data", [])
    gainers = pd.DataFrame(g_records)
    if not gainers.empty:
        gainers["type"] = "gainer"
        
    losers_data = nsefetch("https://www.nseindia.com/api/live-analysis-variations?index=loosers")
    l_records = losers_data.get("FOSec", {}).get("data", [])
    losers = pd.DataFrame(l_records)
    if not losers.empty:
        losers["type"] = "loser"
        
    if not gainers.empty or not losers.empty:
        return pd.concat([gainers, losers], ignore_index=True)
    return pd.DataFrame()


def _fetch_most_active_contracts_view(index_value: str, limit: int = 20) -> pd.DataFrame:
    data = nsefetch(
        f"https://www.nseindia.com/api/snapshot-derivatives-equity?index={index_value}&limit={limit}"
    )
    all_flat = []
    if isinstance(data, dict):
        for ranking_type in ("volume", "value", "oi"):
            if ranking_type in data and isinstance(data[ranking_type], dict):
                contracts_list = data[ranking_type].get("data", [])
                if isinstance(contracts_list, list):
                    for contract in contracts_list:
                        if isinstance(contract, dict):
                            contract_flat = dict(contract)
                            contract_flat["rankingType"] = ranking_type
                            all_flat.append(contract_flat)
                            
    return pd.DataFrame(all_flat)


def fetch_most_active_futures():
    return _fetch_most_active_contracts_view("futures")


def fetch_most_active_options():
    return _fetch_most_active_contracts_view("options")


def fetch_most_active_index_calls():
    return _fetch_most_active_contracts_view("calls-index-vol")


def fetch_most_active_index_puts():
    return _fetch_most_active_contracts_view("puts-index-vol")


def fetch_most_active_stock_calls():
    return _fetch_most_active_contracts_view("calls-stocks-vol")


def fetch_most_active_stock_puts():
    return _fetch_most_active_contracts_view("puts-stocks-vol")


def fetch_most_active_contracts_by_oi():
    return _fetch_most_active_contracts_view("oi")


def fetch_most_active_contracts_combined():
    return _fetch_most_active_contracts_view("contracts")


def fetch_most_active_underlying():
    data = nsefetch("https://www.nseindia.com/api/live-analysis-most-active-underlying")
    return pd.DataFrame(data.get("data", data) if isinstance(data, dict) else data)


@lru_cache(maxsize=1)
def _raw_oi_spurts():
    return nsefetch("https://www.nseindia.com/api/live-analysis-oi-spurts-contracts")


def _extract_oi_quadrant(quadrant_key: str) -> pd.DataFrame:
    payload = _raw_oi_spurts()
    for block in payload.get("data", []):
        if quadrant_key in block:
            return pd.DataFrame(block[quadrant_key])
    return pd.DataFrame()


def fetch_oi_long_buildup():
    return _extract_oi_quadrant("Rise-in-OI-Rise")


def fetch_oi_short_buildup():
    return _extract_oi_quadrant("Rise-in-OI-Slide")


def fetch_oi_short_covering():
    return _extract_oi_quadrant("Slide-in-OI-Rise")


def fetch_oi_long_unwinding():
    return _extract_oi_quadrant("Slide-in-OI-Slide")


def fetch_option_chain():
    all_rows = []
    for symbol in OPTION_CHAIN_SYMBOLS:
        try:
            payload = nse_optionchain_scrapper(symbol)
            records = payload.get("records", {}).get("data", [])
            for strike_row in records:
                expiry = strike_row.get("expiryDate")
                strike = strike_row.get("strikePrice")
                for leg in ("CE", "PE"):
                    if leg in strike_row:
                        leg_data = dict(strike_row[leg])
                        leg_data["symbol"] = symbol
                        leg_data["expiryDate"] = expiry
                        leg_data["strikePrice"] = strike
                        leg_data["optionType"] = leg
                        all_rows.append(leg_data)
        except Exception as e:
            print(f"[option_chain] Error scanning option chain for {symbol}: {e}")
            
    return pd.DataFrame(all_rows)


# =======================================================================
# REGISTRY -- Derivatives Market Data Sources
# =======================================================================
DATA_SOURCES = [
    {"table": "fno_gainers_losers",            "fetch": fetch_fno_gainers_losers,            "key_cols": "symbol"},
    {"table": "most_active_futures",           "fetch": fetch_most_active_futures,           "key_cols": ["symbol", "expiryDate", "rankingType"]},
    {"table": "most_active_options",           "fetch": fetch_most_active_options,           "key_cols": ["symbol", "expiryDate", "strikePrice", "optionType", "rankingType"]},
    {"table": "most_active_index_calls",       "fetch": fetch_most_active_index_calls,       "key_cols": ["symbol", "expiryDate", "strikePrice", "rankingType"]},
    {"table": "most_active_index_puts",        "fetch": fetch_most_active_index_puts,        "key_cols": ["symbol", "expiryDate", "strikePrice", "rankingType"]},
    {"table": "most_active_stock_calls",       "fetch": fetch_most_active_stock_calls,       "key_cols": ["symbol", "expiryDate", "strikePrice", "rankingType"]},
    {"table": "most_active_stock_puts",        "fetch": fetch_most_active_stock_puts,        "key_cols": ["symbol", "expiryDate", "strikePrice", "rankingType"]},
    {"table": "most_active_contracts_by_oi",   "fetch": fetch_most_active_contracts_by_oi,   "key_cols": ["symbol", "expiryDate", "rankingType"]},
    {"table": "most_active_contracts_combined", "fetch": fetch_most_active_contracts_combined, "key_cols": ["symbol", "expiryDate", "strikePrice", "optionType", "instrumentType", "rankingType"]},
    {"table": "most_active_underlying",        "fetch": fetch_most_active_underlying,        "key_cols": "symbol"},
    {"table": "oi_spurts_long_buildup",        "fetch": fetch_oi_long_buildup,        "key_cols": "identifier"},
    {"table": "oi_spurts_short_buildup",       "fetch": fetch_oi_short_buildup,       "key_cols": "identifier"},
    {"table": "oi_spurts_short_covering",      "fetch": fetch_oi_short_covering,      "key_cols": "identifier"},
    {"table": "oi_spurts_long_unwinding",      "fetch": fetch_oi_long_unwinding,      "key_cols": "identifier"},
    {"table": "option_chain",                  "fetch": fetch_option_chain,                  "key_cols": ["symbol", "expiryDate", "strikePrice", "optionType"]},
]

def verify_endpoints():
    checks = {
        "fno_gainers_losers": fetch_fno_gainers_losers,
        "most_active_futures": fetch_most_active_futures,
        "most_active_options": fetch_most_active_options,
        "most_active_index_calls": fetch_most_active_index_calls,
        "most_active_index_puts": fetch_most_active_index_puts,
        "most_active_stock_calls": fetch_most_active_stock_calls,
        "most_active_stock_puts": fetch_most_active_stock_puts,
        "most_active_contracts_by_oi": fetch_most_active_contracts_by_oi,
        "most_active_contracts_combined": fetch_most_active_contracts_combined,
        "most_active_underlying": fetch_most_active_underlying,
        "oi_spurts_long_buildup": fetch_oi_long_buildup,
        "oi_spurts_short_buildup": fetch_oi_short_buildup,
        "oi_spurts_short_covering": fetch_oi_short_covering,
        "oi_spurts_long_unwinding": fetch_oi_long_unwinding,
        "option_chain": fetch_option_chain,
    }
    print("Verifying derivatives endpoints...\n")
    for name, fn in checks.items():
        try:
            if name.startswith("oi_spurts_"):
                _raw_oi_spurts.cache_clear()
            df = fn()
            status = f"OK -- {len(df)} rows" if not df.empty else "EMPTY (check param / market hours)"
        except Exception as e:
            status = f"FAILED -- {e}"
        print(f"  {name:32s} {status}")

def run_all():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Starting NSE Derivatives Market data pull at {timestamp}\n")

    for source in DATA_SOURCES:
        table = source["table"]
        try:
            df = source["fetch"]()
            save_to_db(DB_NAME, df, table, timestamp, source["key_cols"])
        except Exception as e:
            print(f"[{table}] ERROR: {e}")

    print(f"\nDone. Derivatives Market data saved to {DB_NAME}")

if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify_endpoints()
    else:
        run_all()
