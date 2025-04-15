from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import requests
from pathlib import Path
import json
from typing import Dict, List, Set
import uuid
import logging
import math
import time
from collections import defaultdict
import random
import socket
import asyncio
from blockchain import router as blockchain_router
from blockchain import Blockchain, Wallet, Miner, Transaction
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize blockchain components
blockchain = Blockchain.load_from_file()
wallet = Wallet(blockchain)
miner = Miner(blockchain, wallet)

app = FastAPI(title="S4S File Sharing with Sabudhana Blockchain")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Store information about registered renters
renters: Dict[str, dict] = {}

# Store information about registered clients
clients: Dict[str, dict] = {}

# Store information about file shards
shard_locations: Dict[str, List[dict]] = {}

# Store rack information
racks: Dict[str, Set[str]] = defaultdict(set)  # rack_id -> set of renter_ids

# Sharding configuration
SHARD_SIZE = 1024 * 1024  # 1MB per shard
MIN_SHARDS = 3  # Minimum number of shards to create
REPLICATION_FACTOR = 3  # Number of copies for each shard
RACK_COUNT = 3  # Number of racks in the system

# Renter management
RENTER_TIMEOUT = 60  # seconds

# Include blockchain router
app.include_router(blockchain_router, prefix="/blockchain")

def assign_rack(renter_id: str) -> str:
    """Assign a renter to a rack."""
    # Simple round-robin rack assignment
    rack_id = str(len(renters) % RACK_COUNT)
    racks[rack_id].add(renter_id)
    return rack_id

def cleanup_inactive_renters():
    """Remove renters that haven't sent a heartbeat recently."""
    current_time = time.time()
    inactive_renters = [
        renter_id for renter_id, renter in renters.items()
        if current_time - renter.get('last_heartbeat', 0) > RENTER_TIMEOUT
    ]
    for renter_id in inactive_renters:
        logger.info(f"Removing inactive renter: {renter_id}")
        # Remove from rack
        for rack_id, renter_set in racks.items():
            if renter_id in renter_set:
                renter_set.remove(renter_id)
        # Remove from renters
        del renters[renter_id]

def get_renters_for_shard(shard_index: int, num_shards: int) -> List[str]:
    """Get a list of renters to store a shard and its replicas."""
    cleanup_inactive_renters()
    
    if not renters:
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please wait for a renter to register."
        )
    
    # Get all available renters
    available_renters = list(renters.keys())
    
    # Adjust replication factor based on available renters
    actual_replication = min(REPLICATION_FACTOR, len(available_renters))
    if actual_replication < REPLICATION_FACTOR:
        logger.warning(f"Reducing replication factor from {REPLICATION_FACTOR} to {actual_replication} due to limited renters")
    
    # Select renters from different racks
    selected_renters = []
    used_racks = set()
    
    # First, try to select renters from different racks
    for rack_id, renter_set in racks.items():
        if len(selected_renters) >= actual_replication:
            break
        available_in_rack = [r for r in renter_set if r in available_renters and r not in selected_renters]
        if available_in_rack and rack_id not in used_racks:
            selected_renters.append(random.choice(available_in_rack))
            used_racks.add(rack_id)
    
    # If we still need more renters, select from any rack
    while len(selected_renters) < actual_replication:
        remaining_renters = [r for r in available_renters if r not in selected_renters]
        if not remaining_renters:
            break
        selected_renters.append(random.choice(remaining_renters))
    
    return selected_renters

def split_file_into_shards(file_path: Path, num_shards: int) -> List[Path]:
    """Split a file into multiple shards."""
    shards = []
    file_size = os.path.getsize(file_path)
    shard_size = math.ceil(file_size / num_shards)
    
    with open(file_path, 'rb') as f:
        for i in range(num_shards):
            shard_path = UPLOAD_DIR / f"shard_{i}_{file_path.name}"
            with open(shard_path, 'wb') as shard_file:
                shard_file.write(f.read(shard_size))
            shards.append(shard_path)
    
    return shards

