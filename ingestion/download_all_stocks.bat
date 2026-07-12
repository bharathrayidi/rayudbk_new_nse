@echo off
:: NSE Stock Data Downloader - All Listed Stocks
:: Downloads historical price + announcements for ALL NSE listed stocks
:: WARNING: This can take several hours (2000+ stocks)
:: Run during market hours or after hours; uses 10 parallel workers

cd /d "d:\badri\vs code\google_work\nse\ingestion"

echo ====================================================
echo  NSE Full Stock History Downloader (ALL Stocks)
echo ====================================================
echo  Mode   : Full NSE listed stocks (~2000+ symbols)
echo  History: 1 year
echo  Workers: 10 parallel threads
echo  DB     : ..\databases\stock_data.db
echo ====================================================
echo.
echo Starting download... (press Ctrl+C to cancel)
echo.

python stock_downloader.py --all --years 1 --workers 10

echo.
echo === Stock History Download Complete! ===
echo Check ..\databases\stock_data.db for results.
pause
