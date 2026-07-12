"""
NSE Index Historical Data Downloader (Parallel & Incremental)
--------------------------------------------------------------
Downloads daily historical price data (Open, High, Low, Close, Volume)
for major indices (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY) and saves
each one into its own table (e.g. hist_NIFTY) in stock_data.db.

Optimization:
  - If data already exists in the database for an index, it queries only
    the missing recent days (with a 2-day overlap).
  - Splitting: Automatically splits large requests into chunks of 60 days
    to comply with NSE index API range restrictions.
  - Integrates clean column mapping to align with stock history tables.
"""

import time
import sqlite3
import argparse
import pandas as pd
from datetime import datetime, timedelta
from nselib import capital_market
import os
import sys
# Ensure both the ingestion dir (for db_engine) and the project root (for config) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_engine import save_to_db
from config import (
    STOCK_DATA_DB,
    DEFAULT_HISTORY_YEARS,
    DEFAULT_REQUEST_DELAY,
    INDEX_HISTORY_MAPPING,
)

STOCK_DB = STOCK_DATA_DB

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Removes special characters and BOM characters from column names."""
    df = df.copy()
    df.columns = [
        c.replace("﻿", "").replace('"', "").replace("'", "").strip()
        for c in df.columns
    ]
    return df

def get_last_available_date(db_name: str, table_name: str, date_col: str, date_format: str = "%d-%b-%Y") -> datetime:
    """Returns the maximum date present in the SQLite table, or None if the table doesn't exist/is empty."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return None
            
        cursor.execute(f"SELECT DISTINCT {date_col} FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
            
        dates = []
        for r in rows:
            val = r[0]
            if val:
                try:
                    dates.append(datetime.strptime(str(val).strip(), date_format))
                except Exception:
                    pass
        if dates:
            return max(dates)
    except Exception as e:
        print(f"Error checking last date in {table_name}: {e}")
    return None

def download_index_history(symbol: str, index_name: str, from_date: str, to_date: str, timestamp: str):
    """Downloads historical index prices and saves to stock_data.db under hist_{symbol}."""
    try:
        table_name = f"hist_{symbol}"
        df = capital_market.index_data(index_name, from_date, to_date)
        if df is None or df.empty:
            return
            
        df = clean_columns(df)
        
        # Rename columns to match stock price history tables for uniformity
        df = df.rename(columns={
            "INDEX_NAME": "Symbol",
            "OPEN_INDEX_VAL": "Open",
            "HIGH_INDEX_VAL": "High",
            "LOW_INDEX_VAL": "Low",
            "CLOSE_INDEX_VAL": "Close",
            "TRADED_QTY": "Volume",
            "TIMESTAMP": "Date"
        })
        
        if "Symbol" in df.columns:
            df["Symbol"] = symbol
            
        save_to_db(STOCK_DB, df, table_name, timestamp, "Date")
    except Exception as e:
        print(f"[{symbol}] Error downloading index history: {e}")

def download_index_history_in_chunks(symbol: str, index_name: str, start_dt: datetime, end_dt: datetime, timestamp: str):
    """Downloads historical index data in chunks of 60 days to comply with NSE API date range restrictions."""
    delta = end_dt - start_dt
    if delta.days <= 0:
        return
        
    chunk_size = timedelta(days=60)
    current_start = start_dt
    
    while current_start < end_dt:
        current_end = min(current_start + chunk_size, end_dt)
        from_str = current_start.strftime("%d-%m-%Y")
        to_str = current_end.strftime("%d-%m-%Y")
        
        print(f"[{symbol}] Fetching chunk from {from_str} to {to_str}...")
        download_index_history(symbol, index_name, from_str, to_str, timestamp)
        time.sleep(DEFAULT_REQUEST_DELAY)
        
        current_start = current_end + timedelta(days=1)

def run_downloader(years: int = DEFAULT_HISTORY_YEARS):
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=years * 365)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Starting Index History data pull at {timestamp}\n")
    
    for symbol, index_name in INDEX_HISTORY_MAPPING.items():
        table_name = f"hist_{symbol}"
        last_hist_dt = get_last_available_date(STOCK_DB, table_name, "Date", "%d-%b-%Y")
        
        if last_hist_dt:
            # Request delta data (with safe 2-day overlap)
            hist_from_dt = last_hist_dt - timedelta(days=2)
            mode_str = f"Incremental (since {hist_from_dt.strftime('%d-%m-%Y')})"
        else:
            hist_from_dt = from_dt
            mode_str = "Full baseline"
            
        print(f"--- Processing {symbol} ({index_name}) - Mode: {mode_str} ---")
        download_index_history_in_chunks(symbol, index_name, hist_from_dt, to_dt, timestamp)
        
    print("\nIndex history download complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NSE Index History Downloader")
    parser.add_argument("--years", type=int, default=DEFAULT_HISTORY_YEARS, help="Number of years of historical data to fetch (1 to 5)")
    args = parser.parse_args()
    
    run_downloader(years=args.years)
