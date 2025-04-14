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
from datetime import datetime

# Set up basic console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Create base renter directory
BASE_DIR = Path("S4S_Renter")
BASE_DIR.mkdir(exist_ok=True)

# Create storage directory
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Storage directory: {STORAGE_DIR}")

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
RENTER_PORT = 8001  # Default port for renter
RENTER_URL = f"http://{LOCAL_IP}:{RENTER_PORT}"
logger.info(f"Renter will be accessible at: {RENTER_URL}")

# Storage configuration
MIN_STORAGE_MB = 5  # Minimum storage space in MB

# Get available storage space from user
while True:
    try:
        storage_input = input(f"\nEnter the amount of storage space you want to make available (in MB, minimum {MIN_STORAGE_MB} MB) [Press Enter for minimum]: ").strip()
        
        if not storage_input:
            # Use minimum storage if user hits Enter
            STORAGE_AVAILABLE_MB = MIN_STORAGE_MB
            print(f"Using minimum storage space: {MIN_STORAGE_MB} MB")
            break
            
        storage_available = int(storage_input)
        if storage_available < MIN_STORAGE_MB:
            print(f"Storage space must be at least {MIN_STORAGE_MB} MB")
            continue
        STORAGE_AVAILABLE_MB = storage_available
        break
    except ValueError:
        print("Please enter a valid number")

# Convert MB to bytes
STORAGE_AVAILABLE = STORAGE_AVAILABLE_MB * 1024 * 1024

# Global variables
renter_id = None

def register_with_server():
    """Register this renter with the main server."""
    global renter_id
    try:
        # Format the renter information
        renter_info = {
            "address": LOCAL_IP,
            "port": RENTER_PORT,
            "storage_available": STORAGE_AVAILABLE
        }
        
        logger.info(f"Registering with server at {SERVER_URL}")
        logger.info(f"Renter info: {renter_info}")
        
        response = requests.post(
            f"{SERVER_URL}/register-renter/",
            json=renter_info,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        renter_id = data["renter_id"]
        logger.info(f"Successfully registered with server. Renter ID: {renter_id}")
        logger.info(f"Renter details: {data}")
        
    except Exception as e:
        logger.error(f"Error registering with server: {str(e)}")
        raise

def send_heartbeat():
    """Send periodic heartbeats to the server."""
    while not stop_heartbeat.is_set():
        try:
            if renter_id:
                heartbeat_info = {
                    "renter_id": renter_id,
                    "address": LOCAL_IP,
                    "port": RENTER_PORT,
                    "storage_available": STORAGE_AVAILABLE
                }
                
                response = requests.post(
                    f"{SERVER_URL}/heartbeat/",
                    json=heartbeat_info,
                    timeout=30
                )
                response.raise_for_status()
                logger.info("Heartbeat sent successfully")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {str(e)}")
        time.sleep(30)  # Send heartbeat every 30 seconds

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Distributed Storage Renter is running",
        "renter_id": renter_id,
        "renter_url": RENTER_URL
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Renter is running"}

@app.post("/store-shard/")
async def store_shard(file: UploadFile = File(...)):
    """Store a shard of a file."""
    try:
        # Create storage directory if it doesn't exist
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
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