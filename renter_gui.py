from logging.handlers import SYSLOG_TCP_PORT
from re import S
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os, sys
from h11 import SERVER
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
import uvicorn
from nicegui import ui
from nicegui import app as nicegui_app

version = "1.0.0"
SERVER_URL = None
STORAGE_AVAILABLE_MB = 0  # Storage space in MB
RENTER_URL = None
RENTER_ID = None
STORAGE_BLOCKER_PATH = None
HEARTBEAT_INTERVAL = 30  # seconds
STORAGE_AVAILABLE = 0  # Storage space in bytes
RENTER_PORT = 8088  # Port for the renter to listen on
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

#app = FastAPI(title="Distributed Storage Renter")
# nicegui_app.include_router(app.router)

def start_heartbeat():
    global heartbeat_thread
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

def stop_heartbeat_thread():
    stop_heartbeat.set()
    if heartbeat_thread:
        heartbeat_thread.join()
    if blockchain_conn:
        blockchain_conn.close()

# Enable CORS
nicegui_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Welcome message
print("\n=========================================")
print("\nWelcome to the Distributed Storage Renter!")
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


def submit_form():
    # Get the local IP address
    global LOCAL_IP, RENTER_URL, SERVER_URL, STORAGE_AVAILABLE_MB, STORAGE_AVAILABLE, RENTER_PORT, blockchain_conn, blockchain_address
    LOCAL_IP = get_local_ip()
    RENTER_URL = f"http://{LOCAL_IP}:{RENTER_PORT}"
    logger.info(f"Renter will be accessible at: {RENTER_URL}")

    server_input = server_url_input.value
    blockchain_url = blockchain_url_input.value
    username = username_input.value
    storage_input = space_available_input.value

    MIN_STORAGE_MB = 5

    if server_input.startswith('https://'):
        server_input = server_input.replace('https://', 'http://')
    elif not server_input.startswith('http://'):
        server_input = f"http://{server_input}"

    SERVER_URL = server_input.rstrip('/')  # Remove trailing slash if present

    # Get blockchain server URL
    if blockchain_url:
        try:
            blockchain_server_url = blockchain_url.replace('http://', '').replace('https://', '')
            if ':' in blockchain_server_url:
                blockchain_server_url, blockchain_port = blockchain_server_url.split(':')
            else:
                blockchain_port = 7575  # Default port for blockchain server
            blockchain_conn = rpyc.connect(blockchain_server_url, blockchain_port)
            logger.info(f"Connected to blockchain server at {blockchain_server_url}:{blockchain_port}")

            blockchain_address = blockchain_conn.root.exposed_create_account(username, 1000.0)
            print(f"Your blockchain address: {blockchain_address}")
            balance = blockchain_conn.root.exposed_get_balance(blockchain_address)
            print(f"Your blockchain balance: {balance}")
        except Exception as e:
            print(f"Error connecting to blockchain server: {str(e)}")
            print("\nMake sure the blockchain server is running and the IP address is correct.")
            print("Example format: 192.168.0.103 (without http:// or port number)")
            print("The blockchain server should be running on port 7575")

        try:
            if not storage_input:
                # Use minimum storage if user hits Enter
                STORAGE_AVAILABLE_MB = MIN_STORAGE_MB
                print(f"Using minimum storage space: {MIN_STORAGE_MB} MB")
                
            storage_mb = float(storage_input)
            if storage_mb <= 0:
                ui.notify("Storage space must be greater than 0. Please try again.", color="negative")
                
            if storage_mb < MIN_STORAGE_MB:
                ui.notify(f"Requested storage space is less than minimum ({MIN_STORAGE_MB} MB). Using minimum value.", color="warning")
                STORAGE_AVAILABLE_MB = MIN_STORAGE_MB
            else:
                STORAGE_AVAILABLE_MB = storage_mb
                
            print(f"Making {STORAGE_AVAILABLE_MB} MB available for storage")

        except ValueError:
            print("Please enter a valid number. Example: 10 for 10 MB")

    create_storage_blocker_file()
    register_with_server()
    start_heartbeat()

    ui.notify("Storage Renter started successfully!", color="positive")

# Create storage blocker file
def create_storage_blocker_file():
    global LOCAL_IP, RENTER_URL, SERVER_URL, STORAGE_AVAILABLE_MB, STORAGE_BLOCKER_PATH, STORAGE_AVAILABLE, RENTER_ID
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
    global RENTER_URL, SERVER_URL, STORAGE_AVAILABLE, RENTER_ID, blockchain_conn, blockchain_address
    """Register this renter with the server."""
    try:
        logger.info(f"Registering with server at {SERVER_URL}")
        logger.info(f"Renter URL: {RENTER_URL}")
        logger.info(f"Storage available: {STORAGE_AVAILABLE:,} bytes")
        
        response = requests.post(
            f"{SERVER_URL}/register-renter/",
            json={
                "renter_id": RENTER_ID,
                "url": RENTER_URL,
                "storage_available": STORAGE_AVAILABLE,
                "blockchain_address": blockchain_address if blockchain_conn else None
            }
        )
        response.raise_for_status()
        logger.info("Successfully registered with server")
    except Exception as e:
        logger.error(f"Failed to register with server: {str(e)}")

def send_heartbeat():
    global SERVER_URL, HEARTBEAT_INTERVAL, STORAGE_BLOCKER_PATH, RENTER_ID, blockchain_conn, blockchain_address
    """Send periodic heartbeat to server to maintain active status."""
    while not stop_heartbeat.is_set():
        try:
            # Check if the storage blocker file exists
            if not os.path.exists(STORAGE_BLOCKER_PATH):
                raise Exception("Storage may be unavailable.")
            response = requests.post(
                f"{SERVER_URL}/heartbeat/",
                json={
                    "renter_id": RENTER_ID,
                    "blockchain_address": blockchain_address if blockchain_conn else None
                }
            )
            response.raise_for_status()
            logger.debug("Heartbeat sent successfully")
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {str(e)}")
        time.sleep(HEARTBEAT_INTERVAL)

@nicegui_app.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Distributed Storage Renter is running",
        "renter_id": RENTER_ID,
        "renter_url": RENTER_URL,
        "blockchain_address": blockchain_address if blockchain_conn else None
    }

@nicegui_app.post("/store-shard/")
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

@nicegui_app.get("/retrieve-shard/")
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

@nicegui_app.post("/delete-shard/")
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


ui.label('Storage Renter Startup').style('font-size: 64px; font-weight: bold; color: #333;')
with ui.card():
    with ui.row():
        ui.label('Server URL:')
        server_url_input = ui.input()

    with ui.row():
        ui.label('Blockchain URL:')
        blockchain_url_input = ui.input()

    with ui.row():
        ui.label('Username:')
        username_input = ui.input()

    with ui.row():
        ui.label('Space Available (in MB):')
        space_available_input = ui.input()

    ui.button('Submit', on_click=submit_form)

ui.run(title=f"S4S Renter v{version}", dark=True, port=RENTER_PORT, reload=True, favicon='🚀')