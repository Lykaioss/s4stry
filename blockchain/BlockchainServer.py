# rpc_server.py
import socket
import rpyc
from rpyc.utils.server import ThreadedServer
from BlockchainServices import Account, Transaction, Blockchain
import json
from datetime import datetime
import os

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Try to get the IP address that can reach the internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback to localhost
        return "127.0.0.1"
    

class RPyCServer(rpyc.Service):
    def __init__(self):
        super().__init__()
        self.blockchain = Blockchain()
        # Create genesis block if the blockchain is empty
        if not self.blockchain.chain:
            genesis_block = self.blockchain.create_block()
            self.blockchain.add_block(genesis_block)
        # Load the current block or create a new one
        self.load_current_block()

    def exposed_create_account(self, username: str, initial_balance: float) -> str:
        """Create a new account and return its address."""
        try:
            account = Account(username, initial_balance)
            return account.address
        except Exception as e:
            raise Exception(f"Failed to create account: {str(e)}")

    def exposed_get_balance(self, address: str) -> float:
        """Get the balance of an account."""
        try:
            accounts = {}
            if os.path.exists('wallets.json'):
                with open('wallets.json', 'r') as f:
                    accounts = json.load(f)
            return accounts.get(address, 0.0)
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")

    def exposed_send_money(self, sender_address: str, receiver_address: str, amount: float) -> dict:
        """Send money from one account to another and return a transaction receipt."""
        try:
            # Create temporary account objects for the transaction
            sender = Account("temp_sender", 0, create_new=False)
            sender.address = sender_address
            sender.balance = self.exposed_get_balance(sender_address)

            receiver = Account("temp_receiver", 0, create_new=False)
            receiver.address = receiver_address
            receiver.balance = self.exposed_get_balance(receiver_address)

            # Perform the transaction
            sender.send_money(receiver, amount)

            # Create a new transaction
            tx = Transaction(sender_address, receiver_address, amount)

            # Add the transaction to the current block
            try:
                self.current_block.add_transaction(tx)
                # If the block is full, add it to the blockchain and create a new block
                if len(self.current_block.transactions) == self.current_block.BLOCK_SIZE:
                    self.blockchain.add_block(self.current_block)
                    self.current_block = self.blockchain.create_block()
            except self.current_block.BlockFullException:
                # If the block is full, add it to the blockchain and create a new block
                self.blockchain.add_block(self.current_block)
                self.current_block = self.blockchain.create_block()
                # Add the transaction to the new block
                self.current_block.add_transaction(tx)

            # Save the current block to a file
            self.save_current_block()

            # Generate a transaction receipt
            receipt = {
                "transaction_hash": tx.receipt,
                "sender": sender_address,
                "receiver": receiver_address,
                "amount": amount,
                "timestamp": datetime.now().isoformat()
            }
            return receipt

        except Exception as e:
            raise Exception(f"Failed to send money: {str(e)}")

    def exposed_get_blockchain(self) -> dict:
        """Get the current state of the blockchain."""
        self.blockchain._load_chain()  # Ensure the latest chain is loaded
        return {"chain": self.blockchain.chain}

    def exposed_get_latest_block(self) -> dict:
        """Get the latest block in the blockchain."""
        self.blockchain._load_chain()  # Ensure the latest chain is loaded
        if not self.blockchain.chain:
            return {}
        return self.blockchain.chain[-1]

    def exposed_get_current_block(self) -> dict:
        """Get the current block with pending transactions."""
        return self.current_block.__dict__

    def save_current_block(self) -> None:
        """Save the current block to a JSON file."""
        try:
            with open("current_block.json", "w") as f:
                json.dump(self.current_block.__dict__, f, indent=4)
            print("Current block saved to file.")
        except Exception as e:
            print(f"Failed to save current block: {e}")

    def load_current_block(self) -> None:
        """Load the current block from a JSON file."""
        try:
            if os.path.exists("current_block.json"):
                with open("current_block.json", "r") as f:
                    block_data = json.load(f)
                self.current_block = self.blockchain.create_block()
                self.current_block.__dict__.update(block_data)
                print("Current block loaded from file.")
            else:
                print("No saved current block found. Creating a new block.")
                self.current_block = self.blockchain.create_block()
        except Exception as e:
            print(f"Failed to load current block: {e}")
            self.current_block = self.blockchain.create_block()


if __name__ == "__main__":
    SERVER_ADDR, SERVER_PORT = get_local_ip(), 7575
    server = ThreadedServer(RPyCServer, hostname=SERVER_ADDR, port=SERVER_PORT)
    print(f"Listening on {SERVER_ADDR}:{SERVER_PORT}")
    server.start()