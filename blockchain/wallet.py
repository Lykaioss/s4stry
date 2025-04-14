import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from .blockchain import Blockchain, Transaction
import time

class Wallet:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.accounts: Dict[str, Dict] = {}
        self.load_accounts()

    def create_account(self, username: str) -> str:
        """Create a new account and return the address."""
        if username in self.accounts:
            raise ValueError("Username already exists")
            
        # Generate address from username and timestamp
        address = hashlib.sha256(f"{username}{os.urandom(16).hex()}".encode()).hexdigest()
        
        self.accounts[username] = {
            'address': address,
            'balance': self.blockchain.initial_balance,  # Set initial balance directly
            'created_at': os.path.getmtime(__file__)
        }
        
        # Add initial balance transaction
        initial_tx = Transaction(
            "SYSTEM",
            address,
            self.blockchain.initial_balance,
            time.time(),
            {"type": "initial_balance", "user_type": "new_account"}
        )
        
        # Add transaction and mine it immediately
        self.blockchain.add_transaction(initial_tx)
        self.blockchain.mine_pending_transactions()  # Mine the transaction immediately
        
        self.save_accounts()
        
        print(f"\n=== New Account Created ===")
        print(f"Username: {username}")
        print(f"Address: {address}")
        print(f"Initial Balance: {self.blockchain.initial_balance} sabudhana")
        
        return address

    def get_balance(self, username: str) -> float:
        """Get the current balance of an account."""
        if username not in self.accounts:
            raise ValueError("Account not found")
            
        address = self.accounts[username]['address']
        
        # Get balance from blockchain
        blockchain_balance = self.blockchain.get_balance(address)
        
        # Update local account balance
        self.accounts[username]['balance'] = blockchain_balance
        self.save_accounts()
        
        print(f"\n=== Account Balance ===")
        print(f"Username: {username}")
        print(f"Address: {address}")
        print(f"Balance: {blockchain_balance} sabudhana")
        
        return blockchain_balance

    def send_transaction(self, sender: str, receiver: str, amount: float, 
                        data: Optional[Dict] = None) -> bool:
        """Send sabudhana from one account to another."""
        if sender not in self.accounts or receiver not in self.accounts:
            raise ValueError("Invalid sender or receiver")
            
        sender_address = self.accounts[sender]['address']
        receiver_address = self.accounts[receiver]['address']
        
        # Check if sender has enough balance
        if self.get_balance(sender) < amount:
            raise ValueError("Insufficient balance")
            
        # Create and add transaction
        tx = Transaction(
            sender_address,
            receiver_address,
            amount,
            time.time(),
            data
        )
        
        success = self.blockchain.add_transaction(tx)
        
        if success:
            print(f"\n=== Transaction Sent ===")
            print(f"From: {sender} ({sender_address[:8]}...)")
            print(f"To: {receiver} ({receiver_address[:8]}...)")
            print(f"Amount: {amount} sabudhana")
            print(f"Status: Pending (will be processed in next block)")
        
        return success

    def create_storage_contract(self, client: str, renter: str, 
                              file_size: int, duration: int) -> str:
        """Create a storage contract between client and renter."""
        if client not in self.accounts or renter not in self.accounts:
            raise ValueError("Invalid client or renter")
            
        # Calculate price based on file size and duration
        # Price formula: 1 sabudhana per GB per hour
        price = (file_size / (1024 * 1024 * 1024)) * (duration / 3600)
        
        client_address = self.accounts[client]['address']
        renter_address = self.accounts[renter]['address']
        
        contract_id = self.blockchain.create_storage_contract(
            client_address,
            renter_address,
            file_size,
            duration,
            price
        )
        
        print(f"\n=== Storage Contract Created ===")
        print(f"Contract ID: {contract_id[:8]}...")
        print(f"Client: {client} ({client_address[:8]}...)")
        print(f"Renter: {renter} ({renter_address[:8]}...)")
        print(f"File Size: {file_size / (1024 * 1024):.2f} MB")
        print(f"Duration: {duration / 3600:.2f} hours")
        print(f"Price: {price:.2f} sabudhana")
        
        return contract_id

    def release_payment(self, contract_id: str) -> bool:
        """Release payment for a completed storage contract."""
        success = self.blockchain.release_payment(contract_id)
        
        if success:
            contract = self.blockchain.storage_contracts[contract_id]
            print(f"\n=== Payment Released ===")
            print(f"Contract ID: {contract_id[:8]}...")
            print(f"Amount: {contract['price']} sabudhana")
            print(f"From: {contract['client'][:8]}...")
            print(f"To: {contract['renter'][:8]}...")
        
        return success

    def save_accounts(self):
        """Save accounts to file."""
        with open('accounts.json', 'w') as f:
            json.dump(self.accounts, f, indent=4)

    def load_accounts(self):
        """Load accounts from file."""
        if Path('accounts.json').exists():
            with open('accounts.json', 'r') as f:
                self.accounts = json.load(f)

    def get_account_info(self, username: str) -> Dict:
        """Get account information including address and balance."""
        if username not in self.accounts:
            raise ValueError("Account not found")
            
        return {
            'username': username,
            'address': self.accounts[username]['address'],
            'balance': self.get_balance(username)
        } 