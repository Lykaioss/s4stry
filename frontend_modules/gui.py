from nicegui import ui
from client import StorageClient
from blockchain.BlockchainServices import Account
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variables
client = None
ui_elements = {}  # Store UI element references

async def create_client():
    """Initialize the StorageClient with user inputs and create action cards."""
    global client
    server_url = ui_elements["server_input"].value
    blockchain_url = ui_elements["blockchain_input"].value
    username = ui_elements["username_input"].value
    
    # Handle None or empty inputs
    server_url = server_url.strip() if server_url else "http://192.168.3.46:8000"
    blockchain_url = blockchain_url.strip() if blockchain_url else ""
    username = username.strip() if username else ""
    
    if not server_url or not username:
        ui.notify("Server URL and username cannot be empty!", type="negative")
        logger.error("Validation failed: Server URL or username empty")
        return
    
    # Disable inputs
    ui_elements["server_input"].disable()
    ui_elements["blockchain_input"].disable()
    ui_elements["username_input"].disable()
    ui_elements["submit_button"].disable()
    
    # Create loading dialog in main thread
    with ui_elements["dialog_container"]:
        loading_dialog = ui.dialog()
        with loading_dialog, ui.card():
            ui.spinner(size="lg")
            ui.label("Initializing client...")
        loading_dialog.open()
    
    try:
        logger.debug(f"Initializing StorageClient with username: {username}, server_url: {server_url}, blockchain_url: {blockchain_url}")
        client = StorageClient(username, server_url, blockchain_url)
        
        if blockchain_url:
            try:
                client.blockchain_address = client.create_blockchain_account(client.username)
                balance = client.get_blockchain_balance(client.blockchain_address)
                ui.notify(f"Client initialized!\nBlockchain address: {client.blockchain_address}\nBalance: {balance}", type="positive")
                logger.info(f"Blockchain account created: {client.blockchain_address}, balance: {balance}")
            except Exception as e:
                if isinstance(e, Account.AccountExists):
                    ui.notify("This username already exists. Please use a different username.", type="negative")
                    logger.warning(f"Blockchain account creation failed: Username {username} already exists")
                    # Re-enable inputs for retry
                    ui_elements["server_input"].enable()
                    ui_elements["blockchain_input"].enable()
                    ui_elements["username_input"].enable()
                    ui_elements["submit_button"].enable()
                    loading_dialog.close()
                    return
                else:
                    ui.notify(f"Error setting up blockchain account: {str(e)}\nBlockchain features will not be available", type="negative")
                    logger.error(f"Blockchain account setup failed: {str(e)}")
                    client.blockchain_conn = None
        else:
            ui.notify("Client initialized without blockchain connection.", type="positive")
            logger.info("Client initialized without blockchain connection")
        
        # Create action cards
        with ui_elements["dialog_container"]:
            create_action_cards()
        
    except Exception as e:
        ui.notify(f"Error initializing client: {str(e)}", type="negative")
        logger.error(f"Error initializing client: {str(e)}", exc_info=True)
        client = None
        # Re-enable inputs for retry
        ui_elements["server_input"].enable()
        ui_elements["blockchain_input"].enable()
        ui_elements["username_input"].enable()
        ui_elements["submit_button"].enable()
    finally:
        loading_dialog.close()

