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

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Distributed Storage Server is running"}

@app.post("/register-renter/")
async def register_renter(renter_info: dict):
    """Register a new renter."""
    try:
        renter_id = str(uuid.uuid4())
        renters[renter_id] = {
            "url": renter_info["url"],
            "storage_available": renter_info["storage_available"]
        }
        logger.info(f"Renter registered successfully with ID: {renter_id}")
        return {"renter_id": renter_id, "message": "Renter registered successfully"}
    except Exception as e:
        logger.error(f"Error registering renter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and distribute it across renters."""
    if not renters:
        logger.error("No renters available")
        raise HTTPException(
            status_code=503,
            detail="No renters available. Please register a renter first."
        )
    
    try:
        # Save the uploaded file temporarily
        temp_path = UPLOAD_DIR / file.filename
        logger.info(f"Saving uploaded file temporarily to: {temp_path}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Split the file into shards (for simplicity, we'll just copy the file)
        shard_path = f"shard_{file.filename}"
        
        # Store shard information
        shard_locations[file.filename] = [{
            "renter_id": list(renters.keys())[0],  # Use the first renter for simplicity
            "shard_path": shard_path
        }]
        
        # Send shard to renter
        renter = renters[list(renters.keys())[0]]
        renter_url = renter['url']
        logger.info(f"Sending shard to renter at: {renter_url}")
        
        try:
            with open(temp_path, "rb") as f:
                files = {"file": (shard_path, f)}
                response = requests.post(
                    f"{renter_url}/store-shard/",
                    files=files,
                    timeout=30  # Add timeout
                )
                response.raise_for_status()
                logger.info("Shard successfully sent to renter")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending shard to renter: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send shard to renter: {str(e)}"
            )
        
        # Clean up temporary file
        os.remove(temp_path)
        logger.info("Temporary file cleaned up")
        
        return {
            "filename": file.filename,
            "num_shards": 1,
            "message": "File uploaded and distributed successfully"
        }
    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}")
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file by reconstructing it from shards."""
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
                detail="No renters available. Please register a renter first."
            )
        
        # Collect shards from renters
        with open(temp_path, 'wb') as outfile:
            for shard_info in shard_locations[filename]:
                renter = renters[shard_info['renter_id']]
                try:
                    response = requests.get(
                        f"{renter['url']}/retrieve-shard/",
                        params={'filename': shard_info['shard_path']},
                        timeout=30  # Add timeout
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 