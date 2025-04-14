import json
import os
from pathlib import Path
from solcx import compile_source, install_solc

def compile_contract():
    # Install solc
    install_solc('0.8.0')
    
    # Read contract source
    contract_path = Path("contracts/StoragePayment.sol")
    with open(contract_path) as f:
        contract_source = f.read()
    
    # Compile contract
    compiled_sol = compile_source(
        contract_source,
        output_values=['abi', 'bin'],
        solc_version='0.8.0'
    )
    
    # Get contract data
    contract_id, contract_interface = compiled_sol.popitem()
    bytecode = contract_interface['bin']
    abi = contract_interface['abi']
    
    # Create output directory if it doesn't exist
    output_dir = Path("contracts")
    output_dir.mkdir(exist_ok=True)
    
    # Save compiled contract
    output_path = output_dir / "StoragePayment.json"
    with open(output_path, 'w') as f:
        json.dump({
            'abi': abi,
            'bytecode': bytecode
        }, f, indent=2)
    
    print(f"Contract compiled and saved to {output_path}")

if __name__ == "__main__":
    compile_contract() 