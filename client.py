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

# Set up basic console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self, server_url: str, blockchain_server_url: str = None):
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
                self.blockchain_conn = rpyc.connect(blockchain_server_url, 7575)
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
        
        # Dictionary to track scheduled retrievals
        self.scheduled_retrievals = {}
        
        logger.info(f"Initialized client with server URL: {self.server_url}")
        logger.info(f"Base directory: {self.base_dir}")
        logger.info(f"Downloads directory: {self.downloads_dir}")
        logger.info(f"Keys directory: {self.keys_dir}")
    
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
    
    def calculate_storage_cost(self, file_size_mb: float, duration_minutes: int) -> float:
        """Calculate the cost of storing a file based on size and duration."""
        # Base cost per MB per minute
        BASE_COST_PER_MB_PER_MINUTE = 0.01  # $0.01 per MB per minute
        
        # Calculate total cost
        total_cost = file_size_mb * duration_minutes * BASE_COST_PER_MB_PER_MINUTE
        
        # Round to 2 decimal places
        return round(total_cost, 2)

    def make_payment(self, amount: float, renter_address: str) -> bool:
        """Make a payment to a renter's blockchain address."""
        if not self.blockchain_conn or not self.blockchain_address:
            raise Exception("Blockchain not connected or account not created")
        
        try:
            # Check if user has sufficient balance
            balance = self.get_blockchain_balance(self.blockchain_address)
            if balance < amount:
                raise ValueError(f"Insufficient balance. Required: {amount}, Available: {balance}")
            
            # Make the payment
            success = self.send_blockchain_payment(self.blockchain_address, renter_address, amount)
            if success:
                logger.info(f"Successfully paid {amount} to renter {renter_address}")
                return True
            return False
        except Exception as e:
            logger.error(f"Payment failed: {str(e)}")
            raise

    def upload_file(self, file_path: str, duration_minutes: int = None) -> None:
        """Upload a file to the storage system."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file size in MB
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Calculate storage cost if duration is specified
            if duration_minutes is not None and duration_minutes > 0:
                cost = self.calculate_storage_cost(file_size_mb, duration_minutes)
                print(f"\nStorage cost for {file_size_mb:.2f} MB for {duration_minutes} minutes: {cost}")
                
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
                
                # Make the payment
                self.make_payment(cost, renter_address)
            
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
            
            logger.info(f"File uploaded successfully: {file_path.name}")
            print(f"File uploaded successfully: {file_path.name}")
            
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
            logger.error(f"Failed to create blockchain account: {str(e)}")
            raise

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
    blockchain_server_url = input("Enter the blockchain server URL (e.g., 192.168.1.100) [Press Enter to skip]: ").strip()
    
    # Initialize client
    client = StorageClient(server_url, blockchain_server_url)
    
    # Create blockchain account if connected
    if blockchain_server_url:
        try:
            username = input("Enter your username for blockchain account: ").strip()
            client.blockchain_address = client.create_blockchain_account(username)
            print(f"Your blockchain address: {client.blockchain_address}")
            balance = client.get_blockchain_balance(client.blockchain_address)
            print(f"Your blockchain balance: {balance}")
        except Exception as e:
            print(f"Error setting up blockchain account: {str(e)}")
            print("Blockchain features will not be available")
            client.blockchain_conn = None  # Disable blockchain features
    
    while True:
        print("\nOptions:")
        print("1. Upload a file")
        print("2. Download a file")
        if client.blockchain_conn and client.blockchain_address:
            print("3. Check blockchain balance")
            print("4. Send blockchain payment")
            print("5. Exit")
        else:
            print("3. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            file_path = input("Enter the path to the file you want to upload: ")
            while True:
                try:
                    duration_input = input("Enter duration in minutes after which to automatically retrieve the file (0 for no auto-retrieval): ").strip()
                    if not duration_input:
                        duration_minutes = None
                        break
                    duration_minutes = int(duration_input)
                    if duration_minutes >= 0:
                        break
                    print("Duration must be 0 or greater. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            try:
                client.upload_file(file_path, duration_minutes)
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "2":
            filename = input("Enter the filename to download: ")
            output_path = input("Enter the path where you want to save the file (press Enter to use default location): ")
            try:
                client.download_file(filename, output_path)
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "3" and client.blockchain_conn and client.blockchain_address:
            try:
                balance = client.get_blockchain_balance(client.blockchain_address)
                print(f"Your blockchain balance: {balance}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "4" and client.blockchain_conn and client.blockchain_address:
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
        
        elif choice == "3" and not client.blockchain_conn or choice == "5" and client.blockchain_conn:
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 