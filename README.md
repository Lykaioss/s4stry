# Distributed Storage System

A distributed file storage system that splits files into shards and stores them across multiple renters. Built with FastAPI.

## Features

- File sharding and distribution
- Automatic renter discovery and management
- Heartbeat system for renter health monitoring
- Fault tolerance with multiple renters
- Simple client interface

## Architecture

The system consists of three main components:

1. **Server** (`main.py`):
   - Manages file sharding and distribution
   - Maintains list of active renters
   - Handles file uploads and downloads
   - Monitors renter health through heartbeats

2. **Renters** (`renter.py`):
   - Automatically registers with the server
   - Sends periodic heartbeats to maintain active status
   - Stores file shards
   - Provides shard retrieval functionality

3. **Client** (`client.py`):
   - Simple interface for file operations
   - Only needs to know the server's address
   - Handles file uploads and downloads

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python main.py
```

3. Start one or more renters:
```bash
python renter.py
```

4. Use the client:
```bash
python client.py
```

## Usage

1. Start the server on one machine:
```bash
python main.py
```

2. Start one or more renters on other machines:
```bash
python renter.py
```

3. Use the client on any machine:
```bash
python client.py
```
- Enter the server's URL when prompted (e.g., `http://192.168.1.100:8000`)
- Choose to upload or download files
- Follow the prompts to complete the operation

## How It Works

1. **Renter Registration**:
   - Renters automatically register with the server on startup
   - Each renter gets a unique ID
   - Renters send periodic heartbeats to maintain active status

2. **File Upload**:
   - Client sends file to server
   - Server splits file into shards
   - Shards are distributed across available renters
   - Server tracks shard locations

3. **File Download**:
   - Client requests file from server
   - Server retrieves shards from renters
   - Server reconstructs file from shards
   - Client receives complete file

4. **Renter Management**:
   - Server tracks active renters through heartbeats
   - Inactive renters are automatically removed
   - Shards are redistributed if renters become unavailable

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- Requests
- Python-multipart

## Notes

- The server runs on port 8000
- Renters run on port 8001
- Make sure all machines can reach each other on the network
- The system requires at least one active renter for file operations

## Project Structure

```
.
├── main.py           # Server application (runs on port 8000)
├── renter.py         # Renter application (runs on port 8001)
├── client.py         # Client application for interacting with the system
├── requirements.txt  # Python dependencies
└── README.md        # This file
```

## Setup Instructions

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Linux/Mac
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System on Three Separate Machines

You need three separate machines on the same network:

### 1. Server Machine (Port 8000)
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the server
python main.py
```
The server will run on port 8000. Note down the server's IP address.

### 2. Renter Machine (Port 8001)
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the renter
python renter.py
```
The renter will run on port 8001. Note down the renter's IP address.

### 3. Client Machine
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the client
python client.py
```
When prompted, enter the server's IP address in this format:
```
http://192.168.1.100:8000  # Replace with your server's actual IP
```

## Network Setup Requirements

1. All three machines must be on the same network
2. The server and renter machines need to have their ports (8000 and 8001) accessible
3. You might need to configure Windows Firewall to allow these connections
4. Use local network IPs (usually starting with 192.168.x.x)

## Finding IP Addresses

On Windows, open Command Prompt and type:
```bash
ipconfig
```
Look for "IPv4 Address" under your active network adapter.

## Testing Connectivity

From the client machine, try to ping the server:
```bash
ping 192.168.1.100  # Replace with server's IP
```

## Using the Client Interface

When you run the client, you'll see a menu with these options:
```
Distributed Storage System Client
1. Upload a file
2. Download a file
3. Exit
```

### To Upload a File:
1. Choose option 1
2. Enter the full path to your file
3. Example paths:
   ```
   C:\Users\username\Downloads\test.txt
   or
   C:/Users/username/Downloads/test.txt
   ```
4. The system will upload the file and show you the number of shards created

### To Download a File:
1. Choose option 2
2. Enter the filename you want to download
3. Enter the path where you want to save the file
4. Example save path:
   ```
   C:\Users\username\Downloads
   or
   C:/Users/username/Downloads
   ```

## Troubleshooting

1. If you get a "ModuleNotFoundError":
   - Make sure your virtual environment is activated
   - Run `pip install -r requirements.txt` again

2. If you get a "Port already in use" error:
   - Close any other applications using ports 8000 or 8001
   - Or wait a few seconds and try again

3. If file upload/download fails:
   - Check if the file paths are correct
   - Make sure you have read/write permissions
   - Check if the file exists at the specified path

## Notes

- The system creates two directories automatically:
  - `uploads/` - For temporary file storage on the server
  - `