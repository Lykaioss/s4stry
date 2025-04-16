import os
import shutil
from pathlib import Path

def reset_project():
    """Reset the blockchain and clean up related files."""
    # Files to delete
    files_to_delete = [
        "blockchain.json",
        "accounts.json",
        "wallets.json"
    ]

    directories_to_delete = [
        "S4S_Client",
        "S4S_Renter",
        "uploads"
    ]
    
    print("\n=== Blockchain Reset Tool ===")
    print("This will:")
    print("1. Delete blockchain.json")
    print("2. Delete accounts.json")
    print("3. Clear client directory")
    print("4. Clear renter directory")
    print("\nWARNING: This will permanently delete all blockchain data!")
    
    confirm = input("\nAre you sure you want to continue? (yes/no): ").lower()
    if confirm not in ['yes', 'y', '']:
        print("Reset cancelled.")
        return
    
    try:
        # Delete blockchain and accounts files
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}")
        
        # Clear client downloads
        for directory in directories_to_delete:
            print(f"Deleting {directory}")
            if os.path.exists(directory):
                shutil.rmtree(directory)
                print(f"Deleted {directory}")
        
        
        print("\nProject Reset Complete!")
        
    except Exception as e:
        print(f"Error during reset: {str(e)}")

if __name__ == "__main__":
    reset_project() 