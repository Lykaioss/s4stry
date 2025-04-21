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
import rpyc

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

# Global blockchain connection
blockchain_conn = None
blockchain_address = None

def create_blockchain_account(username: str, initial_balance: float = 1000.0) -> str:
    """Create a new blockchain account."""
    try:
        if not blockchain_conn:
            raise Exception("Not connected to blockchain server")
        
        # Call the remote create_account method
        response = blockchain_conn.root.exposed_create_account(username, initial_balance)
        
        if response["status"] == "error":
            logger.error(f"Failed to create blockchain account: {response['message']}")
            raise Exception(response["message"])
        
        address = response["address"]
        logger.info(f"Created blockchain account with address: {address}")
        return address
    except Exception as e:
        logger.error(f"Failed to create blockchain account: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global blockchain_conn, blockchain_address
    
    # Connect to blockchain server if URL provided
    if blockchain_server_url:
        try:
            blockchain_conn = rpyc.connect(blockchain_server_url, 7575)
            logger.info("Connected to blockchain server")
            
            # Create blockchain account for renter
            try:
                blockchain_address = create_blockchain_account(f"renter_{get_local_ip()}")
                logger.info(f"Renter blockchain address: {blockchain_address}")
            except Exception as e:
                logger.error(f"Failed to create blockchain account: {str(e)}")
                logger.info("Continuing without blockchain functionality")
                blockchain_conn = None
        except Exception as e:
            logger.error(f"Failed to connect to blockchain server: {str(e)}")
            logger.info("Continuing without blockchain functionality")
    
    # Register with storage server
    register_with_server()
    
    # Start heartbeat thread
    global heartbeat_thread
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    
    yield
    
    # Shutdown
    stop_heartbeat.set()
    if heartbeat_thread:
        heartbeat_thread.join()
    if blockchain_conn:
        blockchain_conn.close()

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
print("Example: 192.168.1.100:8000")
server_input = input("Server URL: ").strip() or "192.168.3.46:8000"

# Ensure server URL has http:// prefix and no https://
if server_input.startswith('https://'):
    server_input = server_input.replace('https://', 'http://')
elif not server_input.startswith('http://'):
    server_input = f"http://{server_input}"

SERVER_URL = server_input.rstrip('/')  # Remove trailing slash if present

# Get blockchain server URL
blockchain_server_url = input("Enter the blockchain server URL (e.g., 192.168.1.100) [Press Enter to skip]: ").strip()
if blockchain_server_url:
    try:
        # Remove any protocol prefix and port if present
        blockchain_server_url = blockchain_server_url.replace('http://', '').replace('https://', '')
        if ':' in blockchain_server_url:
            blockchain_server_url = blockchain_server_url.split(':')[0]
        
        blockchain_conn = rpyc.connect(blockchain_server_url, 7575)
        print(f"Connected to blockchain server at {blockchain_server_url}:7575")
        
        username = input("Enter your username for blockchain account: ").strip()
        blockchain_address = blockchain_conn.root.exposed_create_account(username, 1000.0)
        print(f"Your blockchain address: {blockchain_address}")
        balance = blockchain_conn.root.exposed_get_balance(blockchain_address)
        print(f"Your blockchain balance: {balance}")
    except Exception as e:
        print(f"Error connecting to blockchain server: {str(e)}")
        print("\nMake sure the blockchain server is running and the IP address is correct.")
        print("Example format: 192.168.0.103 (without http:// or port number)")
        print("The blockchain server should be running on port 7575")

# Get the local IP address
LOCAL_IP = get_local_ip()
RENTER_URL = f"http://{LOCAL_IP}:8001"
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
            
        storage_mb = float(storage_input)
        if storage_mb <= 0:
            print("Storage space must be greater than 0. Please try again.")
            continue
            
        if storage_mb < MIN_STORAGE_MB:
            print(f"Requested storage space is less than minimum ({MIN_STORAGE_MB} MB). Using minimum value.")
            STORAGE_AVAILABLE_MB = MIN_STORAGE_MB
        else:
            STORAGE_AVAILABLE_MB = storage_mb
            
        print(f"Making {STORAGE_AVAILABLE_MB} MB available for storage")
        break
    except ValueError:
        print("Please enter a valid number. Example: 10 for 10 MB")

# Create storage blocker file
STORAGE_BLOCKER_PATH = STORAGE_DIR / "storage_blocker.bin"
try:
    # Create a file of the specified size
    with open(STORAGE_BLOCKER_PATH, 'wb') as f:
        # Write zeros to create a file of the specified size
        f.write(b'\0' * int(STORAGE_AVAILABLE_MB * 1024 * 1024))
    logger.info(f"Created storage blocker file of {STORAGE_AVAILABLE_MB} MB at {STORAGE_BLOCKER_PATH}")
except Exception as e:
    logger.error(f"Failed to create storage blocker file: {str(e)}")
    raise

# Convert MB to bytes for server registration
STORAGE_AVAILABLE = int(STORAGE_AVAILABLE_MB * 1024 * 1024)

RENTER_ID = str(uuid.uuid4())  # Unique ID for this renter
HEARTBEAT_INTERVAL = 30  # seconds

def register_with_server():
    """Register this renter with the server."""
    try:
        # Get local IP and port
        local_ip = get_local_ip()
        local_port = 8001  # Renter port
        
        # Prepare registration data
        registration_data = {
            "renter_id": str(uuid.uuid4()),
            "ip_address": local_ip,
            "port": local_port,
            "blockchain_address": str(blockchain_address) if blockchain_address else None,  # Convert to string if exists
            "storage_available": STORAGE_AVAILABLE
        }
        
        # Send registration request
        response = requests.post(
            f"{SERVER_URL}/register-renter/",
            json=registration_data
        )
        response.raise_for_status()
        
        logger.info(f"Successfully registered with server at {SERVER_URL}")
        logger.info(f"Renter ID: {registration_data['renter_id']}")
        logger.info(f"IP Address: {local_ip}")
        logger.info(f"Port: {local_port}")
        if blockchain_address:
            logger.info(f"Blockchain Address: {blockchain_address}")
    except Exception as e:
        logger.error(f"Failed to register with server: {str(e)}")
        raise

def send_heartbeat():
    """Send periodic heartbeat to server to maintain active status."""
    while not stop_heartbeat.is_set():
        try:
            heartbeat_data = {
                "renter_id": RENTER_ID,
                "blockchain_address": str(blockchain_address) if blockchain_address else None,
                "storage_available": STORAGE_AVAILABLE
            }
            
            response = requests.post(
                f"{SERVER_URL}/heartbeat/",
                json=heartbeat_data
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
        "renter_url": RENTER_URL,
        "blockchain_address": blockchain_address if blockchain_conn else None
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