import streamlit as st
import os
from client import StorageClient
import time
from pathlib import Path
import tempfile
import json

# Configure Streamlit page
st.set_page_config(
    page_title="Distributed Storage System",
    page_icon="🗄️",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'client' not in st.session_state:
    st.session_state.client = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'payment_confirmed' not in st.session_state:
    st.session_state.payment_confirmed = False
if 'current_upload' not in st.session_state:
    st.session_state.current_upload = None

def save_username(username: str, keys_dir: Path) -> str:
    """Save username to user_data.json and return the username with nonce"""
    import random
    user_data_file = keys_dir / "user_data.json"
    
    nonce = random.randint(100000, 999999)
    username_with_nonce = f"{username}{nonce}"
    
    user_data = {
        "username": username_with_nonce,
        "upload_history": []
    }
    
    # Create keys directory if it doesn't exist
    keys_dir.mkdir(exist_ok=True)
    
    with open(user_data_file, 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return username_with_nonce

def init_client(server_url, username, blockchain_url=None):
    """Initialize the storage client and store it in session state"""
    try:
        # Create base client directory and keys directory
        base_dir = Path("S4S_Client")
        keys_dir = base_dir / "keys"
        base_dir.mkdir(exist_ok=True)
        keys_dir.mkdir(exist_ok=True)
        
        # Save username first
        username_with_nonce = save_username(username, keys_dir)
        st.session_state.username = username_with_nonce
        
        # Now initialize the client with the username
        st.session_state.client = StorageClient(
            server_url, 
            blockchain_server_url=blockchain_url if blockchain_url else None,
            username=username_with_nonce
        )
        st.session_state.connected = True

        # Check for blockchain connection error after initialization
        if blockchain_url and st.session_state.client.blockchain_connection_error:
            st.warning(f"Blockchain connection failed: {st.session_state.client.blockchain_connection_error}")

        return True
    except Exception as e:
        st.error(f"Failed to connect: {str(e)}")
        # Clear potentially partially initialized client state
        st.session_state.client = None
        st.session_state.connected = False
        st.session_state.username = None
        return False

def handle_payment_confirmation(cost, renter_address):
    """Handle payment confirmation through the GUI"""
    st.session_state.payment_confirmed = False
    st.session_state.current_upload = {
        'cost': cost,
        'renter_address': renter_address
    }
    return False  # Initial return, actual confirmation handled in UI

# Sidebar for connection settings
with st.sidebar:
    st.title("Connection Settings")
    
    # Server connection form
    with st.form("connection_form"):
        username = st.text_input("Username", help="Enter your desired username")
        server_url = st.text_input("Server URL", value="http://192.168.0.103:8000")
        blockchain_url = st.text_input("Blockchain Server URL (optional)", help="Enter IP or hostname, e.g., 192.168.1.100")
        
        connect_button = st.form_submit_button("Connect")
        if connect_button:
            if not username:
                st.error("Username is required!")
            else:
                # Store the provided blockchain_url in session state for later display
                st.session_state.provided_blockchain_url = blockchain_url
                if init_client(server_url, username, blockchain_url if blockchain_url else None):
                    st.success("Connected successfully!")
                    st.info(f"Your unique username is: {st.session_state.username}")
                    st.warning("Please remember the six trailing digits as your special key!")
                    if st.session_state.client and st.session_state.client.blockchain_address:
                        st.info(f"Blockchain Address: {st.session_state.client.blockchain_address}")
                        balance = st.session_state.client.get_blockchain_balance(st.session_state.client.blockchain_address)
                        st.info(f"Balance: {balance}")

    # Display connection status
    if st.session_state.connected and st.session_state.client:
        st.success("Status: Connected")
        st.success(f"Username: {st.session_state.username}")
        if st.session_state.client.blockchain_conn:
            st.success("Blockchain: Connected")
        else:
            # Check if a blockchain URL was provided during the last connection attempt
            if hasattr(st.session_state, 'provided_blockchain_url') and st.session_state.provided_blockchain_url:
                st.warning("Blockchain: Connection Failed")
                # Display the specific error message if available
                if st.session_state.client.blockchain_connection_error:
                    st.caption(f"Error: {st.session_state.client.blockchain_connection_error}")
            else:
                st.info("Blockchain: Not Specified")
    else:
        st.error("Status: Not Connected")

# Main content area
st.title("Distributed Storage System")

if st.session_state.connected and st.session_state.client:
    # Create tabs for different functionalities
    tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Retrieve", "Files", "Blockchain"])
    
    # Upload Tab
    with tab1:
        st.header("Upload File")
        
        # Payment confirmation section
        if hasattr(st.session_state, 'current_upload') and st.session_state.current_upload:
            st.info(f"Storage cost for this upload: {st.session_state.current_upload['cost']}")
            st.info(f"Renter address: {st.session_state.current_upload['renter_address']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Payment"):
                    st.session_state.payment_confirmed = True
                    st.session_state.current_upload = None
                    st.rerun()
            with col2:
                if st.button("Cancel Payment"):
                    st.session_state.payment_confirmed = False
                    st.session_state.current_upload = None
                    st.error("Upload cancelled")
                    st.rerun()
        
        # Regular upload section
        if not st.session_state.current_upload:
            uploaded_file = st.file_uploader("Choose a file", type=None)
            duration = st.number_input("Auto-retrieve duration (minutes)", min_value=0, value=0, 
                                     help="Set to 0 for no auto-retrieval")
            
            if uploaded_file and st.button("Upload"):
                try:
                    # Create a temporary directory to store the file
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir) / uploaded_file.name
                        
                        # Save the uploaded file
                        with open(temp_path, 'wb') as f:
                            f.write(uploaded_file.getvalue())
                        
                        # Get file size and check minimum requirement
                        file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
                        if file_size_mb < 5:
                            st.error(f"File size must be at least 5 MB. Current size: {file_size_mb:.2f} MB")
                            st.stop()  # Use st.stop() instead of return
                        
                        # Show upload progress
                        with st.spinner(f"Uploading file ({file_size_mb:.2f} MB)..."):
                            def payment_confirmation_callback(cost, renter_address):
                                if not st.session_state.payment_confirmed:
                                    handle_payment_confirmation(cost, renter_address)
                                    st.rerun()
                                return st.session_state.payment_confirmed
                            
                            try:
                                st.session_state.client.upload_file(
                                    str(temp_path),
                                    duration if duration > 0 else None,
                                    payment_confirmation_callback=payment_confirmation_callback
                                )
                                st.success(f"Successfully uploaded {uploaded_file.name}")
                                
                                # Show upload details
                                st.info("Upload Details:")
                                st.json({
                                    "File Name": uploaded_file.name,
                                    "Size": f"{file_size_mb:.2f} MB",
                                    "Auto-retrieve Duration": f"{duration} minutes" if duration > 0 else "None"
                                })
                                
                            except Exception as upload_error:
                                if "Payment cancelled by user" not in str(upload_error):
                                    st.error(f"Upload failed: {str(upload_error)}")
                                    st.error("Please check the following:")
                                    st.markdown("""
                                        - File size is at least 5 MB
                                        - You have sufficient blockchain balance (if payment required)
                                        - The server is accessible
                                        - The file format is supported
                                    """)
                                raise
                
                except Exception as e:
                    if "Payment cancelled by user" not in str(e):
                        st.error(f"Error during upload process: {str(e)}")
                        logger.error(f"Upload error: {str(e)}")
    
    # Retrieve Tab
    with tab2:
        st.header("Retrieve File")
        
        # Get list of unretrieved files
        try:
            user_data_file = st.session_state.client.keys_dir / "user_data.json"
            if user_data_file.exists():
                with open(user_data_file, 'r') as f:
                    import json
                    user_data = json.load(f)
                    unretrieved_files = [
                        upload["file_name"] 
                        for upload in user_data["upload_history"] 
                        if not upload.get("retrieved", False)
                    ]
            else:
                unretrieved_files = []
        except Exception:
            unretrieved_files = []
        
        if unretrieved_files:
            file_to_retrieve = st.selectbox("Select file to retrieve", unretrieved_files)
            output_path = st.text_input("Output path (optional)")
            
            if st.button("Retrieve"):
                try:
                    with st.spinner("Retrieving file..."):
                        st.session_state.client.retrieve_file(file_to_retrieve, output_path)
                    st.success(f"Successfully retrieved {file_to_retrieve}")
                except Exception as e:
                    st.error(f"Retrieval failed: {str(e)}")
        else:
            st.info("No files available for retrieval")
    
    # Files Tab
    with tab3:
        st.header("File Management")
        
        if st.button("Refresh File List"):
            st.session_state.client.list_unretrieved_files()
            
        # Display file history
        try:
            user_data_file = st.session_state.client.keys_dir / "user_data.json"
            if user_data_file.exists():
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
                    if user_data["upload_history"]:
                        st.subheader("Upload History")
                        for upload in user_data["upload_history"]:
                            with st.expander(f"{upload['file_name']} - {upload['timestamp']}"):
                                st.write(f"Size: {upload['file_size_mb']} MB")
                                st.write(f"Payment: {upload['payment']}")
                                st.write(f"Transaction: {upload['transaction_hash']}")
                                st.write(f"Retrieved: {'Yes' if upload['retrieved'] else 'No'}")
            else:
                st.info("No file history available")
        except Exception as e:
            st.error(f"Error loading file history: {str(e)}")
    
    # Blockchain Tab
    with tab4:
        if st.session_state.client.blockchain_conn and st.session_state.client.blockchain_address:
            st.header("Blockchain Operations")
            
            # Display account information
            st.subheader("Account Information")
            st.info(f"Account Address: {st.session_state.client.blockchain_address}")
            
            # Display current balance with refresh button
            col1, col2 = st.columns([3, 1])
            with col1:
                try:
                    balance = st.session_state.client.get_blockchain_balance(
                        st.session_state.client.blockchain_address
                    )
                    st.metric("Current Balance", f"{balance:.2f}")
                except Exception as e:
                    st.error(f"Failed to get balance: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh"):
                    try:
                        balance = st.session_state.client.get_blockchain_balance(
                            st.session_state.client.blockchain_address
                        )
                        st.metric("Current Balance", f"{balance:.2f}")
                    except Exception as e:
                        st.error(f"Failed to get balance: {str(e)}")
            
            # Send payment form
            st.subheader("Send Payment")
            with st.form("payment_form"):
                receiver = st.text_input("Receiver's Address")
                amount = st.number_input("Amount", min_value=0.0, step=0.1)
                
                if st.form_submit_button("Send Payment"):
                    if not receiver:
                        st.error("Please enter receiver's address")
                    elif amount <= 0:
                        st.error("Please enter a valid amount")
                    else:
                        try:
                            success = st.session_state.client.send_blockchain_payment(
                                st.session_state.client.blockchain_address,
                                receiver,
                                amount
                            )
                            if success:
                                st.success("Payment sent successfully!")
                                # Update balance after successful payment
                                new_balance = st.session_state.client.get_blockchain_balance(
                                    st.session_state.client.blockchain_address
                                )
                                st.info(f"New Balance: {new_balance:.2f}")
                        except Exception as e:
                            st.error(f"Payment failed: {str(e)}")
        else:
            st.warning("Blockchain features are not available.")
            if st.session_state.client.blockchain_connection_error:
                st.error(f"Connection Error: {st.session_state.client.blockchain_connection_error}")
            st.info("To use blockchain features, please connect to a blockchain server in the connection settings.")
else:
    st.warning("Please connect to a server using the sidebar settings.") 