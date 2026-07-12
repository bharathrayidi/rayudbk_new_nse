@echo off
:: Central script to execute all NSE Market Data Collectors sequentially
cd /d "d:\badri\vs code\google_work\nse\ingestion"

echo === Starting NSE Capital Market Data Collector ===
python capital_market.py

echo === Starting NSE Derivatives Market Data Collector ===
python derivatives_market.py

echo === Starting NSE Index Option Chain Downloader ===
python option_chain_downloader.py

echo === Starting NSE Stock and Announcements Downloader ===
python stock_downloader.py --all --years 1 --workers 10

echo === Starting NSE Index History Downloader ===
python index_downloader.py --years 1

echo === Data Collection Complete! ===
