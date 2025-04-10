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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Distributed Storage Renter")

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
SERVER_URL = "http://localhost:8000"  # Default server URL
RENTER_ID = str(uuid.uuid4())  # Unique ID for this renter
HEARTBEAT_INTERVAL = 30  # seconds

def register_with_server():
    """Register this renter with the server."""
    try:
        response = requests.post(
            f"{SERVER_URL}/register-renter/",
            json={
                "renter_id": RENTER_ID,
                "url": f"http://localhost:8001",  # This will be updated with actual IP
                "storage_available": 1000000000  # 1GB in bytes
            }
        )
        response.raise_for_status()
        logger.info("Successfully registered with server")
    except Exception as e:
        logger.error(f"Failed to register with server: {str(e)}")

def send_heartbeat():
    """Send periodic heartbeat to server to maintain active status."""
    while True:
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

@app.on_event("startup")
async def startup_event():
    """Register with server and start heartbeat thread on startup."""
    register_with_server()
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Distributed Storage Renter is running"}

@app.post("/store-shard/")
async def store_shard(file: UploadFile = File(...)):
    """Store a shard of a file."""
    try:
        file_path = STORAGE_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
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
            raise HTTPException(status_code=404, detail="Shard not found")
        return FileResponse(path=file_path, filename=filename)
    except Exception as e:
        logger.error(f"Error retrieving shard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 