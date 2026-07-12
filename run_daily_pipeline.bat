@echo off
:: NSE Market Data Daily Pipeline Runner
:: Executes the full data ingestion, feature store build, and AI prediction sequence.

echo ============================================
echo   NSE Daily Data Pipeline
echo ============================================
echo.

set NSE_ROOT=d:\badri\vs code\google_work\nse

pushd "%NSE_ROOT%"
echo Starting scheduler.py...
python scripts\scheduler.py
popd

echo.
echo ============================================
echo   Pipeline Finished!
echo ============================================
pause
