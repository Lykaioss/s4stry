from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import requests
from pathlib import Path
import json
from typing import Dict, List
import uuid
import logging
import threading
import time
import socket
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for the heartbeat thread
heartbeat_thread = None
stop_heartbeat = threading.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    register_with_server()
    global heartbeat_thread
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    yield
    # Shutdown
    stop_heartbeat.set()
    if heartbeat_thread:
        heartbeat_thread.join()

app = FastAPI(title="Distributed Storage Renter", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory if it doesn't exist
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)

# Server configuration
def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Try to get the IP address that can reach the internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.info(f"Detected local IP: {local_ip}")
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {str(e)}")
        # Fallback to localhost
        return "127.0.0.1"

# Get the server IP from user input
print("\nWelcome to the Distributed Storage Renter!")
print("Please enter the IP address of the server machine")
print("Example: http://192.168.1.100:8000")
SERVER_URL = input("Server URL: ").strip()

# Get the local IP address
LOCAL_IP = get_local_ip()
RENTER_URL = f"http://{LOCAL_IP}:8001"
logger.info(f"Renter will be accessible at: {RENTER_URL}")

RENTER_ID = str(uuid.uuid4())  # Unique ID for this renter
HEARTBEAT_INTERVAL = 30  # seconds

def register_with_server():
    """Register this renter with the server."""
    try:
        logger.info(f"Registering with server at {SERVER_URL}")
        logger.info(f"Renter URL: {RENTER_URL}")
        
        response = requests.post(
            f"{SERVER_URL}/register-renter/",
            json={
                "renter_id": RENTER_ID,
                "url": RENTER_URL,
                "storage_available": 1000000000  # 1GB in bytes
            }
        )
        response.raise_for_status()
        logger.info("Successfully registered with server")
    except Exception as e:
        logger.error(f"Failed to register with server: {str(e)}")

def send_heartbeat():
    """Send periodic heartbeat to server to maintain active status."""
    while not stop_heartbeat.is_set():
        try:
            response = requests.post(
                f"{SERVER_URL}/heartbeat/",
                json={"renter_id": RENTER_ID}
            )
            response.raise_for_status()
            logger.debug("Heartbeat sent successfully")
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {str(e)}")
        time.sleep(HEARTBEAT_INTERVAL)

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Distributed Storage Renter is running",
        "renter_id": RENTER_ID,
        "renter_url": RENTER_URL
    }

@app.post("/store-shard/")
async def store_shard(file: UploadFile = File(...)):
    """Store a shard of a file."""
    try:
        file_path = STORAGE_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Stored shard: {file.filename}")
        return {"message": "Shard stored successfully", "filename": file.filename}
    except Exception as e:
        logger.error(f"Error storing shard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/retrieve-shard/")
async def retrieve_shard(filename: str):
    """Retrieve a shard of a file."""
    try:
        file_path = STORAGE_DIR / filename
        if not file_path.exists():
            logger.error(f"Shard not found: {filename}")
            raise HTTPException(status_code=404, detail="Shard not found")
        logger.info(f"Retrieved shard: {filename}")
        return FileResponse(path=file_path, filename=filename)
    except Exception as e:
        logger.error(f"Error retrieving shard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-shard/")
async def delete_shard(filename: str):
    """Delete a shard from the renter's storage."""
    try:
        file_path = STORAGE_DIR / filename
        if not file_path.exists():
            logger.error(f"Shard not found: {filename}")
            raise HTTPException(status_code=404, detail="Shard not found")
        
        # Delete the shard file
        os.remove(file_path)
        logger.info(f"Deleted shard: {filename}")
        
        return {"message": f"Shard '{filename}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting shard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Run on all network interfaces
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info") 