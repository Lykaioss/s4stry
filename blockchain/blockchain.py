import hashlib
import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    timestamp: float
    data: Dict[str, Any] = None

    def to_dict(self) -> dict:
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'data': self.data
        }

    def is_valid(self) -> bool:
        """Validate the transaction."""
        # Check if required fields are present
        if not all([self.sender, self.receiver, self.amount is not None]):
            return False
            
        # Check if amount is positive
        if self.amount <= 0:
            return False
            
        # For SYSTEM transactions (initial balance), skip balance check
        if self.sender == "SYSTEM":
            return True
            
        return True

class Block:
    def __init__(self, index: int, transactions: List[Transaction], timestamp: float, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int):
        while self.hash[:difficulty] != '0' * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = 2
        self.mining_reward = 10.0
        self.storage_contracts: Dict[str, Dict] = {}  # Contract ID -> Contract data
        self.initial_balance = 1000.0  # Initial balance for new accounts
        
        # Create genesis block if chain is empty
        if not self.chain:
            self.create_genesis_block()
            self.save_blockchain()

    def create_genesis_block(self):
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def save_blockchain(self):
        """Save the current state of the blockchain to file."""
        try:
            self.save_to_file()
            print("Blockchain state saved successfully")
        except Exception as e:
            print(f"Error saving blockchain: {e}")

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a new transaction to the pending transactions list."""
        try:
            # Verify transaction
            if not transaction.is_valid():
                print(f"Invalid transaction: {transaction.to_dict()}")
                return False
                
            # For initial balance transactions, mine immediately
            if transaction.sender == "SYSTEM" and transaction.data and transaction.data.get("type") == "initial_balance":
                print(f"Processing initial balance transaction for {transaction.receiver}")
                self.pending_transactions.append(transaction)
                success = self.mine_pending_transactions()
                if success:
                    print(f"Initial balance of {transaction.amount} sabudhana added for {transaction.receiver}")
                return success
                
            # For regular transactions, check sender balance
            if transaction.sender != "SYSTEM":
                balance = self.get_balance(transaction.sender)
                if balance < transaction.amount:
                    print(f"Insufficient balance: {balance} < {transaction.amount}")
                    return False
                
            # Add to pending transactions
            print(f"Adding transaction: {transaction.amount} sabudhana from {transaction.sender} to {transaction.receiver}")
            self.pending_transactions.append(transaction)
            return True
            
        except Exception as e:
            print(f"Error adding transaction: {e}")
            return False

    def mine_pending_transactions(self, miner_address: str = "SYSTEM") -> bool:
        """Mine pending transactions and add them to the blockchain."""
        try:
            if not self.pending_transactions:
                print("No pending transactions to mine")
                return False
                
            # Create new block with pending transactions
            new_block = Block(
                len(self.chain),
                self.pending_transactions,
                time.time(),
                self.chain[-1].hash if self.chain else "0" * 64
            )
            
            # Mine the block
            print("Mining new block...")
            new_block.mine_block(self.difficulty)
            
            # Add block to chain
            self.chain.append(new_block)
            
            # Clear pending transactions
            self.pending_transactions = []
            
            # Save blockchain state
            self.save_blockchain()
            
            print(f"\n=== New Block Mined ===")
            print(f"Block Height: {len(self.chain)}")
            print(f"Transactions: {len(new_block.transactions)}")
            print(f"Block Hash: {new_block.hash[:8]}...")
            print(f"Miner: {miner_address[:8]}...")
            
            return True
            
        except Exception as e:
            print(f"Error mining transactions: {e}")
            return False

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address:
                    balance -= tx.amount
                if tx.receiver == address:
                    balance += tx.amount
        return balance

    def create_storage_contract(self, client_address: str, renter_address: str, 
                              file_size: int, duration: int, price: float) -> str:
        """Create a new storage contract between client and renter."""
        try:
            # Validate inputs
            if not all([client_address, renter_address, file_size > 0, duration > 0, price > 0]):
                print("Invalid contract parameters")
                return ""
                
            # Check if client has enough balance
            client_balance = self.get_balance(client_address)
            if client_balance < price:
                print(f"Client has insufficient balance: {client_balance} < {price}")
                return ""
            
            contract_id = hashlib.sha256(f"{client_address}{renter_address}{time.time()}".encode()).hexdigest()
            
            contract = {
                'id': contract_id,
                'client': client_address,
                'renter': renter_address,
                'file_size': file_size,
                'duration': duration,
                'price': price,
                'created_at': time.time(),
                'status': 'pending',
                'payment_released': False
            }
            
            self.storage_contracts[contract_id] = contract
            self.save_blockchain()  # Save after creating contract
            
            print(f"\n=== Storage Contract Created ===")
            print(f"Contract ID: {contract_id[:8]}...")
            print(f"Client: {client_address[:8]}...")
            print(f"Renter: {renter_address[:8]}...")
            print(f"Price: {price} sabudhana")
            
            return contract_id
            
        except Exception as e:
            print(f"Error creating storage contract: {e}")
            return ""

    def release_payment(self, contract_id: str) -> bool:
        """Release payment for a completed storage contract."""
        try:
            if not contract_id:
                print("Invalid contract ID")
                return False
                
            if contract_id not in self.storage_contracts:
                print(f"Contract not found: {contract_id}")
                return False
                
            contract = self.storage_contracts[contract_id]
            
            if contract['payment_released']:
                print(f"Payment already released for contract {contract_id[:8]}...")
                return False
                
            # Create transaction to release payment
            tx = Transaction(
                contract['client'],
                contract['renter'],
                contract['price'],
                time.time(),
                {'type': 'storage_payment', 'contract_id': contract_id}
            )
            
            # Add and mine the transaction
            if self.add_transaction(tx):
                contract['payment_released'] = True
                contract['status'] = 'completed'
                self.save_blockchain()  # Save after updating contract
                
                print(f"\n=== Payment Released ===")
                print(f"Contract: {contract_id[:8]}...")
                print(f"Amount: {contract['price']} sabudhana")
                print(f"From: {contract['client'][:8]}...")
                print(f"To: {contract['renter'][:8]}...")
                return True
            else:
                print("Failed to process payment transaction")
                return False
                
        except Exception as e:
            print(f"Error releasing payment: {e}")
            return False

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            if current_block.hash != current_block.calculate_hash():
                return False
                
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True

    def save_to_file(self, filename: str = "blockchain.json"):
        data = {
            'chain': [{
                'index': block.index,
                'timestamp': block.timestamp,
                'transactions': [tx.to_dict() for tx in block.transactions],
                'previous_hash': block.previous_hash,
                'nonce': block.nonce,
                'hash': block.hash
            } for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'storage_contracts': self.storage_contracts
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_from_file(cls, filename: str = "blockchain.json") -> 'Blockchain':
        if not Path(filename).exists():
            return cls()
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        blockchain = cls()
        blockchain.chain = []
        blockchain.pending_transactions = []
        blockchain.storage_contracts = data.get('storage_contracts', {})
        
        for block_data in data['chain']:
            transactions = [
                Transaction(
                    tx['sender'],
                    tx['receiver'],
                    tx['amount'],
                    tx['timestamp'],
                    tx.get('data')
                ) for tx in block_data['transactions']
            ]
            
            block = Block(
                block_data['index'],
                transactions,
                block_data['timestamp'],
                block_data['previous_hash']
            )
            block.nonce = block_data['nonce']
            block.hash = block_data['hash']
            
            blockchain.chain.append(block)
            
        blockchain.pending_transactions = [
            Transaction(
                tx['sender'],
                tx['receiver'],
                tx['amount'],
                tx['timestamp'],
                tx.get('data')
            ) for tx in data['pending_transactions']
        ]
        
        return blockchain 

    def print_blockchain_status(self):
        """Print a clear overview of the blockchain status."""
        print("\n=== Blockchain Status ===")
        print(f"Block Height: {len(self.chain)}")
        print(f"Pending Transactions: {len(self.pending_transactions)}")
        print(f"Storage Contracts: {len(self.storage_contracts)}")
        print("\nRecent Transactions:")
        for block in self.chain[-3:]:  # Show last 3 blocks
            print(f"\nBlock {block.index}:")
            for tx in block.transactions:
                if tx.sender == "SYSTEM":
                    print(f"  SYSTEM -> {tx.receiver[:8]}...: {tx.amount} sabudhana (Initial balance)")
                else:
                    print(f"  {tx.sender[:8]}... -> {tx.receiver[:8]}...: {tx.amount} sabudhana")
        print("\nActive Storage Contracts:")
        for contract_id, contract in list(self.storage_contracts.items())[:3]:  # Show first 3 contracts
            print(f"\nContract {contract_id[:8]}...:")
            print(f"  Client: {contract['client'][:8]}...")
            print(f"  Renter: {contract['renter'][:8]}...")
            print(f"  Price: {contract['price']} sabudhana")
            print(f"  Status: {contract['status']}")
            print(f"  Payment Released: {contract['payment_released']}") 