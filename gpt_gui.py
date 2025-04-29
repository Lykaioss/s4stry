from nicegui import ui, events
from client import StorageClient  # Assuming client.py is in the same directory
from blockchain.BlockchainServices import Account
from starlette.formparsers import MultiPartParser # used for efficiently handling large files
import traceback

MultiPartParser.max_file_size = 1024 * 1024 * 1024 * 10  # 10 GB

client = None
uploaded_file_path = None

def initialize_client(server_url, blockchain_url, username):
    global client
    try:
        if not server_url:
            server_url = "http://192.168.3.46:8000"

        if not username:
            ui.notify("Username cannot be empty.", color="negative")
            return

        client = StorageClient(username, server_url, blockchain_url)
        ui.notify(f"Client initialized for {username}")

        # Create blockchain account if blockchain URL is provided
        if blockchain_url:
            try:
                client.blockchain_address = client.create_blockchain_account(client.username)
                balance = client.get_blockchain_balance(client.blockchain_address)
                client.set_or_get_blockchain_address(client.blockchain_address)
                ui.notify(f"Blockchain address created.\nAddress: {client.blockchain_address}\nBalance: {balance}")
            except Exception as e:
                if isinstance(e, Account.AccountExists):
                    ui.notify("Username already exists on blockchain. Please use a different username.", color="warning")
                else:
                    ui.notify(f"Blockchain setup error: {str(e)}", color="warning")
                    client.blockchain_conn = None  # Disable blockchain features

    except Exception as e:
        ui.notify(f"Error: {e}", color="negative")
        print(traceback.format_exc())

def upload_file(file_path, duration):
    if client is None:
        ui.notify("Client not initialized.", color="negative")
        return
    try:
        duration = int(duration) if duration else 1
        if duration < 0:
            ui.notify("Duration must be 0 or greater.", color="negative")
            return

        cost = client.calculate_storage_cost(file_path, duration)
        client.upload_file(file_path, cost, duration)
        ui.notify("File uploaded successfully")
    except Exception as e:
        ui.notify(f"Error: {e}", color="negative")
        print(traceback.format_exc())

def update_cost_label():
    if client is None or not uploaded_file_path or not uploaded_file_path.exists():
        cost_label.text = "Cost: N/A"
        return
    try:
        duration = int(upload_duration.value) if upload_duration.value else 1
        print(f"Duration taken: {duration}")
        cost = client.calculate_storage_cost(str(uploaded_file_path), duration)
        cost_label.text = f"Cost: {cost}"
    except Exception as e:
        cost_label.text = f"Error: {e}"

    except Exception as e:
        ui.notify(f"Error: {e}", color="negative")
        print(traceback.format_exc())

def retrieve_file(file_name, output_path):
    if client is None:
        ui.notify("Client not initialized.", color="negative")
        return
    try:
        if not file_name:
            ui.notify("File name cannot be empty.", color="negative")
            return
        client.retrieve_file(file_name, output_path)
        ui.notify("File retrieved successfully")
    except Exception as e:
        ui.notify(f"Error: {e}", color="negative")
        print(traceback.format_exc())

def show_balance():
    if client and client.blockchain_conn and client.blockchain_address:
        try:
            balance = client.get_blockchain_balance(client.blockchain_address)
            ui.notify(f"Balance: {balance}")
        except Exception as e:
            ui.notify(f"Error: {e}", color="negative")
            print(traceback.format_exc())
    else:
        ui.notify("Blockchain not connected.", color="warning")

def save_tmp_file(e: events.UploadEventArguments):
    global uploaded_file_path

    if client is None:
        ui.notify("Client not initialized.", color="negative")
        return

    # Ensure upload dir exists
    temp_dir = client.temp_dir

    # Save file manually
    uploaded_file_path = temp_dir / e.name
    try:
        with open(uploaded_file_path, "wb") as f:
            f.write(e.content.read())
        ui.notify(f"Saved file: {uploaded_file_path}")
        update_cost_label()
    except Exception as ex:
        ui.notify(f"Failed to save file: {ex}", color="negative")
        uploaded_file_path = None



# GUI Layout
ui.label('Storage Client GUI').style('font-size: 64px; font-weight: bold; color: #333;')
ui.label('Upload and Retrieve Files').style('font-size: 18px; color: #555;')
with ui.card():
    ui.label('Client Initialization')
    server_url = ui.input('Server URL (default if empty)').props('filled')
    blockchain_url = ui.input('Blockchain Server URL (optional)').props('filled')
    username = ui.input('Username').props('filled')
    ui.button('Initialize Client', on_click=lambda: initialize_client(server_url.value, blockchain_url.value, username.value))

with ui.card():
    ui.label('Upload a File')
    upload_duration = ui.input('Duration in minutes (default 1)').props('filled')
    ui.upload(label="Select a file", multiple=False, auto_upload=True, on_upload=save_tmp_file).props('accept="*/*"')
    cost_label = ui.label('Cost: N/A')
    ui.button('Upload File', on_click=lambda: upload_file(uploaded_file_path, upload_duration.value))

with ui.card():
    ui.label('Retrieve a File')
    retrieve_filename = ui.input('Filename to retrieve').props('filled')
    retrieve_output_path = ui.input('Output path (optional)').props('filled')
    ui.button('Retrieve File', on_click=lambda: retrieve_file(retrieve_filename.value, retrieve_output_path.value))

with ui.card():
    ui.label('Blockchain')
    ui.button('Show Blockchain Balance', on_click=show_balance)

ui.run()
