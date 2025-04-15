# rpc_client.py
import rpyc

def main():
    ADDR, PORT = "192.168.0.217", 7575
    try:
        # Connect to the server
        conn = rpyc.connect(ADDR, PORT)
        
        # Call the add method
        result = conn.root.exposed_add(5, 3)
        print("Result:", result)
        
        # Example of getting balance
        balance = conn.root.exposed_get_balance("some_address")
        print("Balance:", balance)
        
        # Example of sending a transaction
        success = conn.root.exposed_send_transaction("sender_addr", "receiver_addr", 10)
        print("Transaction success:", success)
        
    except Exception as e:
        print(f"Error connecting to server: {e}")
    finally:
        # Close the connection
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
