from fastapi import FastAPI, UploadFile, File, HTTPException, Form
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
from datetime import datetime, timedelta
from pydantic import BaseModel

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
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

# Create temp directory for file operations
TEMP_DIR = UPLOAD_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True, parents=True)

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

class FileInfo(BaseModel):
    filename: str
    original_name: str
    upload_time: str
    time_duration: int

# Store file information
file_info: Dict[str, FileInfo] = {}

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
    """Distribute shards to renters with replication."""
    cleanup_inactive_renters()
    
    if not renters:
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please wait for a renter to register."
        )
    
    distributed_shards = []
    for shard_index, shard_path in enumerate(shards):
        # Get renters for this shard
        shard_renters = get_renters_for_shard(shard_index, len(shards))
        
        for replica_index, renter_id in enumerate(shard_renters):
            renter = renters.get(renter_id)
            if not renter:
                logger.warning(f"Renter {renter_id} not found, skipping")
                continue
                
            shard_name = f"shard_{shard_index}_replica_{replica_index}_{filename}"
            
            try:
                # Send shard to renter
                with open(shard_path, 'rb') as f:
                    files = {'file': (shard_name, f)}
                    response = requests.post(
                        f"http://{renter['address']}:{renter['port']}/store-shard/",
                        files=files,
                        timeout=30
                    )
                    response.raise_for_status()
                
                # Store shard information
                distributed_shards.append({
                    'renter_id': renter_id,
                    'shard_path': shard_name,
                    'shard_index': shard_index,
                    'replica_index': replica_index
                })
                
                logger.info(f"Successfully sent shard {shard_name} to renter {renter_id} at {renter['address']}:{renter['port']}")
                
            except Exception as e:
                logger.error(f"Error sending shard to renter {renter_id}: {str(e)}")
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
        # Validate required fields
        required_fields = ["address", "port", "storage_available"]
        for field in required_fields:
            if field not in renter_info:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Get renter information
        address = renter_info["address"]
        port = renter_info["port"]
        storage_available = renter_info["storage_available"]
        
        # Check if renter already exists with same address and port
        for existing_id, existing_renter in renters.items():
            if existing_renter["address"] == address and existing_renter["port"] == port:
                logger.warning(f"Renter already exists with address {address} and port {port}")
                return {
                    "renter_id": existing_id,
                    "message": "Renter already registered",
                    "rack_id": existing_renter["rack_id"]
                }
        
        # Generate new renter ID
        renter_id = str(uuid.uuid4())
        
        # Store renter information
        renters[renter_id] = {
            "address": address,
            "port": port,
            "storage_available": storage_available,
            "last_heartbeat": time.time(),
            "rack_id": assign_rack(renter_id)
        }
        
        logger.info(f"Renter registered successfully with ID: {renter_id}")
        logger.info(f"Renter details: {renters[renter_id]}")
        
        return {
            "renter_id": renter_id,
            "message": "Renter registered successfully",
            "rack_id": renters[renter_id]["rack_id"]
        }
    except Exception as e:
        logger.error(f"Error registering renter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/heartbeat/")
