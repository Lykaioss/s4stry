import requests
import os
from pathlib import Path

class StorageClient:
    def __init__(self, server_url):
        """Initialize the client with the server URL."""
        self.server_url = server_url

    def upload_file(self, file_path):
        """Upload a file to the server."""
        try:
            # Remove quotes if present and normalize path
            file_path = file_path.strip('"').strip("'")
            file_path = os.path.normpath(file_path)
            
            if not os.path.exists(file_path):
                print(f"File not found at path: {file_path}")
                return None
                
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(f"{self.server_url}/upload/", files=files)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None

    def download_file(self, filename, output_path):
        """Download a file from the server."""
        try:
            # Remove quotes if present and normalize path
            output_path = output_path.strip('"').strip("'")
            output_path = os.path.normpath(output_path)
            
            # If output_path is a directory, append the filename
            if os.path.isdir(output_path):
                output_path = os.path.join(output_path, filename)
            
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
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
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
                print("File downloaded successfully!")
            else:
                print("Failed to download file.")
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 