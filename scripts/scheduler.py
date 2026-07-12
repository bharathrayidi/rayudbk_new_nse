import os
import sys
import subprocess
import time

def run_script(script_path, args=None, cwd=None):
    print(f"\n[{time.strftime('%X')}] Running {os.path.basename(script_path)}...")
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    try:
        if cwd:
            subprocess.run(cmd, cwd=cwd, check=True)
        else:
            subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
        return False
        # Not stopping the whole pipeline for one failure

def main():
    print("============================================")
    print(" NSE Daily Data Pipeline & AI Scheduler")
    print("============================================")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ingestion_dir = os.path.join(root_dir, "ingestion")
    
    if ingestion_dir not in sys.path:
        sys.path.insert(0, ingestion_dir)
    try:
        import sync_log
    except ImportError:
        sync_log = None
    
    # 1. Run all core market data downloaders
    print("\n--- Phase 1: Core Market Data & Announcements ---")
    core_sources = [
        ("capital_market.py", []),
        ("derivatives_market.py", []),
        ("option_chain_downloader.py", []),
        ("stock_downloader.py", ["--all", "--years", "1", "--workers", "10"]),
        ("index_downloader.py", ["--years", "1"])
    ]
    for source, args in core_sources:
        script_path = os.path.join(ingestion_dir, source)
        if os.path.exists(script_path):
            if sync_log and sync_log.is_updated_today(source):
                print(f"\n[{time.strftime('%X')}] Skipping {source} - Already updated today.")
                continue
                
            success = run_script(script_path, args=args, cwd=ingestion_dir)
            
            if sync_log and success:
                sync_log.mark_updated_today(source)
            
    # 2. Run all new ingestion sources
    new_sources = [
        "bse_deals_downloader.py",
        "institutional_flows.py",
        "market_breadth_vix.py",
        "fundamentals_scraper.py",
        "social_sentiment.py",
        "macro_data_rbi.py",
        "broker_microstructure.py"
    ]
    
    print("\n--- Phase 2: Ingesting Alternative Data & APIs ---")
    for source in new_sources:
        script_path = os.path.join(ingestion_dir, source)
        if os.path.exists(script_path):
            if sync_log and sync_log.is_updated_today(source):
                print(f"\n[{time.strftime('%X')}] Skipping {source} - Already updated today.")
                continue
                
            success = run_script(script_path, cwd=ingestion_dir)
            
            if sync_log and success:
                sync_log.mark_updated_today(source)
            
    # 3. Build Feature Store
    print("\n--- Phase 3: Building Feature Store ---")
    fs_script = os.path.join(ingestion_dir, "feature_store.py")
    if os.path.exists(fs_script):
        if sync_log and sync_log.is_updated_today("feature_store.py"):
            print(f"\n[{time.strftime('%X')}] Skipping feature_store.py - Already updated today.")
        else:
            success = run_script(fs_script, cwd=ingestion_dir)
            if sync_log and success:
                sync_log.mark_updated_today("feature_store.py")
        
    # 4. Run ML Predictor (v2)
    print("\n--- Phase 4: Training/Evaluating ML Ensemble ---")
    ml_script = os.path.join(root_dir, os.path.join("ml", "ml_predictor.py"))
    if os.path.exists(ml_script):
        if sync_log and sync_log.is_updated_today("ml_predictor.py"):
            print(f"\n[{time.strftime('%X')}] Skipping ml_predictor.py - Already run today.")
        else:
            print("Note: This step may take several minutes if evaluating the full database.")
            success = run_script(ml_script, cwd=root_dir)
            if sync_log and success:
                sync_log.mark_updated_today("ml_predictor.py")
        
    print("\n============================================")
    print(f" [{time.strftime('%X')}] Pipeline Execution Complete!")
    print("============================================")

if __name__ == "__main__":
    main()
