from nicegui import ui, events
from client import StorageClient  # Assuming client.py is in the same directory
from blockchain.BlockchainServices import Account
from starlette.formparsers import MultiPartParser  # used for efficiently handling large files
import traceback

version = "1.0.0"
MultiPartParser.max_file_size = 1024 * 1024 * 1024 * 10  # 10 GB

client = None
uploaded_file_path = None
blockchain_balance = None



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
            blockchain_balance_label.text = f"{balance}"
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

def fetch_unretrieved_files(container):
        if client is None:
            ui.notify("Client not initialized.", color="negative")
            return
        try:
            files = client.list_unretrieved_files()
            container.clear()  # Clear the previous list
            # if files:
            #     for file in files:
            #         container.add(ui.label(file))

            if files:
                with unretrieved_files_list:
                    for file in files:
                        ui.item(str(file))
            else:
                container.add(ui.label("No unretrieved files found."))
        except Exception as e:
            ui.notify(f"Error: {e}", color="negative")
            print(traceback.format_exc())

def pay_user(receiver, amount):
    if client is None:
        ui.notify("Client not initialized.", color="negative")
        return
    try:
        if amount <= 0:
            ui.notify("Amount must be greater than 0.", color="negative")
            return
        if not receiver:
            ui.notify("Receiver cannot be empty.", color="negative")
            return

        success = client.send_blockchain_payment(client.blockchain_address, receiver, amount)
        if success:
            ui.notify("Payment sent successfully")
            balance = client.get_blockchain_balance(client.blockchain_address)
            blockchain_balance_label.text = f"{balance}"
            print(f"Your new balance: {balance}")
        
    except Exception as e:
        ui.notify(f"Error: {e}", color="negative")
        print(traceback.format_exc())

# GUI Layout
ui.label('Storage Client GUI').style('font-size: 64px; font-weight: bold; color: #333;')
ui.label('Upload and Retrieve Files').style('font-size: 18px; color: #555;')

# First row: Client Initialization card centered
with ui.row().classes('justify-center'):
    with ui.card():
        ui.label('Client Initialization')
        server_url = ui.input('Server URL (default if empty)').props('filled')
        blockchain_url = ui.input('Blockchain Server URL').props('filled')
        username = ui.input('Username').props('filled')
        ui.button('Connect', on_click=lambda: initialize_client(server_url.value, blockchain_url.value, username.value))

# Second row onwards: Remaining cards in groups of 3
with ui.column().classes('w-full'):
    with ui.row().classes('justify-around'):
        with ui.card():
            ui.label('Upload a File').style('font-size: 32px;')
            upload_duration = ui.input('Duration in minutes (default 1)').props('filled')
            ui.upload(label="Select a file", multiple=False, auto_upload=True, on_upload=save_tmp_file).props('accept="*/*"')
            cost_label = ui.label('Cost: N/A')
            ui.button('Upload File', on_click=lambda: upload_file(uploaded_file_path, upload_duration.value))

        with ui.card():
            ui.label('Retrieve a File').style('font-size: 32px;')
            retrieve_filename = ui.input('Filename to retrieve').props('filled')
            retrieve_output_path = ui.input('Output path (optional)').props('filled')
            ui.button('Retrieve File', on_click=lambda: retrieve_file(retrieve_filename.value, retrieve_output_path.value))

        with ui.card():
            ui.label('Unretrieved Files').style('font-size: 32px;')
            unretrieved_files_list = ui.list().props('dense separator')  # Container to display the list of files
            ui.button('Fetch Unretrieved Files', on_click=lambda: fetch_unretrieved_files(unretrieved_files_list))

        with ui.card():
            ui.label('Blockchain').style('font-size: 32px;')
            with ui.row(align_items="baseline").classes('justify-around'):
                ui.label('Balance:')
                blockchain_balance_label = ui.label('N/A').style('font-size: 20px; font-weight: bold; color: #16cc68;')
            ui.button('Get Balance', on_click=show_balance)
            receiver_address = ui.input('Receiver Address').props('filled')
            amount = ui.input('Amount to send').props('filled')
            ui.button('Make Payment', on_click=lambda:pay_user(receiver_address.value, float(amount.value)))


ui.add_head_html('''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cal+Sans&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Hubot+Sans:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">
    <style>
        * {
            font-family: 'Hubot Sans', sans-serif;
        }
    </style>
''')

ui.run(title=f"S4S Client v{version}", dark=True, port=8080, reload=True, favicon='🚀',)