async def receive_heartbeat(heartbeat_info: dict):
    """Receive a heartbeat from a renter."""
    try:
        # Validate required fields
        required_fields = ["renter_id", "address", "port"]
        for field in required_fields:
            if field not in heartbeat_info:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        renter_id = heartbeat_info["renter_id"]
        address = heartbeat_info["address"]
        port = heartbeat_info["port"]
        
        if renter_id not in renters:
            # If renter not found, try to register it
            return await register_renter(heartbeat_info)
        
        # Update renter information
        renters[renter_id].update({
            "last_heartbeat": time.time(),
            "address": address,
            "port": port
        })
        
        # Update storage available if provided
        if "storage_available" in heartbeat_info:
            renters[renter_id]["storage_available"] = heartbeat_info["storage_available"]
        
        logger.info(f"Heartbeat received from renter {renter_id}")
        return {"message": "Heartbeat received"}
        
    except Exception as e:
        logger.error(f"Error processing heartbeat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    time_duration: int = Form(0)
):
    try:
        # Generate a unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = TEMP_DIR / unique_filename

        # Save the uploaded file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Calculate number of shards needed
        file_size = os.path.getsize(file_path)
        num_shards = max(MIN_SHARDS, math.ceil(file_size / SHARD_SIZE))

        # Split file into shards
        shards = split_file_into_shards(file_path, num_shards)

        # Distribute shards to renters
        shard_info = distribute_shards_to_renters(shards, unique_filename)

        # Store shard locations
        shard_locations[unique_filename] = shard_info

        # Store file info
        file_info[unique_filename] = FileInfo(
            filename=unique_filename,
            original_name=file.filename,
            upload_time=datetime.now().isoformat(),
            time_duration=time_duration
        )

        # Schedule auto-retrieval if time_duration is set
        if time_duration > 0:
            asyncio.create_task(schedule_auto_retrieval(unique_filename, time_duration))

        # Clean up temporary files
        os.remove(file_path)
        for shard in shards:
            os.remove(shard)

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "filename": unique_filename,
            "original_name": file.filename,
            "shard_count": num_shards,
            "shard_info": shard_info
        }

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file by reassembling its shards."""
    if filename not in shard_locations:
        raise HTTPException(status_code=404, detail="File not found")

    # Create a temporary directory for reassembly
    temp_dir = UPLOAD_DIR / "temp" / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)

    shard_paths = []
    output_path = None
    
    try:
        # Store original filename before any deletions
        original_filename = file_info[filename].original_name

        # Download shards from renters
        for shard_info in shard_locations[filename]:
            renter_id = shard_info["renter_id"]
            renter = renters.get(renter_id)
            if not renter:
                continue

            shard_path = temp_dir / f"shard_{shard_info['shard_index']}"
            response = requests.get(
                f"http://{renter['address']}:{renter['port']}/retrieve-shard/",
                params={"filename": shard_info['shard_path']},
                timeout=30
            )
            if response.status_code == 200:
                with open(shard_path, "wb") as f:
                    f.write(response.content)
                shard_paths.append(shard_path)
                logger.info(f"Successfully downloaded shard {shard_info['shard_path']} from renter {renter_id}")

        if not shard_paths:
            raise HTTPException(status_code=404, detail="No shards available")

        # Reassemble the file
        output_path = temp_dir / filename
        with open(output_path, "wb") as outfile:
            for shard_path in sorted(shard_paths):
                with open(shard_path, "rb") as infile:
                    outfile.write(infile.read())
        logger.info(f"Successfully reassembled file {filename}")

        # Verify the file exists before returning
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Failed to create output file")

        # Delete shards from renters after successful download
        for shard_info in shard_locations[filename]:
            renter = renters.get(shard_info['renter_id'])
            if not renter:
                continue
            try:
                response = requests.post(
                    f"http://{renter['address']}:{renter['port']}/delete-shard/",
                    params={'filename': shard_info['shard_path']},
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"Deleted shard {shard_info['shard_path']} from renter {shard_info['renter_id']}")
            except Exception as e:
                logger.error(f"Error deleting shard from renter: {str(e)}")

        # Remove file from shard_locations and file_info to prevent auto-retrieval
        if filename in shard_locations:
            del shard_locations[filename]
        if filename in file_info:
            del file_info[filename]

        # Create a response with background cleanup
        response = FileResponse(
            path=str(output_path),
            filename=original_filename,
            media_type="application/octet-stream",
            background=None  # Disable background task to prevent premature cleanup
        )

        # Clean up shards but keep the output file
        for shard_path in shard_paths:
            if os.path.exists(shard_path):
                os.remove(shard_path)

        # Return the response
        return response

    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        # Clean up on error
        try:
            for shard_path in shard_paths:
                if os.path.exists(shard_path):
                    os.remove(shard_path)
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up: {str(cleanup_error)}")
        raise HTTPException(status_code=500, detail=str(e))

async def schedule_auto_retrieval(filename: str, duration_minutes: int):
    """Schedule automatic file retrieval after specified duration."""
    try:
        # Convert minutes to seconds and wait
        await asyncio.sleep(duration_minutes * 60)
        
        # Check if file still exists
        if filename not in file_info:
            logger.warning(f"File {filename} not found for auto-retrieval")
            return
            
        logger.info(f"Starting auto-retrieval for file {filename}")
        
        # Create a temporary directory for the download
        temp_dir = UPLOAD_DIR / "temp" / str(uuid.uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download shards from renters
            shard_paths = []
            for shard_info in shard_locations[filename]:
                renter_id = shard_info["renter_id"]
                renter = renters.get(renter_id)
                if not renter:
                    continue

                shard_path = temp_dir / f"shard_{shard_info['shard_index']}"
                response = requests.get(
                    f"http://{renter['address']}:{renter['port']}/retrieve-shard/",
                    params={"filename": shard_info['shard_path']},
                    timeout=30
                )
                if response.status_code == 200:
                    with open(shard_path, "wb") as f:
                        f.write(response.content)
                    shard_paths.append(shard_path)
                    logger.info(f"Successfully downloaded shard {shard_info['shard_path']} from renter {renter_id}")

            if not shard_paths:
                logger.error(f"No shards available for auto-retrieval of {filename}")
                return

            # Reassemble the file
            output_path = temp_dir / filename
            with open(output_path, "wb") as outfile:
                for shard_path in sorted(shard_paths):
                    with open(shard_path, "rb") as infile:
                        outfile.write(infile.read())
            logger.info(f"Successfully reassembled file {filename} for auto-retrieval")
            
            # Move the file to the uploads directory
            final_path = UPLOAD_DIR / file_info[filename].original_name
            shutil.move(str(output_path), str(final_path))
            logger.info(f"Successfully moved auto-retrieved file to {final_path}")
            
            # Delete shards from renters after successful auto-retrieval
            for shard_info in shard_locations[filename]:
                renter = renters.get(shard_info['renter_id'])
                if not renter:
                    continue
                try:
                    response = requests.post(
                        f"http://{renter['address']}:{renter['port']}/delete-shard/",
                        params={'filename': shard_info['shard_path']},
                        timeout=30
                    )
                    response.raise_for_status()
                    logger.info(f"Deleted shard {shard_info['shard_path']} from renter {shard_info['renter_id']}")
                except Exception as e:
                    logger.error(f"Error deleting shard from renter: {str(e)}")

            # Remove file from shard_locations and file_info
            if filename in shard_locations:
                del shard_locations[filename]
            if filename in file_info:
                del file_info[filename]
            
        finally:
            # Clean up temporary files
            try:
                for shard_path in shard_paths:
                    if os.path.exists(shard_path):
                        os.remove(shard_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temporary files during auto-retrieval: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in auto-retrieval of {filename}: {str(e)}")

@app.get("/list-files/")
async def list_files():
    """Return a list of all uploaded files with their metadata."""
    return {
        "files": [
            {
                "filename": info.filename,
                "original_name": info.original_name,
                "upload_time": info.upload_time,
                "time_duration": info.time_duration,
                "is_retrieved": filename not in shard_locations  # If file is not in shard_locations, it has been retrieved
            }
            for filename, info in file_info.items()
        ]
    }

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