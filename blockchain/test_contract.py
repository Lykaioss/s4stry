from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware
from eth_account import Account
import json
import os
from pathlib import Path
from dotenv import load_dotenv

def deploy_contract(w3, account, contract_path):
    """Deploy the StoragePayment contract to the network."""
    # Load contract bytecode and ABI
    with open(contract_path) as f:
        contract_json = json.load(f)
        bytecode = contract_json['bytecode']
        abi = contract_json['abi']
    
    # Create contract
    contract = w3.eth.contract(bytecode=bytecode, abi=abi)
    
    # Build transaction
    construct_txn = contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(construct_txn, account.key)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Get contract address
    contract_address = tx_receipt.contractAddress
    
    print(f"Contract deployed at: {contract_address}")
    return contract_address

def test_contract():
    # Load environment variables
    load_dotenv()
    
    # Connect to Sepolia testnet
    w3 = Web3(Web3.HTTPProvider(f'https://sepolia.infura.io/v3/{os.getenv("INFURA_PROJECT_ID")}'))
    
    # Check connection
    if not w3.is_connected():
        print("Failed to connect to network")
        return
    
    print("Connected to Sepolia testnet")
    
    # Create account from private key
    account = Account.from_key(os.getenv("PRIVATE_KEY"))
    
    # Add account to web3
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    
    print(f"\nUsing account: {account.address}")
    
    # Deploy contract
    print("\nDeploying contract...")
    contract_path = Path("contracts/StoragePayment.json")
    contract_address = deploy_contract(w3, account, contract_path)
    
    # Load contract ABI
    with open(contract_path) as f:
        contract_json = json.load(f)
        abi = contract_json['abi']
    
    # Create contract instance
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Test client registration
    print("\nTesting client registration...")
    tx = contract.functions.registerClient().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Client registration status: {receipt.status == 1}")
    
    # Test renter registration
    print("\nTesting renter registration...")
    tx = contract.functions.registerRenter().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Renter registration status: {receipt.status == 1}")
    
    # Mint test tokens
    print("\nMinting test tokens...")
    tx = contract.functions.mintTestTokens(account.address, 1000).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Token minting status: {receipt.status == 1}")
    
    # Check balance
    balance = contract.functions.balances(account.address).call()
    print(f"Account balance: {balance}")
    
    # Create storage agreement
    print("\nCreating storage agreement...")
    tx = contract.functions.createStorageAgreement(
        account.address,  # renter
        100,  # amount
        3600  # duration (1 hour)
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 300000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        # Get agreement ID from event logs
        event = contract.events.StorageAgreementCreated().process_receipt(receipt)
        if event:
            agreement_id = event[0]['args']['agreementId']
            print(f"Storage agreement created with ID: {agreement_id.hex()}")
            
            # Get agreement details
            agreement = contract.functions.getAgreement(agreement_id).call()
            print("\nAgreement details:")
            print(f"Client: {agreement[0]}")
            print(f"Renter: {agreement[1]}")
            print(f"Amount: {agreement[2]}")
            print(f"Start Time: {agreement[3]}")
            print(f"Duration: {agreement[4]}")
            print(f"Active: {agreement[5]}")
            print(f"Paid: {agreement[6]}")
            
            # Release payment
            print("\nReleasing payment...")
            tx = contract.functions.releasePayment(agreement_id).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': 200000,
                'gasPrice': w3.eth.gas_price
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx, account.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Payment release status: {receipt.status == 1}")
            
            # Check final balance
            final_balance = contract.functions.balances(account.address).call()
            print(f"\nFinal balance: {final_balance}")

if __name__ == "__main__":
    test_contract() 