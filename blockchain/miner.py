import time
from typing import Optional
from .blockchain import Blockchain
from .wallet import Wallet

class Miner:
    def __init__(self, blockchain: Blockchain, wallet: Wallet):
        self.blockchain = blockchain
        self.wallet = wallet
        self.mining_interval = 60  # seconds
        self.is_mining = False

    def start_mining(self, miner_username: str):
        """Start the mining process."""
        if miner_username not in self.wallet.accounts:
            raise ValueError("Miner account not found")
            
        self.is_mining = True
        miner_address = self.wallet.accounts[miner_username]['address']
        
        while self.is_mining:
            if self.blockchain.pending_transactions:
                print("Mining new block...")
                self.blockchain.mine_pending_transactions(miner_address)
                print("Block mined successfully!")
                
            time.sleep(self.mining_interval)

    def stop_mining(self):
        """Stop the mining process."""
        self.is_mining = False

    def get_mining_status(self) -> dict:
        """Get current mining status and statistics."""
        return {
            'is_mining': self.is_mining,
            'pending_transactions': len(self.blockchain.pending_transactions),
            'block_height': len(self.blockchain.chain),
            'mining_interval': self.mining_interval
        } 