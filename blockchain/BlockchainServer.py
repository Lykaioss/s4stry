# rpc_server.py
import socket
import rpyc
from rpyc.utils.server import ThreadedServer

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Try to get the IP address that can reach the internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback to localhost
        return "127.0.0.1"
    

class BlockchainService(rpyc.Service):
    def exposed_add(self, x, y):
        return x + y
    
    def exposed_get_balance(self, address):
        # TODO: Implement blockchain balance check
        return 0
    
    def exposed_send_transaction(self, sender, receiver, amount):
        # TODO: Implement blockchain transaction
        return True

if __name__ == "__main__":
    SERVER_ADDR, SERVER_PORT = get_local_ip(), 7575
    server = ThreadedServer(BlockchainService, hostname=SERVER_ADDR, port=SERVER_PORT)
    print(f"Listening on {SERVER_ADDR}:{SERVER_PORT}")
    server.start()