from re import A
from turtle import st
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
import rpyc
import random
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import json

from blockchain.BlockchainServices import Account  # Add this import for JSON handling

# Set up basic console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def stopwatch(func):
    def wrapper(*args, **kwargs):
        t0 = time.time()
        print("Starting stopwatch...")
        func(*args, **kwargs)
        t1 = time.time()
        elapsed_time = t1 - t0
        print("function {} time: {:.2f} seconds".format(func.__name__,elapsed_time))
    return wrapper

class StorageClient:
    def __init__(self, username, server_url: str, blockchain_server_url: str = None):
        """Initialize the storage client with the server URL."""
        # Ensure server_url has a scheme
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"http://{server_url}"
        self.server_url = server_url.rstrip('/')  # Remove trailing slash if present
        
        # Initialize blockchain connection if URL provided
        self.blockchain_conn = None
        self.blockchain_address = None
        if blockchain_server_url:
            try:
            # Remove any protocol prefix and port if present
                blockchain_server_url = blockchain_server_url.replace('http://', '').replace('https://', '')
                if ':' in blockchain_server_url:
                    blockchain_server_url, blockchain_port = blockchain_server_url.split(':')
                else:
                    blockchain_port = 7575  # Default port for blockchain server
                self.blockchain_conn = rpyc.connect(blockchain_server_url, blockchain_port)
                logger.info("Connected to blockchain server")
            except Exception as e:
                logger.error(f"Failed to connect to blockchain server: {str(e)}")
        
        # Create base client directory
        self.base_dir = Path("S4S_Client")
        self.base_dir.mkdir(exist_ok=True)
        
        # Create downloads directory
        self.downloads_dir = self.base_dir / "downloads"
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Create keys directory
        self.keys_dir = self.base_dir / "keys"
        self.keys_dir.mkdir(exist_ok=True)
        
        # Load or generate encryption key
        self.encryption_key = self.load_or_generate_key()
        
        # Load or generate RSA keys
        self.private_key, self.public_key = self.load_or_generate_rsa_keys()
        
        # Get username from user
        try:
            self.username = self.create_username(username) # creates username, adds nonce and saves it.
            print(f"Your username is: {self.username}")
        except ValueError as e:
            print(f"Username cannot be empty. Please try again.")
            raise e
        
        # Register public key with server
        self.register_public_key()
        
        # Dictionary to track scheduled retrievals
        self.scheduled_retrievals = {}
        
        logger.info(f"Initialized client with server URL: {self.server_url}")
        logger.info(f"Base directory: {self.base_dir}")
        logger.info(f"Downloads directory: {self.downloads_dir}")
        logger.info(f"Keys directory: {self.keys_dir}")
        logger.info(f"Username: {self.username}")
    
    def create_username(self, username) -> str:
        """Prompt user for username and store it in a JSON file."""
        user_data_file = self.keys_dir / "user_data.json"
        # Load existing user data if the file exists
        if user_data_file.exists():
            try:
                print(f"Loading existing user data from {user_data_file}...")
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
                    stored_username = user_data.get("username")
                    if stored_username:
                        print(f"Found stored username: {stored_username}")
                        return stored_username
            except Exception as e:
                logger.error(f"Error reading user data file: {e}")
           
        if username:
            try:
                nonce = random.randint(100000, 999999)  # Generate a random 6-digit nonce
                username = f"{username}{nonce}"
                # Save the username in the JSON file
                user_data = {"username": username, "upload_history": []}
                with open(user_data_file, 'w') as f:
                    json.dump(user_data, f, indent=4)
                return username
            except Exception as e:
                logger.error(f"Error saving username: {e}")
                print("Username will not be saved for future use")
                return username
        raise ValueError("Username cannot be empty. Please try again.")
    
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
    
    def load_or_generate_key(self) -> bytes:
        """Load existing key or generate a new one."""
        key_file = self.keys_dir / "encryption.key"
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                    logger.info("Loaded existing encryption key")
                    return key
            except Exception as e:
                logger.error(f"Error loading encryption key: {e}")
                logger.info("Generating new key...")
        
        # Generate new key
        key = self.generate_key("your-secret-password")  # In production, get this from user input
        
        # Save the key
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("New encryption key generated and saved")
        except Exception as e:
            logger.error(f"Warning: Failed to save encryption key: {e}")
        
        return key
    
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
    
    def calculate_storage_cost(self, file_path: str, duration_minutes: int) -> float:
        """Calculate the cost of storing a file based on size and duration."""
        if duration_minutes is None or duration_minutes <= 0:
            raise ValueError("Duration must be greater than 0 minutes")       
        # Base cost per MB per minute
        BASE_COST_PER_MB_PER_MINUTE = 0.01  # $0.01 per MB per minute
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}") 
        # Get file size in MB
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        # Calculate total cost
        total_cost = file_size_mb * duration_minutes * BASE_COST_PER_MB_PER_MINUTE
        
        return round(total_cost, 2) # Round to 2 decimal places

    def make_payment(self, amount: float, renter_address: str) -> str:
        """Make a payment to a renter's blockchain address and return the transaction hash."""
        if not self.blockchain_conn or not self.blockchain_address:
            raise Exception("Blockchain not connected or account not created")
        
        try:
            # Check if user has sufficient balance
            balance = self.get_blockchain_balance(self.blockchain_address)
            if balance < amount:
                raise ValueError(f"Insufficient balance. Required: {amount}, Available: {balance}")
            
            # Make the payment and get the transaction receipt
            receipt = self.blockchain_conn.root.exposed_send_money(self.blockchain_address, renter_address, amount)

            # Convert RPyC proxy object to a standard dictionary if necessary
            if hasattr(receipt, "items"):
                receipt = {key: value for key, value in receipt.items()}
            
            # Extract the transaction hash
            transaction_hash = receipt["transaction_hash"]
            if not transaction_hash:
                raise Exception("Transaction hash not found in the receipt")
            
            logger.info(f"Payment successful: {transaction_hash}")
            return transaction_hash
        except Exception as e:
            logger.error(f"Payment failed: {str(e)}")
            raise
    
    @stopwatch
    def upload_file(self, file_path: str, cost, duration_minutes: int = 1) -> None:
        """Upload a file to the storage system."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file size in MB
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Enforce minimum file size of 5 MB
            MIN_FILE_SIZE_MB = 5
            if file_size_mb < MIN_FILE_SIZE_MB:
                raise ValueError(f"File size must be at least {MIN_FILE_SIZE_MB} MB. Current file size: {file_size_mb:.2f} MB")
            
            # Calculate storage cost if duration is specified
            payment = 0
            transaction_hash = None
                
            # Get renter information from server
            response = requests.get(f"{self.server_url}/get-renters/")
            response.raise_for_status()
            renters = response.json()
            
            if not renters:
                raise Exception("No renters available")
            
            # Select a random renter to pay
            renter = random.choice(renters)
            renter_address = renter.get('blockchain_address')
            
            if not renter_address:
                raise Exception("Selected renter has no blockchain address")
            
            # Ask for confirmation
            confirm = input(f"Confirm payment of {cost} to renter {renter_address}? (y/n): ").lower()
            if confirm != 'y':
                print("Upload cancelled")
                return
            
            # Make the payment and get the transaction hash
            transaction_hash = self.make_payment(cost, renter_address)
            payment = cost
            
            # Create temporary encrypted file
            temp_encrypted = file_path.parent / f"encrypted_{file_path.name}"
            self.encrypt_file(file_path, temp_encrypted, self.encryption_key)
            
            # Upload the encrypted file
            with open(temp_encrypted, 'rb') as f:
                files = {'file': (file_path.name, f)}
                response = requests.post(
                    f"{self.server_url}/upload/",
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
            
            # Clean up temporary file
            os.remove(temp_encrypted)
                       
            # Update upload history
            self.update_upload_history(file_path.name, file_size_mb, payment, transaction_hash)
            
            # If duration is specified, schedule automatic retrieval
            if duration_minutes is not None and duration_minutes > 0:
                self.schedule_retrieval(file_path.name, duration_minutes)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in upload process: {str(e)}")
            raise
    
    def download_file(self, filename: str, output_path: str = None) -> None:
        """Download a file from the storage system with challenge-response authentication."""
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
            
            # Get the challenge from the server
            response = requests.get(
                f"{self.server_url}/download/{filename}",
                params={"username": self.username},
                timeout=30
            )
            response.raise_for_status()
            challenge_data = response.json()
            
            # Decrypt the challenge using our private key
            encrypted_challenge = base64.b64decode(challenge_data["challenge"])
            decrypted_nonce = self.decrypt_challenge(encrypted_challenge)
            
            # Send the decrypted nonce back to the server
            verify_response = requests.post(
                f"{self.server_url}/verify-challenge/{filename}",
                params={"username": self.username},
                json={"response": decrypted_nonce},
                timeout=30
            )
            verify_response.raise_for_status()
            
            # Save the encrypted file temporarily
            temp_encrypted = output_path.parent / f"encrypted_{filename}"
            with open(temp_encrypted, 'wb') as f:
                f.write(verify_response.content)
            
            # Decrypt the file using the stored key
            try:
                self.decrypt_file(temp_encrypted, output_path, self.encryption_key)
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
            
            # Mark file as retrieved in upload history
            self.mark_file_as_retrieved(filename)
            
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

    def create_blockchain_account(self, username: str, initial_balance: float = 1000.0) -> str:
        """Create a new blockchain account."""
        if not self.blockchain_conn:
            raise Exception("Blockchain server not connected")
        try:
            address = self.blockchain_conn.root.exposed_create_account(username, initial_balance)
            logger.info(f"Created blockchain account for {username}")
            return address
        except Exception as e:
                raise Exception(e)

    def get_blockchain_balance(self, address: str) -> float:
        """Get the balance of a blockchain account."""
        if not self.blockchain_conn:
            raise Exception("Blockchain server not connected")
        try:
            balance = self.blockchain_conn.root.exposed_get_balance(address)
            return balance
        except Exception as e:
            logger.error(f"Failed to get blockchain balance: {str(e)}")
            raise

    def send_blockchain_payment(self, sender_address: str, receiver_address: str, amount: float) -> bool:
        """Send payment through the blockchain."""
        if not self.blockchain_conn:
            raise Exception("Blockchain server not connected")
        try:
            success = self.blockchain_conn.root.exposed_send_money(sender_address, receiver_address, amount)
            if success:
                logger.info(f"Successfully sent {amount} from {sender_address} to {receiver_address}")
            return success
        except Exception as e:
            logger.error(f"Failed to send blockchain payment: {str(e)}")
            raise

    def load_or_generate_rsa_keys(self):
        """Load existing RSA keys or generate new ones."""
        private_key_path = self.keys_dir / "private_key.pem"
        public_key_path = self.keys_dir / "public_key.pem"
        
        if private_key_path.exists() and public_key_path.exists():
            try:
                with open(private_key_path, "rb") as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None
                    )
                with open(public_key_path, "rb") as f:
                    public_key = serialization.load_pem_public_key(
                        f.read()
                    )
                logger.info("Loaded existing RSA keys")
                return private_key, public_key
            except Exception as e:
                logger.error(f"Error loading RSA keys: {e}")
                logger.info("Generating new RSA keys...")
        
        # Generate new RSA keys
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Save the keys
        try:
            with open(private_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            with open(public_key_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            logger.info("New RSA keys generated and saved")
        except Exception as e:
            logger.error(f"Warning: Failed to save RSA keys: {e}")
        
        return private_key, public_key
    
    def register_public_key(self):
        """Register the client's public key with the server."""
        try:
            # Convert public key to PEM format
            public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            # Send public key to server
            response = requests.post(
                f"{self.server_url}/register-public-key/",
                json={
                    "username": self.username,
                    "public_key": public_key_pem
                }
            )
            response.raise_for_status()
            logger.info("Public key registered with server")
        except Exception as e:
            logger.error(f"Failed to register public key: {e}")
    
    def decrypt_challenge(self, encrypted_challenge: bytes) -> str:
        """Decrypt a challenge using the private key."""
        try:
            decrypted = self.private_key.decrypt(
                encrypted_challenge,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted.decode('utf-8')
        except ValueError as e:
            logger.error(f"Decryption failed due to invalid data or key mismatch: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during decryption: {e}")
            raise

    def update_upload_history(self, file_name: str, file_size: float, payment: float, transaction_hash: str) -> None:
        """Update the JSON file with file upload details."""
        user_data_file = self.keys_dir / "user_data.json"
        
        try:
            # Load existing user data
            if user_data_file.exists():
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
            else:
                user_data = {"username": self.username, "upload_history": []}
            
            # Add new upload details
            upload_details = {
                "file_name": file_name,
                "file_size_mb": round(file_size, 2),
                "payment": round(payment, 2),
                "transaction_hash": transaction_hash,
                "timestamp": datetime.now().isoformat(),  # Add timestamp for upload
                "retrieved": False  # Set retrieved to False initially
            }
            user_data["upload_history"].append(upload_details)
            
            # Save updated data back to the file
            with open(user_data_file, 'w') as f:
                json.dump(user_data, f, indent=4)
            
            logger.info(f"Upload history updated for file: {file_name}")
        except Exception as e:
            logger.error(f"Error updating upload history: {e}")

    def mark_file_as_retrieved(self, file_name: str) -> None:
        """Mark a file as retrieved in the upload history."""
        user_data_file = self.keys_dir / "user_data.json"
        
        try:
            # Load existing user data
            if user_data_file.exists():
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
            else:
                raise FileNotFoundError("User data file not found")
            
            # Find the file in the upload history and update the retrieved field
            for upload in user_data["upload_history"]:
                if upload["file_name"] == file_name:
                    upload["retrieved"] = True
                    break
            else:
                raise ValueError(f"File '{file_name}' not found in upload history")
            
            # Save updated data back to the file
            with open(user_data_file, 'w') as f:
                json.dump(user_data, f, indent=4)
            
            logger.info(f"File marked as retrieved: {file_name}")
        except Exception as e:
            logger.error(f"Error marking file as retrieved: {e}")

    def list_unretrieved_files(self) -> None:
        """List all files from user_data.json that haven't been retrieved yet."""
        user_data_file = self.keys_dir / "user_data.json"
        
        try:
            # Load existing user data
            if user_data_file.exists():
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
            else:
                raise FileNotFoundError("User data file not found")
            
            # Filter files that haven't been retrieved
            unretrieved_files = [
                upload["file_name"] for upload in user_data["upload_history"] if not upload.get("retrieved", False)
            ]
            
            # Print the unretrieved files
            if unretrieved_files:
                print("\nFiles that haven't been retrieved yet:")
                for file_name in unretrieved_files:
                    print(f"- {file_name}")
            else:
                print("\nAll files have been retrieved.")
        except Exception as e:
            logger.error(f"Error listing unretrieved files: {e}")

    def retrieve_file(self, file_name, output_path=None) -> None:
        """Handle file retrieval."""
        try:
            # List unretrieved files
            self.list_unretrieved_files()
            # Ask the user for the file name to retrieve
            if not file_name:
                print("File name cannot be empty.")
                return
            try:
                # Call the download_file method to retrieve the file
                if not output_path or output_path.strip() == "":
                    output_path = str(self.downloads_dir / file_name)
                    print(f"Using default download location: {output_path}")
                elif not os.path.exists(output_path):
                    # If the path doesn't exist, create it
                    print(f"Specified path does not exist...Creating new directory:\n{output_path}")
                    os.makedirs(output_path, exist_ok=True)
                    output_path = os.path.join(output_path, file_name)
                
                self.download_file(file_name, output_path)
            except Exception as e:
                logger.error(f"Error during file retrieval: {e}")
                print(f"Error: {e}")
            
            # Mark the file as retrieved
            self.mark_file_as_retrieved(file_name)

        except Exception as e:
            logger.error(f"Error retrieving file: {e}")

def main():
    """Main function to run the client."""
    print("Welcome to the Distributed Storage Client!")
    
    # Get server URL
    while True:
        server_url = input("Enter the server URL (e.g., 192.168.1.100:8000): ").strip() or "http://192.168.3.46:8000"
        if server_url:
            break
        print("Server URL cannot be empty. Please try again.")
    
    # Get blockchain server URL
    blockchain_server_url = input("Enter the blockchain server URL (e.g., 192.168.1.100:7575) [Press Enter to skip]: ").strip()
    
    # Get username from user
    username = input("Enter your username: ").strip()
    
    # Initialize client
    client = StorageClient(username, server_url, blockchain_server_url)
    
    # Create blockchain account if connected
    if blockchain_server_url:
        try:
            client.blockchain_address = client.create_blockchain_account(client.username)
            print(f"Your blockchain address: {client.blockchain_address}")
            balance = client.get_blockchain_balance(client.blockchain_address)
            print(f"Your blockchain balance: {balance}")
        except Exception as e:
            if isinstance(e, Account.AccountExists):  # Ensure it's not the AccountExists exception
                print("This username already exists. Please use a different username.")
            else:
                print(f"Error setting up blockchain account: {str(e)}")
                print("Blockchain features will not be available")
                client.blockchain_conn = None  # Disable blockchain features
    
    while True:
        print("\nOptions:")
        print("1. Upload a file")
        print("2. Retrieve a file")
        print("3. List unretrieved files")
        if client.blockchain_conn and client.blockchain_address:
            print("4. Check blockchain balance")
            print("5. Send blockchain payment")
            print("6. Exit")
        else:
            print("4. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            file_path = input("Enter the path to the file you want to upload: ")
            while True:
                try:
                    duration_input = input("Enter duration in minutes after which to automatically retrieve the file (1 minute minimum): ").strip()
                    if not duration_input:
                        duration_minutes = 1
                        break
                    duration_minutes = int(duration_input)
                    if duration_minutes >= 0:
                        break
                    print("Duration must be 0 or greater. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            try:
                cost = client.calculate_storage_cost(file_path, duration_minutes)
                client.upload_file(file_path, cost, duration_minutes)
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == "2":
            try:
                file_name = input("\nEnter the name of the file you wish to retrieve: ").strip()
                output_path = input("Enter the path where you want to save the file (press Enter to use default location): ").strip()
                client.retrieve_file(file_name, output_path)
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == "3":
            try:
                client.list_unretrieved_files()
            except Exception as e:
                print(f"Error: {str(e)}")

        elif choice == "4" and client.blockchain_conn and client.blockchain_address:
            try:
                balance = client.get_blockchain_balance(client.blockchain_address)
                print(f"Your blockchain balance: {balance}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "5" and client.blockchain_conn and client.blockchain_address:
            try:
                receiver_address = input("Enter receiver's blockchain address: ").strip()
                amount = float(input("Enter amount to send: "))
                success = client.send_blockchain_payment(client.blockchain_address, receiver_address, amount)
                if success:
                    print("Payment sent successfully!")
                    balance = client.get_blockchain_balance(client.blockchain_address)
                    print(f"Your new balance: {balance}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "4" and not client.blockchain_conn or choice == "6" and client.blockchain_conn:
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()