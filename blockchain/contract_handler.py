from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import os
from pathlib import Path
from typing import Dict, Tuple

class ContractHandler:
    def __init__(self, contract_address: str, abi_path: str):
        # Connect to Sepolia testnet
        self.w3 = Web3(Web3.HTTPProvider('https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID'))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Load contract ABI
        with open(abi_path) as f:
            contract_abi = json.load(f)
        
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
        
        # Test accounts with high balances for development
        self.test_accounts = {
            'client1': {
                'address': '0x123...',  # Replace with actual test account address
                'private_key': '0x...'  # Replace with actual private key
            },
            'renter1': {
                'address': '0x456...',  # Replace with actual test account address
                'private_key': '0x...'  # Replace with actual private key
            }
        }
    
    def register_client(self, client_address: str) -> bool:
        """Register a client on the blockchain."""
        try:
            tx = self.contract.functions.registerClient().build_transaction({
                'from': client_address,
                'nonce': self.w3.eth.get_transaction_count(client_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                self.test_accounts['client1']['private_key']
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt.status == 1
        except Exception as e:
            print(f"Error registering client: {str(e)}")
            return False
    
    def register_renter(self, renter_address: str) -> bool:
        """Register a renter on the blockchain."""
        try:
            tx = self.contract.functions.registerRenter().build_transaction({
                'from': renter_address,
                'nonce': self.w3.eth.get_transaction_count(renter_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                self.test_accounts['renter1']['private_key']
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt.status == 1
        except Exception as e:
            print(f"Error registering renter: {str(e)}")
            return False
    
    def create_storage_agreement(
        self,
        client_address: str,
        renter_address: str,
        amount: int,
        duration: int
    ) -> Tuple[bool, str]:
        """Create a storage agreement on the blockchain."""
        try:
            tx = self.contract.functions.createStorageAgreement(
                renter_address,
                amount,
                duration
            ).build_transaction({
                'from': client_address,
                'nonce': self.w3.eth.get_transaction_count(client_address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                self.test_accounts['client1']['private_key']
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                # Get the agreement ID from the event logs
                event = self.contract.events.StorageAgreementCreated().process_receipt(receipt)
                if event:
                    return True, event[0]['args']['agreementId'].hex()
            return False, ""
        except Exception as e:
            print(f"Error creating storage agreement: {str(e)}")
            return False, ""
    
    def release_payment(self, client_address: str, agreement_id: str) -> bool:
        """Release payment to the renter after successful file retrieval."""
        try:
            tx = self.contract.functions.releasePayment(
                bytes.fromhex(agreement_id.replace('0x', ''))
            ).build_transaction({
                'from': client_address,
                'nonce': self.w3.eth.get_transaction_count(client_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                self.test_accounts['client1']['private_key']
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt.status == 1
        except Exception as e:
            print(f"Error releasing payment: {str(e)}")
            return False
    
    def get_agreement_status(self, agreement_id: str) -> Dict:
        """Get the status of a storage agreement."""
        try:
            result = self.contract.functions.getAgreement(
                bytes.fromhex(agreement_id.replace('0x', ''))
            ).call()
            
            return {
                'client': result[0],
                'renter': result[1],
                'amount': result[2],
                'startTime': result[3],
                'duration': result[4],
                'isActive': result[5],
                'isPaid': result[6]
            }
        except Exception as e:
            print(f"Error getting agreement status: {str(e)}")
            return {}
    
    def get_balance(self, address: str) -> int:
        """Get the token balance of an address."""
        try:
            return self.contract.functions.balances(address).call()
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
            return 0 