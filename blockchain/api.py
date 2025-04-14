from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from .blockchain import Blockchain
from .wallet import Wallet
from .miner import Miner

router = APIRouter()

# Initialize blockchain components
blockchain = Blockchain.load_from_file()
wallet = Wallet(blockchain)
miner = Miner(blockchain, wallet)

@router.post("/accounts/create")
async def create_account(username: str):
    try:
        address = wallet.create_account(username)
        return {"username": username, "address": address}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/accounts/{username}")
async def get_account(username: str):
    try:
        return wallet.get_account_info(username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/transactions/send")
async def send_transaction(sender: str, receiver: str, amount: float):
    try:
        success = wallet.send_transaction(sender, receiver, amount)
        if success:
            return {"status": "success", "message": "Transaction added to pending transactions"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add transaction")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/contracts/create")
async def create_storage_contract(client: str, renter: str, file_size: int, duration: int):
    try:
        contract_id = wallet.create_storage_contract(client, renter, file_size, duration)
        return {
            "status": "success",
            "contract_id": contract_id,
            "message": "Storage contract created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/contracts/{contract_id}/release")
async def release_payment(contract_id: str):
    try:
        success = wallet.release_payment(contract_id)
        if success:
            return {"status": "success", "message": "Payment released successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to release payment")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/mining/start")
async def start_mining(miner_username: str):
    try:
        miner.start_mining(miner_username)
        return {"status": "success", "message": "Mining started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/mining/stop")
async def stop_mining():
    miner.stop_mining()
    return {"status": "success", "message": "Mining stopped"}

@router.get("/mining/status")
async def get_mining_status():
    return miner.get_mining_status()

@router.get("/blockchain/status")
async def get_blockchain_status():
    return {
        "block_height": len(blockchain.chain),
        "pending_transactions": len(blockchain.pending_transactions),
        "is_valid": blockchain.is_chain_valid()
    } 