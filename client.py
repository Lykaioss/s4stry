import requests
import os
from pathlib import Path
import logging
from cryptography.fernet import Fernet
import base64
import hashlib
import time
import threading
from datetime import datetime
import uuid
import random
import traceback
import aiohttp
from blockchain.blockchain import Blockchain

# Set up basic console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        """Initialize the client with server URL."""
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
        self.blockchain = Blockchain()
        self.blockchain_address = None
        self.session = None
        
        # Create client directory if it doesn't exist
        os.makedirs("S4S_Client/downloads", exist_ok=True)
        
        print(f"\n=== Client Initialized ===")
        print(f"Client ID: {self.client_id}")
        print(f"Server URL: {self.server_url}")
        
    async def start(self):
        """Start the client session."""
        self.session = aiohttp.ClientSession()
        return await self.register_with_server()
        
    async def stop(self):
        """Stop the client session."""
        if self.session:
            await self.session.close()
    
    async def register_with_server(self):
        """Register with the server and create blockchain account."""
        try:
            # First, create blockchain account
            self.blockchain_address = self.blockchain.create_account(self.client_id)
            if not self.blockchain_address:
                print("Failed to create blockchain account")
                return False
                
            # Then register with server
            response = await self.session.post(
                f"{self.server_url}/register-client/",
                json={
                    "client_id": self.client_id,
                    "blockchain_address": self.blockchain_address
                }
            )
            
            if response.status == 200:
                data = await response.json()
                print(f"\n=== Registration Successful ===")
                print(f"Client ID: {self.client_id}")
                print(f"Blockchain Address: {self.blockchain_address}")
                print(f"Initial Balance: {self.blockchain.initial_balance} sabudhana")
                return True
            else:
                print(f"Failed to register with server: {response.status}")
                return False
                
        except Exception as e:
            print(f"Error registering with server: {e}")
            traceback.print_exc()
            return False
    
    def generate_key(self, password: str) -> bytes:
        """Generate a Fernet key from a password."""
        # Use SHA-256 to hash the password and then base64 encode it
        key = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def encrypt_file(self, input_path: Path, output_path: Path, key: bytes) -> None:
        """Encrypt a file using Fernet."""
        fernet = Fernet(key)
        with open(input_path, 'rb') as file:
            original = file.read()
        encrypted = fernet.encrypt(original)
        with open(output_path, 'wb') as encrypted_file:
            encrypted_file.write(encrypted)
    
    def decrypt_file(self, input_path: Path, output_path: Path, key: bytes) -> None:
        """Decrypt a file using Fernet."""
        fernet = Fernet(key)
        with open(input_path, 'rb') as encrypted_file:
            encrypted = encrypted_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open(output_path, 'wb') as decrypted_file:
            decrypted_file.write(decrypted)
    
    def schedule_retrieval(self, filename: str, duration_minutes: int) -> None:
        """Schedule automatic retrieval of a file after specified duration."""
        def retrieve_after_delay():
            time.sleep(duration_minutes * 60)  # Convert minutes to seconds
            try:
                print(f"\nAutomatically retrieving file: {filename}")
                self.download_file(filename)
                # Remove from scheduled retrievals after successful retrieval
                if filename in self.scheduled_retrievals:
                    del self.scheduled_retrievals[filename]
            except Exception as e:
                print(f"Error during automatic retrieval of {filename}: {str(e)}")
        
        # Store the thread in our tracking dictionary
        thread = threading.Thread(target=retrieve_after_delay, daemon=True)
        self.scheduled_retrievals[filename] = thread
        thread.start()
        print(f"File '{filename}' will be automatically retrieved after {duration_minutes} minutes")
    
    async def upload_file(self, file_path: str):
        """Upload a file to the network."""
        try:
            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                return

            # Get file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Calculate storage cost (1 sabudhana per GB per hour)
            # For demo, we'll use 1 hour duration
            duration = 3600  # 1 hour in seconds
            cost_per_gb_hour = 1.0
            storage_cost = (file_size / (1024 * 1024 * 1024)) * (duration / 3600) * cost_per_gb_hour
            
            # Get current balance
            balance = self.blockchain.get_balance(self.blockchain_address)
            
            print(f"\n=== File Upload Details ===")
            print(f"File: {file_name}")
            print(f"Size: {file_size / (1024 * 1024):.2f} MB")
            print(f"Duration: {duration / 3600:.2f} hours")
            print(f"Storage Cost: {storage_cost:.2f} sabudhana")
            print(f"Current Balance: {balance:.2f} sabudhana")
            print(f"Remaining Balance: {balance - storage_cost:.2f} sabudhana")
            
            # Ask for confirmation
            confirm = input("\nDo you want to proceed with the upload? (yes/no): ").lower()
            if confirm != 'yes':
                print("Upload cancelled.")
                return

            # Register with server
            await self.register_with_server()

            # Get available renters
            renters = await self.get_available_renters()
            if not renters:
                print("No renters available")
                return

            # Split file into shards
            shards = self.split_file(file_path)
            print(f"Split file into {len(shards)} shards")

            # Create storage contracts for each shard
            contracts = []
            for shard in shards:
                # Select a random renter
                renter = random.choice(renters)
                
                # Create storage contract
                contract_id = self.blockchain.create_storage_contract(
                    self.blockchain_address,
                    renter['blockchain_address'],
                    len(shard),
                    duration,
                    storage_cost / len(shards)  # Split cost among shards
                )
                
                if not contract_id:
                    print("Failed to create storage contract")
                    return
                    
                contracts.append({
                    'contract_id': contract_id,
                    'renter': renter,
                    'shard': shard
                })

            # Send shards to renters
            for contract in contracts:
                success = await self.send_shard_to_renter(
                    contract['renter'],
                    contract['shard'],
                    file_name,
                    contract['contract_id']
                )
                if not success:
                    print(f"Failed to send shard to renter {contract['renter']['id']}")
                    return

            print(f"\nFile '{file_name}' uploaded successfully!")
            print(f"Storage Cost: {storage_cost:.2f} sabudhana")
            print(f"New Balance: {self.blockchain.get_balance(self.blockchain_address):.2f} sabudhana")

        except Exception as e:
            print(f"Error uploading file: {e}")
            traceback.print_exc()
    
    def download_file(self, filename: str, output_path: str = None) -> None:
        """Download a file from the storage system."""
        try:
            # If no output path provided, use the default downloads directory
            if not output_path or output_path.strip() == "":
                output_path = str(self.downloads_dir / filename)
                print(f"Using default download location: {output_path}")
            
            # Convert to Path object and normalize
            output_path = Path(output_path.strip('"').strip("'"))
            
            # Check if the path exists and is a directory
            if output_path.exists() and output_path.is_dir():
                # If it's a directory, append the filename
                output_path = output_path / filename
            elif not output_path.parent.exists():
                # If parent directory doesn't exist, try to create it
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    raise PermissionError(f"Cannot create directory: {output_path.parent}. Please check permissions.")
            
            # Check if we have write permission
            try:
                # Try to create a test file
                test_file = output_path.parent / f".test_{int(time.time())}"
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                raise PermissionError(f"No write permission in directory: {output_path.parent}. Please choose a different location.")
            
            # Download the encrypted file
            response = requests.get(
                f"{self.server_url}/download/{filename}",
                params={'client_id': self.client_id},
                timeout=30
            )
            response.raise_for_status()
            
            # Save the encrypted file temporarily in the system temp directory
            temp_dir = Path(os.environ.get('TEMP', os.environ.get('TMP', '.')))
            temp_encrypted = temp_dir / f"encrypted_{filename}"
            try:
                with open(temp_encrypted, 'wb') as f:
                    f.write(response.content)
            except PermissionError:
                raise PermissionError(f"Cannot write to temporary directory: {temp_dir}. Please check permissions.")
            
            # Generate the same key used for encryption
            key = self.generate_key("your-secret-password")  # Must match the key used for encryption
            
            # Decrypt the file
            try:
                self.decrypt_file(temp_encrypted, output_path, key)
            except PermissionError:
                raise PermissionError(f"Cannot write to: {output_path}. Please check permissions.")
            
            # Clean up temporary file
            try:
                os.remove(temp_encrypted)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {str(e)}")
            
            # Request deletion from renters
            try:
                response = requests.post(
                    f"{self.server_url}/delete/{filename}",
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"File deleted from renters: {filename}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to delete file from renters: {str(e)}")
            
            logger.info(f"File downloaded successfully: {filename}")
            print(f"File downloaded successfully to: {output_path}")
            
        except PermissionError as e:
            logger.error(f"Permission error: {str(e)}")
            print(f"Error: {str(e)}")
            print("Please try a different location where you have write permissions.")
            print("Suggested locations:")
            print("1. Your Desktop: C:\\Users\\YourUsername\\Desktop")
            print("2. Your Documents: C:\\Users\\YourUsername\\Documents")
            print("3. Your Downloads: C:\\Users\\YourUsername\\Downloads")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            raise

