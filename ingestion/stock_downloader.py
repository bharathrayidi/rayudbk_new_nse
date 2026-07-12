"""
NSE Stock Data & Corporate Announcements Downloader (Parallel & Incremental)
----------------------------------------------------------------------------
Downloads:
  1. Historical stock price data (Open, High, Low, Close, Volume)
     for the last N years (default 1, up to 5) and saves each stock
     into its own table in stock_data.db.
  2. Corporate Announcements for each stock and appends them
     incrementally into a combined table in corporate_announcements.db.

Optimization:
  - If data already exists in the database for a symbol, the script
    automatically queries only the missing recent days (with a 2-day overlap)
    to minimize API calls, prevent blocks, and speed up daily execution.
  - Utilizes ThreadPoolExecutor for concurrent fetching and db_engine's Lock
    to prevent SQLite concurrency issues.

Imported configurations from central config.py registry.
"""

import sys
import time
import sqlite3
import argparse
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from nselib import capital_market
from nsepython import nsefetch
import os
# Ensure both the ingestion dir (for db_engine) and the project root (for config) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_engine import save_to_db
from config import (
    STOCK_DATA_DB,
    CORPORATE_DB,
    EQUITY_LIST_URL,
    CORP_ANNOUNCEMENTS_URL,
    DEFAULT_CRAWLER_WORKERS,
    DEFAULT_HISTORY_YEARS,
    DEFAULT_REQUEST_DELAY,
)

STOCK_DB = STOCK_DATA_DB
CORP_DB = CORPORATE_DB

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Removes special characters and BOM characters from column names."""
    df = df.copy()
    df.columns = [
        c.replace("﻿", "").replace('"', "").replace("'", "").strip()
        for c in df.columns
    ]
    return df

def get_stocks_list(nifty50_only: bool = True) -> list:
    """Fetches list of stock symbols from nselib (Nifty 50 or full EQUITY_L list)."""
    if nifty50_only:
        print("Fetching Nifty 50 stock list...")
        df = capital_market.nifty50_equity_list()
        return df["Symbol"].dropna().unique().tolist()
    else:
        print("Fetching full NSE listed stock list...")
        df = pd.read_csv(EQUITY_LIST_URL)
        return df["SYMBOL"].dropna().unique().tolist()

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

def get_last_announcement_date(symbol: str) -> datetime:
    """Returns the maximum announcement sort_date for a given symbol in announcements table."""
    try:
        conn = sqlite3.connect(CORP_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='announcements'")
        if not cursor.fetchone():
            conn.close()
            return None
            
        cursor.execute("SELECT DISTINCT sort_date FROM announcements WHERE symbol = ?", (symbol,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
            
        dates = []
        for r in rows:
            val = r[0]
            if val:
                try:
                    dates.append(datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M:%S"))
                except Exception:
                    pass
        if dates:
            return max(dates)
    except Exception as e:
        print(f"Error checking last announcement date for {symbol}: {e}")
    return None

def download_stock_history(symbol: str, from_date: str, to_date: str, timestamp: str):
    """Downloads historical prices and saves to stock_data.db."""
    try:
        df = capital_market.price_volume_and_deliverable_position_data(symbol, from_date, to_date)
        if df is None or df.empty:
            return
        
        df = clean_columns(df)
        table_name = f"hist_{symbol.replace('-', '_')}"
        save_to_db(STOCK_DB, df, table_name, timestamp, "Date")
    except Exception as e:
        print(f"[{symbol}] Error downloading price history: {e}")

def download_announcements(symbol: str, from_date: str, to_date: str, timestamp: str):
    """Downloads corporate announcements and saves to corporate_announcements.db."""
    try:
        url = f"{CORP_ANNOUNCEMENTS_URL}&symbol={symbol}&from_date={from_date}&to_date={to_date}"
        data = nsefetch(url)
        
        if not data or not isinstance(data, list):
            return
            
        df = pd.DataFrame(data)
        if df.empty:
            return
            
        df = clean_columns(df)
        if "symbol" not in df.columns:
            df["symbol"] = symbol
            
        save_to_db(CORP_DB, df, "announcements", timestamp, "seq_id")
    except Exception as e:
        print(f"[{symbol}] Error downloading announcements: {e}")

def process_symbol(symbol: str, from_date_str: str, to_date_str: str, timestamp: str, index_info: str):
    """Worker task processing a single symbol incrementally."""
    table_name = f"hist_{symbol.replace('-', '_')}"
    last_hist_dt = get_last_available_date(STOCK_DB, table_name, "Date", "%d-%b-%Y")
    
    if last_hist_dt:
        hist_from_date = (last_hist_dt - timedelta(days=2)).strftime("%d-%m-%Y")
        is_incremental_hist = True
    else:
        hist_from_date = from_date_str
        is_incremental_hist = False
        
    last_ann_dt = get_last_announcement_date(symbol)
    if last_ann_dt:
        ann_from_date = (last_ann_dt - timedelta(days=2)).strftime("%d-%m-%Y")
        is_incremental_ann = True
    else:
        ann_from_date = from_date_str
        is_incremental_ann = False
        
    mode_str = f"Incremental (hist since {hist_from_date}, ann since {ann_from_date})" if (is_incremental_hist or is_incremental_ann) else "Full baseline"
    print(f"[{index_info}] Processing {symbol} - Mode: {mode_str}")
    
    download_stock_history(symbol, hist_from_date, to_date_str, timestamp)
    time.sleep(DEFAULT_REQUEST_DELAY)
    
    download_announcements(symbol, ann_from_date, to_date_str, timestamp)

def main():
    parser = argparse.ArgumentParser(description="NSE Stock Data Downloader")
    parser.add_argument("--years", type=int, default=DEFAULT_HISTORY_YEARS, help="Number of years of historical data to fetch (1 to 5)")
    parser.add_argument("--nifty50", action="store_true", default=True, help="Download only Nifty 50 stocks (default)")
    parser.add_argument("--all", action="store_true", help="Download all listed NSE stocks (may take hours)")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols (e.g. SBIN,RELIANCE)")
    parser.add_argument("--workers", type=int, default=DEFAULT_CRAWLER_WORKERS, help="Number of concurrent threads/workers (default 5)")
    
    args = parser.parse_args()
    nifty50_flag = args.nifty50
    if args.all or args.symbols:
        nifty50_flag = False
        
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = get_stocks_list(nifty50_only=nifty50_flag)
        
    print(f"Resolved {len(symbols)} symbols to process.")
    
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=args.years * 365)
    
    to_date_str = to_dt.strftime("%d-%m-%Y")
    from_date_str = from_dt.strftime("%d-%m-%Y")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    workers = args.workers
    print(f"Starting parallel processing with {workers} threads...\n")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_symbol, symbol, from_date_str, to_date_str, timestamp, f"{i}/{len(symbols)}"): symbol
            for i, symbol in enumerate(symbols, 1)
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"[{symbol}] Thread generated an exception: {exc}")
                
    print("\nProcessing complete!")

if __name__ == "__main__":
    main()
