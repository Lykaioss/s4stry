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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Distributed Storage Server")

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

def distribute_shards_to_renters(shards: List[Path], filename: str) -> List[dict]:
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
                with open(shard_path, 'rb') as f:
                    files = {"file": (shard_name, f)}
                    response = requests.post(
                        f"{renter['url']}/store-shard/",
                        files=files,
                        timeout=30
                    )
                    response.raise_for_status()
                
                distributed_shards.append({
                    "renter_id": renter_id,
                    "shard_path": shard_name,
                    "shard_index": i,
                    "replica_index": replica_index
                })
            except requests.exceptions.RequestException as e:
                logger.error(f"Error sending shard to renter: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send shard to renter: {str(e)}"
                )
    
    return distributed_shards

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Distributed Storage Server is running"}

@app.post("/register-renter/")
async def register_renter(renter_info: dict):
    """Register a new renter."""
    try:
        renter_id = renter_info.get("renter_id", str(uuid.uuid4()))
        renters[renter_id] = {
            "url": renter_info["url"],
            "storage_available": renter_info["storage_available"],
            "last_heartbeat": time.time(),
            "rack_id": assign_rack(renter_id)
        }
        logger.info(f"Renter registered successfully with ID: {renter_id} in rack {renters[renter_id]['rack_id']}")
        return {"renter_id": renter_id, "message": "Renter registered successfully"}
    except Exception as e:
        logger.error(f"Error registering renter: {str(e)}")
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
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and distribute it across renters with replication."""
    cleanup_inactive_renters()
    
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
        
        # Distribute shards to renters with replication
        logger.info("Starting shard distribution to renters")
        distributed_shards = distribute_shards_to_renters(shards, file.filename)
        logger.info(f"Successfully distributed shards: {distributed_shards}")
        
        # Store shard information
        shard_locations[file.filename] = distributed_shards
        
        return {
            "filename": file.filename,
            "num_shards": num_shards,
            "replication_factor": actual_replication,
            "shard_size": SHARD_SIZE,
            "message": f"File uploaded and distributed successfully with replication factor {actual_replication}"
        }
    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file {temp_path}: {str(e)}")
        
        for shard in shards:
            if os.path.exists(shard):
                try:
                    os.remove(shard)
                    logger.info(f"Cleaned up shard: {shard}")
                except Exception as e:
                    logger.error(f"Error cleaning up shard {shard}: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file by retrieving and reconstructing its shards."""
    try:
        # Check if file exists in our records
        if filename not in shard_locations:
            raise HTTPException(status_code=404, detail="File not found")

        # Create a temporary file for reconstruction
        temp_file = UPLOAD_DIR / f"reconstructed_{filename}"
        
        # Reconstruct the file from shards
        with open(temp_file, 'wb') as reconstructed_file:
            # Get all shards for this file
            shards = shard_locations[filename]
            
            # Sort shards by shard_index and replica_index
            shards.sort(key=lambda x: (x['shard_index'], x['replica_index']))
            
            # Track which shards we've successfully retrieved
            retrieved_shards = set()
            
            # Try to get each shard from its renters
            for shard in shards:
                shard_index = shard['shard_index']
                if shard_index in retrieved_shards:
                    continue
                
                renter_id = shard['renter_id']
                renter = renters.get(renter_id)
                
                if not renter:
                    logger.warning(f"Renter {renter_id} not found, trying next replica")
                    continue
                
                try:
                    # Request shard from renter
                    renter_url = renter['url']
                    if not renter_url.startswith('http'):
                        renter_url = f"http://{renter_url}"
                    
                    response = requests.get(
                        f"{renter_url}/retrieve-shard/",
                        params={'filename': shard['shard_path']},
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    # Write shard to reconstructed file
                    reconstructed_file.write(response.content)
                    retrieved_shards.add(shard_index)
                    logger.info(f"Successfully retrieved shard {shard['shard_path']} from renter {renter_id}")
                    
                except Exception as e:
                    logger.error(f"Error retrieving shard from renter {renter_id}: {str(e)}")
                    continue
            
            # Check if we got all shards
            if len(retrieved_shards) != len(set(s['shard_index'] for s in shards)):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve all shards"
                )

        # Schedule file deletion after 30 seconds
        asyncio.create_task(delete_temp_file_after_delay(temp_file, 30))

        # Return the reconstructed file
        return FileResponse(
            path=temp_file,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )

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