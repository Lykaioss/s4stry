import os
import shutil
from pathlib import Path

def reset_blockchain():
    """Reset the blockchain and clean up related files."""
    # Files to delete
    files_to_delete = [
        "blockchain.json",
        "accounts.json",
        "S4S_Client/downloads",
        "S4S_Renter/storage"
    ]
    
    print("\n=== Blockchain Reset Tool ===")
    print("This will:")
    print("1. Delete blockchain.json")
    print("2. Delete accounts.json")
    print("3. Clear client downloads")
    print("4. Clear renter storage")
    print("\nWARNING: This will permanently delete all blockchain data!")
    
    confirm = input("\nAre you sure you want to continue? (yes/no): ").lower()
    if confirm not in ['yes', 'y', '']:
        print("Reset cancelled.")
        return
    
    try:
        # Delete blockchain and accounts files
        for file in files_to_delete[:2]:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}")
        
        # Clear client downloads
        if os.path.exists(files_to_delete[2]):
            shutil.rmtree(files_to_delete[2])
            os.makedirs(files_to_delete[2])
            print("Cleared client downloads")
        
        # Clear renter storage
        if os.path.exists(files_to_delete[3]):
            shutil.rmtree(files_to_delete[3])
            os.makedirs(files_to_delete[3])
            print("Cleared renter storage")
        
        print("\nBlockchain reset complete!")
        print("You can now start fresh with new blockchain data.")
        
    except Exception as e:
        print(f"Error during reset: {str(e)}")

if __name__ == "__main__":
    reset_blockchain() 