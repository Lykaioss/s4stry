#!/usr/bin/env python3
import os
import json
import argparse
import shlex
from pathlib import Path
from typing import Optional, Dict, Any

# Import your StorageClient class
from client import StorageClient  # Uncomment and adjust this import

# Configuration file path in user's home directory
CONFIG_PATH = os.path.expanduser("~/.s4s_config.json")
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/S4S_Client/downloads")

def load_config() -> Dict[str, Any]:
    """Load configuration from file or return empty config."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def create_client():
    """Create a StorageClient instance using stored configuration."""
    config = load_config()
    
    if not config.get('server_url'):
        print("Error: You need to join a server first. Use 's4s join <server_url>'")
        return None
    
    # Create the client with stored configuration
    client = StorageClient(
        config['server_url'], 
        config.get('blockchain_url')
    )
    
    # Set blockchain address if available
    if 'blockchain_address' in config:
        client.blockchain_address = config['blockchain_address']
    
    if 'username' in config:
        client.username = config['username']
    
    return client

def cmd_join(args):
    """Handle the join command."""
    config = load_config()
    
    # Update config with new connection details
    config['server_url'] = args.server_url
    if args.blockchain_url:
        config['blockchain_url'] = args.blockchain_url
    
    # Create client to test connection and set up blockchain if needed
    try:
        client = StorageClient(config['server_url'], config.get('blockchain_url'))
        
        # If connected to blockchain, create/retrieve account
        if args.blockchain_url:
            try:
                client.blockchain_address = client.create_blockchain_account(client.username)
                config['blockchain_address'] = client.blockchain_address
                config['username'] = client.username
                
                print(f"Your blockchain address: {client.blockchain_address}")
                balance = client.get_blockchain_balance(client.blockchain_address)
                print(f"Your blockchain balance: {balance}")
            except Exception as e:
                if hasattr(e, '__class__') and e.__class__.__name__ == 'AccountExists':
                    print("This username already exists. Please use a different username.")
                else:
                    print(f"Error setting up blockchain account: {str(e)}")
                    print("Blockchain features will not be available")
        
        # Save configuration
        save_config(config)
        print(f"Successfully connected to server: {args.server_url}")
        
    except Exception as e:
        print(f"Failed to connect: {str(e)}")

def cmd_upload(args):
    """Handle the upload command."""
    client = create_client()
    if not client:
        return
    
    # Check if file exists
    if not os.path.exists(args.file_path):
        print(f"Error: File '{args.file_path}' not found.")
        return
    
    try:
        client.upload_file(args.file_path, args.duration)
        print(f"File '{args.file_path}' uploaded successfully.")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

def cmd_retrieve(args):
    """Handle the retrieve command."""
    client = create_client()
    if not client:
        return
    
    try:
        destination_path = None
        # Ensure the download directory exists
        if not os.path.exists(client.downloads_dir):
            destination_path = client.downloads_dir
        else:
            destination_path = args.destination_path.strip()
            os.makedirs(args.destination_path, exist_ok=True)
        
        # Adjust client.retrieve_file to accept a destination path
        client.retrieve_file(args.file_path, destination_path)
        print(f"File retrieved successfully to {args.destination_path}")
    except Exception as e:
        print(f"Retrieval failed: {str(e)}")

def cmd_check_balance(args):
    """Handle the balance check command."""
    client = create_client()
    if not client:
        return
    
    if not client.blockchain_conn or not client.blockchain_address:
        print("Blockchain features are not available. Please join with a blockchain URL.")
        return
    
    try:
        balance = client.get_blockchain_balance(client.blockchain_address)
        print(f"Your blockchain balance: {balance}")
    except Exception as e:
        print(f"Failed to check balance: {str(e)}")

def cmd_pay(args):
    """Handle the payment command."""
    client = create_client()
    if not client:
        return
    
    if not client.blockchain_conn or not client.blockchain_address:
        print("Blockchain features are not available. Please join with a blockchain URL.")
        return
    
    try:
        success = client.send_blockchain_payment(
            client.blockchain_address, 
            args.receiver_address, 
            args.amount
        )
        
        if success:
            print("Payment sent successfully!")
            balance = client.get_blockchain_balance(client.blockchain_address)
            print(f"Your new balance: {balance}")
        else:
            print("Payment failed.")
    except Exception as e:
        print(f"Payment failed: {str(e)}")

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Distributed Storage Client CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  s4s join 192.168.1.100:8000 -b 192.168.1.100
  s4s upload "C:/My Documents/file.txt" -d 60
  s4s retrieve myfile.txt
  s4s balance
  s4s pay abc123def456 10.5
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Join command
    join_parser = subparsers.add_parser('join', help='Connect to a storage server')
    join_parser.add_argument('server_url', help='URL of the storage server (e.g., 192.168.1.100:8000)')
    join_parser.add_argument('-b', '--blockchain-url', help='URL of the blockchain server (optional)')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a file to storage')
    upload_parser.add_argument('file_path', help='Path to the file to upload')
    upload_parser.add_argument('-d', '--duration', type=int, default=0, 
                              help='Auto-retrieval duration in minutes (0 for no auto-retrieval)')
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve a file from storage')
    retrieve_parser.add_argument('file_path', help='Name or path of the file to retrieve')
    retrieve_parser.add_argument('-p', '--destination-path', default=DEFAULT_DOWNLOAD_DIR,
                                help=f'Destination path (default: {DEFAULT_DOWNLOAD_DIR})')
    
    # Balance command
    subparsers.add_parser('balance', help='Check blockchain balance')
    
    # Payment command
    pay_parser = subparsers.add_parser('pay', help='Send blockchain payment')
    pay_parser.add_argument('receiver_address', help='Blockchain address of the payment recipient')
    pay_parser.add_argument('amount', type=float, help='Amount to send')
    
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return
    
    # Execute the appropriate command
    if args.command == 'join':
        cmd_join(args)
    elif args.command == 'upload':
        cmd_upload(args)
    elif args.command == 'retrieve':
        cmd_retrieve(args)
    elif args.command == 'balance':
        cmd_check_balance(args)
    elif args.command == 'pay':
        cmd_pay(args)

if __name__ == "__main__":
    main()