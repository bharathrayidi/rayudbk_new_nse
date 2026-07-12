"""
NSE Index Option Chain Downloader (v3 API)
-------------------------------------------
Downloads live Option Chain data for major NSE indices (NIFTY, BANKNIFTY,
FINNIFTY, MIDCPNIFTY) and stores each index in its own table (e.g. opt_nifty).
Each row represents a single strike price containing CE and PE columns side-by-side
(prefixed with ce_ and pe_ respectively).

Uses nsepython's core nsefetch to query the new option-chain-v3 API
which remains accessible on weekends and non-market hours.

Best run during market hours (9:15 AM - 3:30 PM IST, weekdays).

Imported configurations from central config.py registry.
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from nsepython import nsefetch
import os
import sys
# Ensure both the ingestion dir (for db_engine) and the project root (for config) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_engine import save_to_db
from config import (
    OPTION_CHAIN_DB,
    OPTION_CHAIN_INDEX_SYMBOLS,
    OPTION_CHAIN_V3_URL,
)

DB_NAME = OPTION_CHAIN_DB
INDEX_SYMBOLS = OPTION_CHAIN_INDEX_SYMBOLS

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Removes special characters, lowercases column names, and drops duplicates."""
    df = df.copy()
    cleaned_cols = [
        c.replace("﻿", "").replace('"', "").replace("'", "").strip().lower()
        for c in df.columns
    ]
    df.columns = cleaned_cols
    # Remove duplicate columns (keeping first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def get_active_expiry_dates() -> list:
    """Calculates upcoming Tuesday and queries option-chain-v3 to get active expiries."""
    today = datetime.now()
    days_ahead = (1 - today.weekday()) % 7
    baseline_dt = (today + timedelta(days=days_ahead)).strftime("%d-%b-%Y")
    
    url = f"{OPTION_CHAIN_V3_URL}?type=Indices&symbol=NIFTY&expiry={baseline_dt}"
    try:
        data = nsefetch(url)
        if isinstance(data, dict):
            expiries = data.get("records", {}).get("expiryDates", [])
            if expiries:
                return expiries
    except Exception as e:
        print(f"Error fetching active expiry dates list: {e}")
        
    return [baseline_dt]

def fetch_and_flatten_option_chain(symbol: str, expiry: str) -> pd.DataFrame:
    """Retrieves and flattens Option Chain data for a given index symbol and expiry."""
    print(f"[{symbol}] Fetching option chain for expiry {expiry}...")
    all_rows = []
    
    url = f"{OPTION_CHAIN_V3_URL}?type=Indices&symbol={symbol}&expiry={expiry}"
    try:
        payload = nsefetch(url)
        if not payload or not isinstance(payload, dict):
            print(f"[{symbol}] Option chain empty for expiry {expiry}.")
            return pd.DataFrame()
            
        records = payload.get("records", {}).get("data", [])
        if not records:
            return pd.DataFrame()
            
        # Extract aggregate open interest and volume from the filtered section
        filtered_ce = payload.get("filtered", {}).get("CE", {})
        filtered_pe = payload.get("filtered", {}).get("PE", {})
            
        for strike_row in records:
            expiry_date = strike_row.get("expiryDate")
            strike = strike_row.get("strikePrice")
            
            row_data = {
                "symbol": symbol,
                "expiryDate": expiry_date,
                "strikePrice": strike
            }
            
            # Map CE fields side-by-side
            ce_data = strike_row.get("CE", {})
            if ce_data and isinstance(ce_data, dict):
                for k, v in ce_data.items():
                    row_data[f"ce_{k}"] = v
                    
            # Map PE fields side-by-side
            pe_data = strike_row.get("PE", {})
            if pe_data and isinstance(pe_data, dict):
                for k, v in pe_data.items():
                    row_data[f"pe_{k}"] = v
            
            # Append overall totals
            row_data["total_ce_oi"] = filtered_ce.get("totOI")
            row_data["total_ce_vol"] = filtered_ce.get("totVol")
            row_data["total_pe_oi"] = filtered_pe.get("totOI")
            row_data["total_pe_vol"] = filtered_pe.get("totVol")
            
            all_rows.append(row_data)
                    
    except Exception as e:
        print(f"[{symbol}] Error parsing option chain for {expiry}: {e}")
        
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = clean_columns(df)
    return df

def run_downloader():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Starting Option Chain data pull at {timestamp}\n")
    
    expiries = get_active_expiry_dates()
    target_expiries = expiries[:3]
    print(f"Targeting active expiries: {target_expiries}\n")
    
    for symbol in INDEX_SYMBOLS:
        table_name = f"opt_{symbol.lower()}"
        for expiry in target_expiries:
            df = fetch_and_flatten_option_chain(symbol, expiry)
            if not df.empty:
                # Key columns: symbol, expirydate, strikeprice
                save_to_db(
                    DB_NAME, 
                    df, 
                    table_name, 
                    timestamp, 
                    ["symbol", "expirydate", "strikeprice"]
                )
            time.sleep(0.5)
            
    print(f"\nDone. Option Chain data saved to {DB_NAME}")

if __name__ == "__main__":
    run_downloader()