def create_action_cards():
    """Create UI cards for upload, retrieve, and blockchain operations."""
    # Clear existing action cards and UI elements
    ui_elements.clear()
    action_container.clear()
    
    # Re-add initialization elements to ui_elements
    ui_elements.update({
        "server_input": server_input,
        "blockchain_input": blockchain_input,
        "username_input": username_input,
        "submit_button": submit_button,
        "dialog_container": dialog_container
    })
    
    with action_container:
        # Upload card
        with ui.card():
            ui.label("Upload File")
            ui_elements["upload_input"] = ui.upload(
                label="Select file to upload",
                on_upload=lambda e: asyncio.create_task(upload_file(e))
            ).props("accept=*/*")
            ui_elements["duration_input"] = ui.number(
                label="Duration (minutes, minimum 1)",
                value=1,
                min=1,
                step=1,
                validation={"Duration must be at least 1": lambda value: value >= 1}
            )

        # Retrieve card
        with ui.card():
            ui.label("Retrieve File")
            ui_elements["retrieve_file_input"] = ui.input(
                label="File name",
                placeholder="Enter file name",
                validation={"File name cannot be empty": lambda value: bool(value.strip()) if value else False}
            )
            ui_elements["output_path_input"] = ui.input(
                label="Output path (optional)",
                placeholder="Enter save location or leave empty for default"
            ).props("clearable")
            ui_elements["retrieve_button"] = ui.button("Retrieve", on_click=lambda: asyncio.create_task(retrieve_file()))
            ui.button("List Unretrieved Files", on_click=lambda: asyncio.create_task(list_unretrieved_files()))

        # Blockchain card (only if blockchain is available)
        if client and client.blockchain_conn and client.blockchain_address:
            with ui.card():
                ui.label("Blockchain Operations")
                ui.button("Check Balance", on_click=lambda: asyncio.create_task(check_balance()))
                ui_elements["receiver_input"] = ui.input(
                    label="Receiver Address",
                    placeholder="Enter receiver's blockchain address",
                    validation={"Receiver address cannot be empty": lambda value: bool(value.strip()) if value else False}
                )
                ui_elements["amount_input"] = ui.number(
                    label="Amount",
                    value=0,
                    min=0,
                    step=0.1,
                    validation={"Amount must be positive": lambda value: value > 0}
                )
                ui_elements["send_payment_button"] = ui.button("Send Payment", on_click=lambda: asyncio.create_task(send_payment()))

async def upload_file(e):
    """Handle file upload with duration and cost calculation."""
    if not client:
        ui.notify("Client not initialized!", type="negative")
        logger.error("Upload attempted without initialized client")
        return
    
    file = e.content
    duration = ui_elements["duration_input"].value or 1
    
    if not file:
        ui.notify("No file selected!", type="negative")
        logger.error("No file selected for upload")
        return
    
    try:
        logger.debug(f"Uploading file: {file.name}, duration: {duration}")
        cost = client.calculate_storage_cost(file.name, duration)
        client.upload_file(file.name, cost, duration)
        ui.notify(f"File {file.name} uploaded successfully!", type="positive")
        logger.info(f"File {file.name} uploaded successfully")
        ui_elements["upload_input"].clear()
        ui_elements["duration_input"].value = 1
    except Exception as e:
        ui.notify(f"Error uploading file: {str(e)}", type="negative")
        logger.error(f"Error uploading file: {str(e)}")

async def retrieve_file():
    """Handle file retrieval."""
    if not client:
        ui.notify("Client not initialized!", type="negative")
        logger.error("Retrieve attempted without initialized client")
        return
    
    file_name = ui_elements["retrieve_file_input"].value
    output_path = ui_elements["output_path_input"].value
    
    file_name = file_name.strip() if file_name else ""
    output_path = output_path.strip() if output_path else ""
    
    if not file_name:
        ui.notify("Please enter a file name!", type="negative")
        logger.error("No file name provided for retrieval")
        return
    
    ui_elements["retrieve_button"].disable()
    try:
        logger.debug(f"Retrieving file: {file_name}, output_path: {output_path}")
        client.retrieve_file(file_name, output_path)
        ui.notify(f"File {file_name} retrieved successfully!", type="positive")
        logger.info(f"File {file_name} retrieved successfully")
        ui_elements["retrieve_file_input"].value = ""
        ui_elements["output_path_input"].value = ""
    except Exception as e:
        ui.notify(f"Error retrieving file: {str(e)}", type="negative")
        logger.error(f"Error retrieving file: {str(e)}")
    finally:
        ui_elements["retrieve_button"].enable()

