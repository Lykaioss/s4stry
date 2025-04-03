# Distributed Storage System

This is a distributed storage system that allows you to upload files and store them across multiple machines (renters) in a network.

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
  - `storage/` - For storing file shards on the renter
- Make sure you have write permissions in your current directory
- The system uses these ports:
  - Server: 8000
  - Renter: 8001 