import subprocess
import os
import time
import webbrowser

# Define paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(root_dir, "frontend")

print("============================================")
print(" NSE Market Intelligence Dashboard Launcher")
print("============================================")
print("Starting servers...\n")

# Start Backend
print("[1/2] Starting FastAPI backend on http://localhost:8000 ...")
backend_process = subprocess.Popen(
    ["python", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
    cwd=root_dir
)

time.sleep(3) # Wait for backend to initialize

# Start Frontend
print("[2/2] Starting Vite frontend on http://localhost:5180 ...")
# Use shell=True for npm to work correctly on Windows
frontend_process = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=frontend_dir,
    shell=True
)

time.sleep(2)

print("\n============================================")
print(" Servers are running!")
print(" Backend:  http://localhost:8000/docs")
print(" Frontend: http://localhost:5180")
print("============================================\n")

print("Opening dashboard in your browser...")
webbrowser.open("http://localhost:5180")

print("\nPress Ctrl+C to stop both servers.")

try:
    # Keep the script running so the child processes stay alive
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping servers...")
    backend_process.terminate()
    frontend_process.terminate()
    print("Servers stopped.")