async def list_unretrieved_files():
    """List unretrieved files."""
    if not client:
        ui.notify("Client not initialized!", type="negative")
        logger.error("List unretrieved files attempted without initialized client")
        return
    
    try:
        logger.debug("Listing unretrieved files")
        client.list_unretrieved_files()
        ui.notify("Unretrieved files listed in console.", type="positive")
        logger.info("Unretrieved files listed")
    except Exception as e:
        ui.notify(f"Error listing files: {str(e)}", type="negative")
        logger.error(f"Error listing files: {str(e)}")

async def check_balance():
    """Check blockchain balance."""
    if not client or not client.blockchain_conn or not client.blockchain_address:
        ui.notify("Blockchain not available!", type="negative")
        logger.error("Check balance attempted without blockchain connection")
        return
    
    try:
        logger.debug(f"Checking balance for address: {client.blockchain_address}")
        balance = client.get_blockchain_balance(client.blockchain_address)
        ui.notify(f"Your blockchain balance: {balance}", type="positive")
        logger.info(f"Balance checked: {balance}")
    except Exception as e:
        ui.notify(f"Error checking balance: {str(e)}", type="negative")
        logger.error(f"Error checking balance: {str(e)}")

async def send_payment():
    """Send blockchain payment."""
    if not client or not client.blockchain_conn or not client.blockchain_address:
        ui.notify("Blockchain not available!", type="negative")
        logger.error("Send payment attempted without blockchain connection")
        return
    
    receiver_address = ui_elements["receiver_input"].value
    amount = ui_elements["amount_input"].value
    
    receiver_address = receiver_address.strip() if receiver_address else ""
    amount = float(amount) if amount is not None else 0
    
    if not receiver_address or amount <= 0:
        ui.notify("Please enter a valid receiver address and amount!", type="negative")
        logger.error(f"Invalid payment details: receiver_address={receiver_address}, amount={amount}")
        return
    
    ui_elements["send_payment_button"].disable()
    try:
        logger.debug(f"Sending payment: {amount} to {receiver_address}")
        success = client.send_blockchain_payment(client.blockchain_address, receiver_address, amount)
        if success:
            balance = client.get_blockchain_balance(client.blockchain_address)
            ui.notify(f"Payment sent successfully!\nNew balance: {balance}", type="positive")
            logger.info(f"Payment sent successfully, new balance: {balance}")
            ui_elements["receiver_input"].value = ""
            ui_elements["amount_input"].value = 0
        else:
            ui.notify("Payment failed!", type="negative")
            logger.error("Payment failed")
    except Exception as e:
        ui.notify(f"Error sending payment: {str(e)}", type="negative")
        logger.error(f"Error sending payment: {str(e)}")
    finally:
        ui_elements["send_payment_button"].enable()

# Create the UI
ui.markdown("# Distributed Storage Client")

with ui.card():
    server_input = ui.input(
        label="Server URL",
        placeholder="e.g., 192.168.1.100:8000",
        value="http://192.168.3.46:8000",
        validation={"Server URL cannot be empty": lambda value: bool(value.strip()) if value else False}
    ).props("clearable")
    blockchain_input = ui.input(
        label="Blockchain Server URL (optional)",
        placeholder="e.g., 192.168.1.100:7575"
    ).props("clearable")
    username_input = ui.input(
        label="Username",
        placeholder="Enter your username",
        validation={"Username cannot be empty": lambda value: bool(value.strip()) if value else False}
    ).props("clearable")
    submit_button = ui.button("Initialize Client", on_click=lambda: asyncio.create_task(create_client()))
    dialog_container = ui.element("div")  # Container for dialogs and action cards

# Store initial UI elements
ui_elements.update({
    "server_input": server_input,
    "blockchain_input": blockchain_input,
    "username_input": username_input,
    "submit_button": submit_button,
    "dialog_container": dialog_container
})

# Container for action cards
action_container = ui.element("div")

# Run the NiceGUI app
ui.run(title="Storage Client", port=8080)