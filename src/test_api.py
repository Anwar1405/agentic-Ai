import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import app

def run_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("\n" + "="*50)
    print("  Agriculture DSS API Server")
    print("="*50)
    print("Server running at: http://127.0.0.1:8000")
    print("\nKeep this window open while using the frontend.")
    print("Press Ctrl+C to stop the server.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped.")
