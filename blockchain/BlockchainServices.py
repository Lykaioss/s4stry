from __future__ import annotations
import json
from operator import add
import os
import hashlib
from datetime import datetime
from turtle import st



class Account:

    class AccountExists(Exception):
        def __init__(self, address: str):
            self.address = address
            self.message = f"Account with address {self.address} already exists."
            super().__init__(self.message)  # Pass the message to the base Exception class

    def __init__(self, username: str, balance: float, create_new: bool = True):
        self.address = self._calc_address(username)
        self.balance = balance
        if create_new:
            if self.account_exists():
                raise self.AccountExists(address=self.address)  # Pass the address directly
            else:
                self._save_account()

    def _calc_address(self, username):
        return hashlib.sha256(username.encode()).hexdigest()

    def _load_wallets(self):
        """Load wallets from the blockchain.json file."""
        if os.path.exists("blockchain.json"):
            with open("blockchain.json", "r") as f:
                try:
                    data = json.load(f)
                    return data.get("wallets", {})
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_wallets(self, wallets):
        """Save wallets to the blockchain.json file."""
        if os.path.exists("blockchain.json"):
            with open("blockchain.json", "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Update the wallets field
        data["wallets"] = wallets

        # Save back to blockchain.json
        with open("blockchain.json", "w") as f:
            json.dump(data, f, indent=4)

    def account_exists(self) -> bool:
        """Check if the account exists in the wallets field of blockchain.json."""
        wallets = self._load_wallets()
        return self.address in wallets

    def _save_account(self):
        """Save the account to the wallets field in blockchain.json."""
        wallets = self._load_wallets()
        wallets[self.address] = self.balance
        self._save_wallets(wallets)

    def send_money(self, receiver: Account, amount: float):
        """Send money to another account."""
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self._save_account()

        # Update the receiver's balance
        wallets = self._load_wallets()
        receiver_balance = wallets.get(receiver.address, 0)
        wallets[receiver.address] = receiver_balance + amount
        self._save_wallets(wallets)


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
        self.chain: list[Block] = []
        self._load_chain()

    def _load_chain(self):
        if os.path.exists("blockchain.json"):
            with open("blockchain.json", "r") as f:
                try:
                    chain_data = json.load(f)
                    self.chain = chain_data.get("chain", [])
                except json.JSONDecodeError:
                    self.chain = []

    def _save_chain(self):
        if os.path.exists("blockchain.json"):
            with open("blockchain.json", "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Update the chain field
        data["chain"] = self.chain

        # Save back to blockchain.json
        with open("blockchain.json", "w") as f:
            json.dump(data, f, indent=4)

    def create_block(self) -> Block:
        """Create a new block with the given previous hash."""
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

    def get_previous_hash(self) -> str:
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
    acc2 = Account("123", 200)

