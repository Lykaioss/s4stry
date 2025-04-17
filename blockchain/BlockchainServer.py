# rpc_server.py
import socket
import rpyc
from rpyc.utils.server import ThreadedServer
from BlockchainServices import Account, Transaction, Block, Blockchain
import json

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
        # Create genesis block
        genesis_block = Block()
        genesis_block.block_hash = "0000"
        self.blockchain.add_block(genesis_block)
    
    def exposed_create_account(self, username: str, initial_balance: float) -> str:
        """Create a new account and return its address"""
        try:
            account = Account(username, initial_balance)
            return account.address
        except Exception as e:
            raise Exception(f"Failed to create account: {str(e)}")
    
    def exposed_get_balance(self, address: str) -> float:
        """Get the balance of an account"""
        try:
            with open('wallets.json', 'r') as f:
                accounts = json.load(f)
                return accounts.get(address, 0)
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")
    
    def exposed_send_money(self, sender_address: str, receiver_address: str, amount: float) -> bool:
        """Send money from one account to another"""
        try:
            # Create temporary account objects for the transaction
            sender = Account("temp_sender", 0)
            sender.address = sender_address
            sender.balance = self.exposed_get_balance(sender_address)
            
            receiver = Account("temp_receiver", 0)
            receiver.address = receiver_address
            receiver.balance = self.exposed_get_balance(receiver_address)
            
            # Perform the transaction
            sender.send_money(receiver, amount)
            
            # Create and add transaction to a new block
            tx = Transaction(sender_address, receiver_address, amount)
            current_block = Block()
            current_block.add_transaction(tx)
            self.blockchain.add_block(current_block)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to send money: {str(e)}")
    
    def exposed_get_blockchain(self) -> dict:
        """Get the current state of the blockchain"""
        return self.blockchain.__dict__
    
    def exposed_get_latest_block(self) -> dict:
        """Get the latest block in the blockchain"""
        if not self.blockchain.chain:
            return {}
        return self.blockchain.chain[-1]


if __name__ == "__main__":
    SERVER_ADDR, SERVER_PORT = get_local_ip(), 7575
    server = ThreadedServer(RPyCServer, hostname=SERVER_ADDR, port=SERVER_PORT)
    print(f"Listening on {SERVER_ADDR}:{SERVER_PORT}")
    server.start()