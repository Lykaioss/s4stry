import requests
import os
from pathlib import Path
import logging
from cryptography.fernet import Fernet
import base64
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self, server_url):
        """Initialize the client with the server URL."""
        self.server_url = server_url
        # Generate a key for encryption/decryption
        self.key = self._generate_key()
        logger.info("Client initialized with encryption key")

    def _generate_key(self):
        """Generate a key for encryption/decryption."""
        # Use a fixed password to generate the key (in a real system, this would be user-provided)
        password = b"mysecretpassword"
        # Generate a key from the password
        key = base64.urlsafe_b64encode(hashlib.sha256(password).digest())
        return Fernet(key)

    def _encrypt_file(self, file_path: str) -> bytes:
        """Encrypt a file and return the encrypted data."""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            encrypted_data = self.key.encrypt(file_data)
            return encrypted_data
        except Exception as e:
            logger.error(f"Error encrypting file: {str(e)}")
            raise

    def _decrypt_file(self, encrypted_data: bytes, output_path: str):
        """Decrypt data and save it to a file."""
        try:
            decrypted_data = self.key.decrypt(encrypted_data)
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
        except Exception as e:
            logger.error(f"Error decrypting file: {str(e)}")
            raise

    def upload_file(self, file_path):
        """Upload an encrypted file to the server."""
        try:
            # Remove quotes if present and normalize path
            file_path = file_path.strip('"').strip("'")
            file_path = os.path.normpath(file_path)
            
            if not os.path.exists(file_path):
                print(f"File not found at path: {file_path}")
                return None
            
            # Encrypt the file
            encrypted_data = self._encrypt_file(file_path)
            
            # Create a temporary file with encrypted data
            temp_path = f"{file_path}.enc"
            with open(temp_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Upload the encrypted file
            with open(temp_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(f"{self.server_url}/upload/", files=files)
                response.raise_for_status()
            
            # Clean up temporary encrypted file
            os.remove(temp_path)
            
            return response.json()
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    def download_file(self, filename, output_path):
        """Download and decrypt a file from the server."""
        try:
            # Remove quotes if present and normalize path
            output_path = output_path.strip('"').strip("'")
            output_path = os.path.normpath(output_path)
            
            # If output_path is a directory, append the filename
            if os.path.isdir(output_path):
                output_path = os.path.join(output_path, filename)
            
            # Download the encrypted file
            response = requests.get(f"{self.server_url}/download/{filename}")
            
            # Handle different error cases
            if response.status_code == 404:
                print(f"Error: File '{filename}' not found. Please upload the file first.")
                return False
            elif response.status_code == 503:
                print("Error: No renters available. Please wait for a renter to register.")
                return False
            elif response.status_code != 200:
                print(f"Error: Server returned status code {response.status_code}")
                print(f"Details: {response.text}")
                return False
            
            # Decrypt the file
            self._decrypt_file(response.content, output_path)
            
            # Request file deletion from renters
            try:
                delete_response = requests.post(
                    f"{self.server_url}/delete/{filename}"
                )
                if delete_response.status_code == 200:
                    logger.info(f"File {filename} deleted from renters")
                else:
                    logger.warning(f"Failed to delete file {filename} from renters")
            except Exception as e:
                logger.error(f"Error requesting file deletion: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

def main():
    # Get server IP from user
    print("\nWelcome to the Distributed Storage System Client!")
    print("Please enter the IP address of the server machine")
    print("Example: http://192.168.1.100:8000")
    server_url = input("Server URL: ").strip()
    
    # Create client instance
    client = StorageClient(server_url)
    
    while True:
        print("\nDistributed Storage System Client")
        print("1. Upload a file")
        print("2. Download a file")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            print("\nEnter the path to the file you want to upload")
            print("Example: C:\\Users\\username\\Downloads\\file.txt")
            print("or: C:/Users/username/Downloads/file.txt")
            file_path = input("Path: ")
            
            if os.path.exists(file_path):
                result = client.upload_file(file_path)
                if result:
                    print(f"File uploaded successfully! Filename: {result['filename']}")
                    print(f"Number of shards: {result['num_shards']}")
            else:
                print(f"File not found at path: {file_path}")
        
        elif choice == "2":
            filename = input("Enter the filename to download: ")
            print("\nEnter where to save the file")
            print("Example: C:\\Users\\username\\Downloads")
            print("or: C:/Users/username/Downloads")
            output_path = input("Path: ")
            
            if client.download_file(filename, output_path):
                print("File downloaded and decrypted successfully!")
            else:
                print("Failed to download file.")
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 