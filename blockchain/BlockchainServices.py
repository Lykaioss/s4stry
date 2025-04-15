from __future__ import annotations
import json
import os
import hashlib

class Account:
    def __init__(self, username:str, balance: float):
        self.address = self._calc_address(username)
        self.balance = balance
        self._save_account()
    
    def _calc_address(self, username):
        return hashlib.sha256(username.encode()).hexdigest()
    
    def _save_account(self):
        # Read existing accounts
        accounts = {}
        if os.path.exists('wallets.json'):
            with open('wallets.json', 'r') as f:
                try:
                    accounts = json.load(f)
                except json.JSONDecodeError:
                    accounts = {}
        
        # Update or add account
        accounts[self.address] = self.balance
        
        # Write back to file
        with open('wallets.json', 'w') as f:
            json.dump(accounts, f, indent=4)
    

    def send_money(self, receiver: Account, amount: float):
        if self.balance < amount:
            raise ValueError("Insufficient balance")   
        self.balance -= amount
        self._save_account()
        # Update receiver.address's balance
        accounts = {}
        if os.path.exists('wallets.json'):
            with open('wallets.json', 'r') as f:
                try:
                    accounts = json.load(f)
                except json.JSONDecodeError:
                    accounts = {}
        receiver_balance = accounts.get(receiver.address, 0)
        accounts[receiver.address] = receiver_balance + amount
        
        with open('wallets.json', 'w') as f:
            json.dump(accounts, f, indent=4)


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
    class BlockFullException(Exception):
        pass

    def __init__(self, previous_hash: str | None, transactions: list[Transaction] = [], block_size: int = 3):
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.block_hash = ""
        self.block_size = block_size

    def calculate_block_hash(self):
        hash_string = ""
        for t in self.transactions:
            hash_string += t.receipt
        block_hash = json.dumps(hash_string, sort_keys=True)
        return hashlib.sha256(block_hash.encode()).hexdigest()


    def add_transaction(self, transaction: Transaction):
        if len(self.transactions) >= self.block_size:
            raise self.BlockFullException("Block is now full")
        
        self.transactions.append(transaction)

        if len(self.transactions) == self.block_size -1 :
            print("Block is full")
            self.block_hash = self.calculate_block_hash()
            self.show_block

    def show_block(self):
        print(self.__dict__)


class Blockchain:
    def __init__(self):
        self.chain:list[Block] = []

    def add_block(self, block: Block):
        self.chain.append(block.__dict__)
    
    def show_chain(self):
        print(self.__dict__)
        
    
if __name__ == "__main__":
    acc1 = Account("123", 100)
    acc2 = Account("456", 200)

    blockchain = Blockchain()
    genesis_block = Block(None)
    genesis_block.block_hash = "0000"

    blockchain.add_block(genesis_block)
    blockchain.show_chain()


    block1 = Block(previous_hash=genesis_block.block_hash)

    acc2.send_money(acc1, 50)
    tx1 = Transaction(acc2.address, acc1.address, 50)

    block1.add_transaction(tx1)

    acc1.send_money(acc2, 80)
    tx2 = Transaction(acc2.address, acc1.address, 50)

    block1.add_transaction(tx2)

    acc3 = Account("789", 400)
    acc3.send_money(acc1, 200)
    tx3 = Transaction(acc3.address, acc1.address, 200)

    block1.add_transaction(tx3)

    blockchain.add_block(block1)
    blockchain.show_chain()

    

