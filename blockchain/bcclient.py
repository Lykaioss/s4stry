# rpc_client.py
import rpyc

def main():
    ADDR, PORT = "192.168.137.61", 7575
    try:
        # Connect to the server
        print("Connecting to blockchain server...")
        conn = rpyc.connect(ADDR, PORT)
        
        # Create accounts
        print("\nCreating accounts...")
        alice_address = conn.root.exposed_create_account("alice", 1000.0)
        bob_address = conn.root.exposed_create_account("bob", 500.0)
        
        print(f"Alice's address: {alice_address}")
        print(f"Bob's address: {bob_address}")
        
        # Check initial balances
        print("\nChecking initial balances...")
        alice_balance = conn.root.exposed_get_balance(alice_address)
        bob_balance = conn.root.exposed_get_balance(bob_address)
        
        print(f"Alice's balance: {alice_balance}")
        print(f"Bob's balance: {bob_balance}")
        
        # Send money from Alice to Bob
        print("\nSending money from Alice to Bob...")
        amount = 200.0
        success = conn.root.exposed_send_money(alice_address, bob_address, amount)
        print(f"Transaction {'successful' if success else 'failed'}")
        
        # Check updated balances
        print("\nChecking updated balances...")
        alice_balance = conn.root.exposed_get_balance(alice_address)
        bob_balance = conn.root.exposed_get_balance(bob_address)
        
        print(f"Alice's new balance: {alice_balance}")
        print(f"Bob's new balance: {bob_balance}")
        
        # Get blockchain info
        print("\nGetting blockchain information...")
        blockchain = conn.root.exposed_get_blockchain()
        latest_block = conn.root.exposed_get_latest_block()
        
        print("Blockchain state:", blockchain)
        print("Latest block:", latest_block)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nConnection closed")

if __name__ == "__main__":
    main()
