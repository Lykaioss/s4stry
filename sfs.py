import click
import json
import rpyc
from pathlib import Path
from client import StorageClient

# Global client instance
client = None
user_data_file = Path("S4S_Client/keys/user_data.json")


def load_client_from_user_data():
    """Load the client instance from user_data.json if available."""
    global client
    if user_data_file.exists():
        try:
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
            server_url = user_data.get("server_url")
            blockchain_url = user_data.get("blockchain_url")
            if server_url:
                client = StorageClient(server_url, blockchain_url)
                click.echo(f"Loaded client from user_data.json: {server_url}")
                if blockchain_url:
                    try:
                        client.blockchain_conn = client.connect_to_blockchain(blockchain_url)
                        client.blockchain_address = client.create_blockchain_account(client.username)
                        click.echo(f"Reconnected to blockchain server: {blockchain_url}")
                        click.echo(f"Blockchain address: {client.blockchain_address}")
                    except Exception as e:
                        click.echo(f"Error reconnecting to blockchain server: {e}")
                        client.blockchain_conn = None
        except Exception as e:
            click.echo(f"Error loading client from user_data.json: {e}")


def save_client_to_user_data(server_url, blockchain_url):
    """Save the server_url and blockchain_url to user_data.json."""
    try:
        if user_data_file.exists():
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {"username": "cal", "upload_history": []}

        # Update server and blockchain details
        user_data["server_url"] = server_url
        user_data["blockchain_url"] = blockchain_url

        # Save back to the file
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
        click.echo("Server and blockchain details saved to user_data.json.")
    except Exception as e:
        click.echo(f"Error saving client details to user_data.json: {e}")


@click.group()
def cli():
    """Distributed Storage Client CLI."""
    load_client_from_user_data()


@cli.command()
@click.option('--server-url', prompt='Enter the server URL (e.g., http://192.168.1.100:8000)', help='The URL of the storage server.')
@click.option('--blockchain-url', default=None, help='The URL of the blockchain server (optional).')
def setup(server_url, blockchain_url):
    """Set up the client by connecting to the storage and blockchain servers."""
    global client
    client = StorageClient(server_url, blockchain_url)
    click.echo(f"Connected to storage server: {server_url}")
    if blockchain_url:
        try:
            client.blockchain_address = client.create_blockchain_account(client.username)
            click.echo(f"Connected to blockchain server: {blockchain_url}")
            click.echo(f"Blockchain address: {client.blockchain_address}")
            balance = client.get_blockchain_balance(client.blockchain_address)
            click.echo(f"Blockchain balance: {balance}")
        except Exception as e:
            click.echo(f"Error connecting to blockchain server: {e}")
            client.blockchain_conn = None

    # Save the details to user_data.json
    save_client_to_user_data(server_url, blockchain_url)


def ensure_client_initialized():
    """Ensure the client is initialized and connected to the servers before executing any command."""
    global client
    if client is None:
        # Attempt to load the client from user_data.json
        load_client_from_user_data()

    if client is None:
        raise click.UsageError("Client is not initialized. Run the 'setup' command first.")

    # Reconnect to the blockchain server if necessary
    if not client.blockchain_conn:
        try:
            # Reconnect to the blockchain server using the saved blockchain URL
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
            blockchain_url = user_data.get("blockchain_url")
            if blockchain_url:
                client.blockchain_conn = client.connect_to_blockchain(blockchain_url)
                client.blockchain_address = client.create_blockchain_account(client.username)
                click.echo(f"Reconnected to blockchain server: {blockchain_url}")
                click.echo(f"Blockchain address: {client.blockchain_address}")
        except Exception as e:
            click.echo(f"Error reconnecting to blockchain server: {e}")
            client.blockchain_conn = None


@cli.command()
@click.argument('file_path', type=str)
@click.option('--duration', default=0, help='Duration in minutes after which to automatically retrieve the file (0 for no auto-retrieval).')
def upload(file_path, duration):
    """Upload a file to the storage system."""
    ensure_client_initialized()

    # Convert the input string to a Path object
    file_path = Path(file_path)

    # Check if the path exists
    if not file_path.exists():
        click.echo(f"Error: The specified path '{file_path}' does not exist.")
        return

    # Check if the path is a file
    if not file_path.is_file():
        click.echo(f"Error: The specified path '{file_path}' is not a file.")
        return

    try:
        client.upload_file(str(file_path), duration)
        click.echo(f"File '{file_path}' uploaded successfully.")
    except Exception as e:
        click.echo(f"Error uploading file: {e}")


@cli.command()
@click.argument('file_name')
@click.option('--output-path', default=None, help='Path to save the retrieved file (default: downloads directory).')
def retrieve(file_name, output_path):
    """Retrieve a file from the storage system."""
    ensure_client_initialized()
    try:
        client.download_file(file_name, output_path)
        click.echo(f"File '{file_name}' retrieved successfully.")
    except Exception as e:
        click.echo(f"Error retrieving file: {e}")


@cli.command()
def list_unretrieved():
    """List all files that haven't been retrieved yet."""
    ensure_client_initialized()
    try:
        client.list_unretrieved_files()
    except Exception as e:
        click.echo(f"Error listing unretrieved files: {e}")


@cli.command()
def check_balance():
    """Check the blockchain account balance."""
    ensure_client_initialized()
    if not client.blockchain_conn or not client.blockchain_address:
        click.echo("Blockchain server not connected.")
        return
    try:
        balance = client.get_blockchain_balance(client.blockchain_address)
        click.echo(f"Blockchain balance: {balance}")
    except Exception as e:
        click.echo(f"Error checking balance: {e}")


@cli.command()
@click.argument('receiver_address')
@click.argument('amount', type=float)
def send_payment(receiver_address, amount):
    """Send a blockchain payment."""
    ensure_client_initialized()
    if not client.blockchain_conn or not client.blockchain_address:
        click.echo("Blockchain server not connected.")
        return
    try:
        success = client.send_blockchain_payment(client.blockchain_address, receiver_address, amount)
        if success:
            click.echo(f"Payment of {amount} sent to {receiver_address} successfully.")
            balance = client.get_blockchain_balance(client.blockchain_address)
            click.echo(f"New balance: {balance}")
    except Exception as e:
        click.echo(f"Error sending payment: {e}")


def connect_to_blockchain(self, blockchain_url: str):
    """Connect to the blockchain server."""
    try:
        connection = rpyc.connect(blockchain_url.split(":")[0], int(blockchain_url.split(":")[1]))
        return connection
    except Exception as e:
        raise Exception(f"Failed to connect to blockchain server at {blockchain_url}: {e}")


if __name__ == '__main__':
    cli()