async def main():
    # Get server URL from user
    server_url = input("Enter server URL (default: http://localhost:8000): ").strip()
    if not server_url:
        server_url = "http://localhost:8000"
        
    # Initialize client
    client = StorageClient(server_url)
    
    try:
        # Start client session and register
        if not await client.start():
            print("Failed to start client. Exiting...")
            return
            
        while True:
            print("\n=== S4S Client Menu ===")
            print("1. Upload file")
            print("2. Download file")
            print("3. View balance")
            print("4. View transactions")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == "1":
                file_path = input("Enter file path to upload: ")
                await client.upload_file(file_path)
                
            elif choice == "2":
                filename = input("Enter filename to download: ")
                output_path = input("Enter output path (press Enter for default): ")
                if output_path:
                    client.download_file(filename, output_path)
                else:
                    client.download_file(filename)
                    
            elif choice == "3":
                balance = client.blockchain.get_balance(client.blockchain_address)
                print(f"\nCurrent Balance: {balance} sabudhana")
                
            elif choice == "4":
                client.blockchain.print_blockchain_status()
                
            elif choice == "5":
                print("Exiting...")
                break
                
            else:
                print("Invalid choice. Please try again.")
                
    except Exception as e:
        print(f"Error in main loop: {e}")
        traceback.print_exc()
    finally:
        await client.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 