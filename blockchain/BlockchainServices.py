from __future__ import annotations
import json
import os
import hashlib
from datetime import datetime

class Account:
    def __init__(self, username:str, balance: float, create_new: bool = True):
        self.address = self._calc_address(username)
        self.balance = balance
        if create_new:
            self._save_account()
    
    def _calc_address(self, username):
        return hashlib.sha256(username.encode()).hexdigest()
    
    def _save_account(self):
        # Read existing blockchain
        blockchain = Blockchain()
        blockchain._load_chain()
        
        # Check if account already exists
        if self.address in blockchain.wallets:
            raise ValueError(f"Account with username '{self.username}' already exists")
        
        # Update or add account to blockchain's wallets
        blockchain.wallets[self.address] = self.balance
        
        # Save the updated blockchain
        blockchain._save_chain()

    def send_money(self, receiver: Account, amount: float):
        if self.balance < amount:
            raise ValueError("Insufficient balance")   
        self.balance -= amount
        
        # Update blockchain wallets
        blockchain = Blockchain()
        blockchain._load_chain()
        
        # Update sender's balance
        blockchain.wallets[self.address] = self.balance
        
        # Update receiver's balance
        receiver_balance = blockchain.wallets.get(receiver.address, 0)
        blockchain.wallets[receiver.address] = receiver_balance + amount
        
        # Save the updated blockchain
        blockchain._save_chain()


class Transaction:
    def __init__(self, sender: str, receiver: str, amount: float):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.receipt = self._create_receipt()
    
    def _create_receipt(self):
        receipt = self.sender + self.receiver + str(self.amount)
        return hashlib.sha256(receipt.encode()).hexdigest() 


class Block:
    BLOCK_SIZE = 3
    class BlockFullException(Exception):
        pass

    def __init__(self):
        self.previous_hash:str ="0" * 64
        self.timestamp:str = datetime.now().isoformat()
        self.index:int = 0
        self.block_hash = "****"
        self.transactions:list[Transaction] = []

    def calculate_block_hash(self):
        """Calculate the hash of the block based on its transactions and previous hash"""
        # Create a string with all transaction data
        transaction_data = ""
        if len(self.transactions) == Block.BLOCK_SIZE:
            for tx in self.transactions:
                transaction_data += f"{tx['sender']}{tx['receiver']}{tx['amount']}{tx['receipt']}"

        data_to_hash = f"{self.previous_hash}{self.index}{transaction_data}"
        
        return hashlib.sha256(data_to_hash.encode()).hexdigest()

    def add_transaction(self, transaction: Transaction):
        """Add a transaction to the block"""
        if len(self.transactions) >= Block.BLOCK_SIZE:
            raise self.BlockFullException("Block already full!")
        
        # Convert transaction to dict and add to block
        tx_dict = transaction.__dict__
        self.transactions.append(tx_dict)
        
        # If block is full, calculate its hash
        if len(self.transactions) == Block.BLOCK_SIZE:
            self.block_hash = self.calculate_block_hash()

    def show_block(self):
        """Print block information"""
        print(self.__dict__)


class Blockchain:
    def __init__(self):
        self.chain = []
        self.wallets = {}  # New wallets dictionary
        self._load_chain()
    
    def _load_chain(self):
        if os.path.exists('blockchain.json'):
            with open('blockchain.json', 'r') as f:
                try:
                    data = json.load(f)
                    self.chain = data.get('chain', [])
                    self.wallets = data.get('wallets', {})  # Load wallets from blockchain
                except json.JSONDecodeError:
                    self.chain = []
                    self.wallets = {}
    
    def _save_chain(self):
        data = {
            'chain': self.chain,
            'wallets': self.wallets  # Save wallets with blockchain
        }
        with open('blockchain.json', 'w') as f:
            json.dump(data, f, indent=4)

    def create_block(self) -> Block:
        """Create a new block with the given previous hash"""
        block = Block()
        block.previous_hash = self.get_previous_hash()
        block.index = len(self.chain)
        block.block_hash = block.calculate_block_hash()
        return block
    
    def add_block(self, block: Block):
        # Set the block index based on the current chain length
        self._load_chain()
        block.index = len(self.chain)
        self.chain.append(block.__dict__)
        self._save_chain()
    
    def get_previous_hash(self)->str:
        self._load_chain()
        if not self.chain:
            return None  
        latest_block = self.chain[-1]
        return latest_block["block_hash"]

    def show_chain(self):
        self._load_chain()
        print(self.__dict__)
        
    
if __name__ == "__main__":
    acc1 = Account("123", 100)
    acc2 = Account("456", 200)

    blockchain = Blockchain()

    genesis_block = Block()
    blockchain.add_block(genesis_block)

    # blockchain.show_chain()
    block1 = Block()

    acc2.send_money(acc1, 50)
    tx1 = Transaction(acc2.address, acc1.address, 50)
    block1.add_transaction(tx1)
    

    acc1.send_money(acc2, 80)
    tx2 = Transaction(acc1.address, acc2.address, 80)
    block1.add_transaction(tx2)

    acc3 = Account("789", 400)
    acc3.send_money(acc1, 200)
    tx3 = Transaction(acc3.address, acc1.address, 200)
    block1.add_transaction(tx3)

    blockchain.add_block(block1)

    block2 = Block()
    print(block2.__dict__)
    #print(block2.transactions)
    blockchain.add_block(block2)
    