def distribute_shards_to_renters(shards: List[Path], filename: str, client_id: str) -> List[dict]:
    """Distribute shards and their replicas across renters."""
    distributed_shards = []
    num_shards = len(shards)
    
    for i, shard_path in enumerate(shards):
        # Get renters for this shard and its replicas
        shard_renters = get_renters_for_shard(i, num_shards)
        
        for replica_index, renter_id in enumerate(shard_renters):
            renter = renters[renter_id]
            shard_name = f"shard_{i}_replica_{replica_index}_{filename}"
            
            try:
                # Create storage contract for this shard
                contract_id = wallet.create_storage_contract(
                    client_id,
                    renter_id,
                    os.path.getsize(shard_path),
                    3600  # 1 hour duration
                )
                
                if not contract_id:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create storage contract"
                    )
                
                with open(shard_path, 'rb') as f:
                    files = {"file": (shard_name, f)}
                    response = requests.post(
                        f"{renter['url']}/store-shard/",
                        files=files,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    # Store shard information with contract ID
                    shard_info = {
                        'shard_path': shard_name,
                        'renter_id': renter_id,
                        'contract_id': contract_id
                    }
                    distributed_shards.append(shard_info)
                    
                    logger.info(f"Stored shard {shard_name} with renter {renter_id} and contract {contract_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error sending shard to renter: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send shard to renter: {str(e)}"
                )
    
    return distributed_shards

@app.get("/")
async def root():
    return {
        "message": "Welcome to S4S File Sharing with Sabudhana Blockchain",
        "status": "running",
        "blockchain": {
            "height": len(blockchain.chain),
            "pending_transactions": len(blockchain.pending_transactions),
            "is_valid": blockchain.is_chain_valid()
        }
    }

@app.post("/register-renter/")
async def register_renter(renter_info: dict):
    """Register a new renter and create a blockchain account."""
    try:
        renter_id = renter_info.get("renter_id", str(uuid.uuid4()))
        
        # Create blockchain account for renter
        try:
            address = wallet.create_account(renter_id)
            # Add initial balance of 1000 sabudhana
            initial_tx = Transaction(
                "SYSTEM",
                address,
                1000.0,
                time.time(),
                {"type": "initial_balance", "user_type": "renter"}
            )
            blockchain.add_transaction(initial_tx)
            print(f"Created blockchain account for renter {renter_id}: {address}")
        except ValueError as e:
            print(f"Error creating blockchain account for renter: {e}")
        
        renters[renter_id] = {
            "url": renter_info["url"],
            "storage_available": renter_info["storage_available"],
            "last_heartbeat": time.time(),
            "rack_id": assign_rack(renter_id),
            "blockchain_address": address
        }
        logger.info(f"Renter registered successfully with ID: {renter_id} in rack {renters[renter_id]['rack_id']}")
        return {
            "renter_id": renter_id,
            "blockchain_address": address,
            "message": "Renter registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering renter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register-client/")
async def register_client(client_info: dict):
    """Register a new client and create a blockchain account."""
    try:
        client_id = client_info.get("client_id", str(uuid.uuid4()))
        
        # Create blockchain account for client
        try:
            address = wallet.create_account(client_id)
            # Add initial balance of 1000 sabudhana
            initial_tx = Transaction(
                "SYSTEM",
                address,
                1000.0,
                time.time(),
                {"type": "initial_balance", "user_type": "client"}
            )
            blockchain.add_transaction(initial_tx)
            blockchain.mine_pending_transactions()  # Mine the transaction immediately
            print(f"Created blockchain account for client {client_id}: {address}")
        except ValueError as e:
            print(f"Error creating blockchain account for client: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        clients[client_id] = {
            "blockchain_address": address,
            "last_activity": time.time()
        }
        logger.info(f"Client registered successfully with ID: {client_id}")
        return {
            "client_id": client_id,
            "blockchain_address": address,
            "message": "Client registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering client: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/heartbeat/")
async def receive_heartbeat(heartbeat_info: dict):
    """Receive a heartbeat from a renter."""
    try:
        renter_id = heartbeat_info["renter_id"]
        if renter_id in renters:
            renters[renter_id]["last_heartbeat"] = time.time()
            return {"message": "Heartbeat received"}
        else:
            raise HTTPException(status_code=404, detail="Renter not found")
    except Exception as e:
        logger.error(f"Error processing heartbeat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), client_id: str = None):
    """Upload a file and create storage contracts with renters."""
    cleanup_inactive_renters()
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Client ID is required")
    
    if client_id not in clients:
        raise HTTPException(status_code=404, detail="Client not found")
    
    logger.info(f"Starting upload process for file: {file.filename}")
    logger.info(f"Current renters: {renters}")
    
    if not renters:
        logger.error("No renters available")
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please wait for a renter to register."
        )
    
    temp_path = None
    shards = []
    try:
        # Save the uploaded file temporarily
        temp_path = UPLOAD_DIR / file.filename
        logger.info(f"Saving uploaded file temporarily to: {temp_path}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Calculate number of shards based on file size
        file_size = os.path.getsize(temp_path)
        num_shards = max(MIN_SHARDS, math.ceil(file_size / SHARD_SIZE))
        
        # Calculate actual replication factor based on available renters
        actual_replication = min(REPLICATION_FACTOR, len(renters))
        logger.info(f"Splitting file into {num_shards} shards with replication factor {actual_replication}")
        
        # Split file into shards
        shards = split_file_into_shards(temp_path, num_shards)
        logger.info(f"Created {len(shards)} shards")
        
        # Create storage contracts and distribute shards
        distributed_shards = distribute_shards_to_renters(shards, file.filename, client_id)
        
        # Store shard locations
        shard_locations[file.filename] = distributed_shards
        
        # Clean up temporary files
        try:
            os.remove(temp_path)
            for shard in shards:
                if os.path.exists(shard):
                    os.remove(shard)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "num_shards": num_shards,
            "replication_factor": actual_replication,
            "contracts": [shard["contract_id"] for shard in distributed_shards]
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        # Clean up on error
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        for shard in shards:
            if os.path.exists(shard):
                try:
                    os.remove(shard)
                except:
                    pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str, client_id: str):
    """Download a file and release payments to renters."""
    try:
        if filename not in shard_locations:
            raise HTTPException(status_code=404, detail="File not found")
            
        if client_id not in clients:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create a temporary file for reconstruction
        temp_file = UPLOAD_DIR / f"reconstructed_{filename}"
        
        # Reconstruct the file from shards
        with open(temp_file, 'wb') as reconstructed_file:
            shards = shard_locations[filename]
            
            for shard in shards:
                renter = renters.get(shard['renter_id'])
                if not renter:
                    continue
                
                try:
                    response = requests.get(
                        f"{renter['url']}/retrieve-shard/",
                        params={'filename': shard['shard_path']},
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    reconstructed_file.write(response.content)
                    
                    # Release payment for this shard using the contract ID
                    if 'contract_id' in shard:
                        try:
                            wallet.release_payment(shard['contract_id'])
                            # Mine the payment transaction immediately
                            blockchain.mine_pending_transactions()
                            logger.info(f"Released payment for contract: {shard['contract_id']}")
                        except Exception as e:
                            logger.error(f"Error releasing payment: {str(e)}")
                            # Continue with download even if payment fails
                    
                except Exception as e:
                    logger.error(f"Error retrieving shard from renter: {str(e)}")
                    continue
        
        # Schedule file deletion after 30 seconds
        asyncio.create_task(delete_temp_file_after_delay(temp_file, 30))
        
        return FileResponse(
            path=temp_file,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def delete_temp_file_after_delay(file_path: Path, delay_seconds: int):
    """Delete a temporary file after a specified delay."""
    try:
        await asyncio.sleep(delay_seconds)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting temporary file {file_path}: {str(e)}")

@app.post("/delete/{filename}")
async def delete_file(filename: str):
    """Delete a file and its shards from all renters."""
    cleanup_inactive_renters()
    
    if filename not in shard_locations:
        logger.error(f"File not found: {filename}")
        raise HTTPException(
            status_code=404, 
            detail=f"File '{filename}' not found."
        )
    
    try:
        # Delete shards from all renters
        for shard_info in shard_locations[filename]:
            renter = renters.get(shard_info['renter_id'])
            if not renter:
                continue
            try:
                response = requests.post(
                    f"{renter['url']}/delete-shard/",
                    params={'filename': shard_info['shard_path']},
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"Deleted shard {shard_info['shard_path']} from renter {shard_info['renter_id']}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error deleting shard from renter: {str(e)}")
        
        # Remove file from shard_locations
        del shard_locations[filename]
        
        return {"message": f"File '{filename}' and all its shards deleted successfully"}
    except Exception as e:
        logger.error(f"Error in delete process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Try to get the IP address that can reach the internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback to localhost
        return "127.0.0.1"

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("\nDistributed Storage Server is starting...")
    print(f"Server will be accessible at:")
    print(f"Local: http://localhost:8000")
    print(f"Network: http://{local_ip}:8000")
    print("\nPress Ctrl+C to stop the server")
    uvicorn.run(app, host="0.0.0.0", port=8000) 