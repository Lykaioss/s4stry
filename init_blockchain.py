from blockchain import Blockchain, Wallet, Miner

def initialize_blockchain():
    # Initialize blockchain
    blockchain = Blockchain()
    wallet = Wallet(blockchain)
    miner = Miner(blockchain, wallet)
    
    # Create test accounts
    test_accounts = [
        "client1",
        "renter1",
        "miner1"
    ]
    
    print("Creating test accounts...")
    for username in test_accounts:
        try:
            address = wallet.create_account(username)
            print(f"Created account for {username}: {address}")
        except ValueError as e:
            print(f"Error creating account for {username}: {e}")
    
    # Save blockchain state
    blockchain.save_to_file()
    print("\nBlockchain initialized and saved to file.")
    
    # Start mining
    print("\nStarting mining process...")
    try:
        miner.start_mining("miner1")
    except ValueError as e:
        print(f"Error starting mining: {e}")

if __name__ == "__main__":
    initialize_blockchain() 