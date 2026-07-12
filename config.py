"""
Centralized Configuration & Constants for NSE Data Collector
------------------------------------------------------------
Allows modifying database filenames, API endpoints, listed stocks URLs,
and default crawler parameters in a single space.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "databases")

# SQLite Database Filenames (resolved dynamically to absolute paths)
CAPITAL_MARKET_DB = os.path.join(DB_DIR, "capital_market.db")
DERIVATIVES_MARKET_DB = os.path.join(DB_DIR, "derivatives_market.db")
STOCK_DATA_DB = os.path.join(DB_DIR, "stock_data.db")
CORPORATE_DB = os.path.join(DB_DIR, "corporate_announcements.db")
OPTION_CHAIN_DB = os.path.join(DB_DIR, "option_chain.db")

# New Data Sources and Feature Store
FEATURE_STORE_DB = os.path.join(DB_DIR, "feature_store.db")
BSE_DEALS_DB = os.path.join(DB_DIR, "bse_deals.db")
MACRO_DATA_DB = os.path.join(DB_DIR, "macro_data.db")
SENTIMENT_DB = os.path.join(DB_DIR, "sentiment.db")
FUNDAMENTALS_DB = os.path.join(DB_DIR, "fundamentals.db")
INSTITUTIONAL_DB = os.path.join(DB_DIR, "institutional.db")
MARKET_BREADTH_DB = os.path.join(DB_DIR, "market_breadth.db")
MICROSTRUCTURE_DB = os.path.join(DB_DIR, "microstructure.db")

# API Endpoints and Source Data URLs
EQUITY_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
CORP_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
OPTION_CHAIN_V3_URL = "https://www.nseindia.com/api/option-chain-v3"

# Index Symbols for Option Chain Downloader
OPTION_CHAIN_INDEX_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

# Defaults for Crawler & Concurrency
DEFAULT_CRAWLER_WORKERS = 5
DEFAULT_HISTORY_YEARS = 1
DEFAULT_REQUEST_DELAY = 0.5  # delay in seconds between calls

# Mapping of index codes to nselib lookup strings for historical index downloader
INDEX_HISTORY_MAPPING = {
    "NIFTY": "Nifty 50",
    "BANKNIFTY": "Nifty BANK",
    "FINNIFTY": "Nifty FINANCIAL SERVICES",
    "MIDCPNIFTY": "Nifty MIDCAP SELECT"
}
