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
import math
import time

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

# Sharding configuration
SHARD_SIZE = 1024 * 1024  # 1MB per shard
MIN_SHARDS = 3  # Minimum number of shards to create

# Renter management
RENTER_TIMEOUT = 60  # seconds

def cleanup_inactive_renters():
    """Remove renters that haven't sent a heartbeat recently."""
    current_time = time.time()
    inactive_renters = [
        renter_id for renter_id, renter in renters.items()
        if current_time - renter.get('last_heartbeat', 0) > RENTER_TIMEOUT
    ]
    for renter_id in inactive_renters:
        logger.info(f"Removing inactive renter: {renter_id}")
        del renters[renter_id]

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
    """Distribute shards across available renters."""
    cleanup_inactive_renters()
    
    if not renters:
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please wait for a renter to register."
        )
    
    distributed_shards = []
    renter_ids = list(renters.keys())
    num_renters = len(renter_ids)
    
    for i, shard_path in enumerate(shards):
        renter_id = renter_ids[i % num_renters]  # Round-robin distribution
        renter = renters[renter_id]
        
        try:
            with open(shard_path, 'rb') as f:
                files = {"file": (shard_path.name, f)}
                response = requests.post(
                    f"{renter['url']}/store-shard/",
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
                
                distributed_shards.append({
                    "renter_id": renter_id,
                    "shard_path": shard_path.name,
                    "shard_index": i
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
            "last_heartbeat": time.time()
        }
        logger.info(f"Renter registered successfully with ID: {renter_id}")
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
    """Upload a file and distribute it across renters."""
    cleanup_inactive_renters()
    
    if not renters:
        logger.error("No renters available")
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please wait for a renter to register."
        )
    
    try:
        # Save the uploaded file temporarily
        temp_path = UPLOAD_DIR / file.filename
        logger.info(f"Saving uploaded file temporarily to: {temp_path}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Calculate number of shards based on file size
        file_size = os.path.getsize(temp_path)
        num_shards = max(MIN_SHARDS, math.ceil(file_size / SHARD_SIZE))
        logger.info(f"Splitting file into {num_shards} shards")
        
        # Split file into shards
        shards = split_file_into_shards(temp_path, num_shards)
        
        # Distribute shards to renters
        distributed_shards = distribute_shards_to_renters(shards, file.filename)
        
        # Store shard information
        shard_locations[file.filename] = distributed_shards
        
        # Clean up temporary files
        os.remove(temp_path)
        for shard in shards:
            os.remove(shard)
        
        logger.info("File successfully uploaded and distributed")
        
        return {
            "filename": file.filename,
            "num_shards": num_shards,
            "shard_size": SHARD_SIZE,
            "message": "File uploaded and distributed successfully"
        }
    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}")
        # Clean up temporary files if they exist
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        if 'shards' in locals():
            for shard in shards:
                if os.path.exists(shard):
                    os.remove(shard)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file by reconstructing it from shards."""
    cleanup_inactive_renters()
    
    if filename not in shard_locations:
        logger.error(f"File not found: {filename}")
        raise HTTPException(
            status_code=404, 
            detail=f"File '{filename}' not found. Please upload the file first."
        )
    
    try:
        # Create a temporary file for reconstruction
        temp_path = UPLOAD_DIR / f"temp_{filename}"
        
        # Check if we have any renters
        if not renters:
            logger.error("No renters available")
            raise HTTPException(
                status_code=503,
                detail="No renters available. Please wait for a renter to register."
            )
        
        # Collect shards from renters in order
        with open(temp_path, 'wb') as outfile:
            for shard_info in sorted(shard_locations[filename], key=lambda x: x['shard_index']):
                renter = renters[shard_info['renter_id']]
                try:
                    response = requests.get(
                        f"{renter['url']}/retrieve-shard/",
                        params={'filename': shard_info['shard_path']},
                        timeout=30
                    )
                    response.raise_for_status()
                    outfile.write(response.content)
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error retrieving shard from renter: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to retrieve shard from renter: {str(e)}"
                    )
        
        # Return the reconstructed file
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Error in download process: {str(e)}")
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

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
            renter = renters[shard_info['renter_id']]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 