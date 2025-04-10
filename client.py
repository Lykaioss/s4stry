import requests
import os
from pathlib import Path
import logging
from cryptography.fernet import Fernet
import base64
import hashlib
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self, server_url: str):
        """Initialize the storage client with the server URL."""
        # Ensure server_url has a scheme
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"http://{server_url}"
        self.server_url = server_url.rstrip('/')  # Remove trailing slash if present
        logger.info(f"Initialized client with server URL: {self.server_url}")
    
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
    
    def upload_file(self, file_path: str) -> None:
        """Upload a file to the storage system."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Generate encryption key
            key = self.generate_key("your-secret-password")  # In production, get this from user input
            
            # Create temporary encrypted file
            temp_encrypted = file_path.parent / f"encrypted_{file_path.name}"
            self.encrypt_file(file_path, temp_encrypted, key)
            
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in upload process: {str(e)}")
            raise
    
    def download_file(self, filename: str, output_path: str) -> None:
        """Download a file from the storage system."""
        try:
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

def main():
    """Main function to run the client."""
    print("Welcome to the Distributed Storage Client!")
    
    # Get server URL
    while True:
        server_url = input("Enter the server URL (e.g., 192.168.1.100:8000): ").strip()
        if server_url:
            break
        print("Server URL cannot be empty. Please try again.")
    
    # Initialize client
    client = StorageClient(server_url)
    
    while True:
        print("\nOptions:")
        print("1. Upload a file")
        print("2. Download a file")
        print("3. Exit")
        
        choice = input("Enter your choice (1-3): ")
        
        if choice == "1":
            file_path = input("Enter the path to the file you want to upload: ")
            try:
                client.upload_file(file_path)
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "2":
            filename = input("Enter the filename to download: ")
            output_path = input("Enter the path where you want to save the file: ")
            try:
                client.download_file(filename, output_path)
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 