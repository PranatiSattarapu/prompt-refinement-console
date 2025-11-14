import streamlit as st
from drive_manager import list_data_files, get_drive_service
from workflow import generate_response # Assuming this is your Claude integration
st.write("Google key loaded:", "GOOGLE_SERVICE_ACCOUNT" in st.secrets)

service = get_drive_service()
st.write("Drive service object:", service)
# --- Streamlit Configuration ---
st.set_page_config(page_title="Health Tutor Console", layout="wide")
st.title("Prompt Refinement Console")

# --- 1. Initialize Session State for Multi-Session Chat ---
if "sessions" not in st.session_state:
    # Key is session name, value is the list of messages
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"

# --- Sidebar: Session Management ---
# st.sidebar.header("💬 Chat Session Management")

# # A. Session Selector
# session_names = list(st.session_state.sessions.keys())
# selected_session = st.sidebar.selectbox(
#     "Select or Create Session",
#     options=session_names + ["+ New Session"],
#     index=session_names.index(st.session_state.current_session) if st.session_state.current_session in session_names else 0
# )

# # B. Handle New Session Creation
# if selected_session == "+ New Session":
#     new_session_num = len(st.session_state.sessions) + 1
#     new_session_name = f"Session {new_session_num}"
#     st.session_state.sessions[new_session_name] = []
#     st.session_state.current_session = new_session_name
#     st.rerun()
# elif selected_session != st.session_state.current_session:
#     st.session_state.current_session = selected_session

# # C. Display Current Session Status
# st.sidebar.markdown(f"**Active Session:** **{st.session_state.current_session}**")

# # D. Clear Session Button
# if st.sidebar.button(f"🗑️ Clear **{st.session_state.current_session}** Chat"):
#     st.session_state.sessions[st.session_state.current_session] = []
#     st.rerun()

# st.sidebar.divider()

# --- Sidebar: Document Management (Read-Only) ---
st.sidebar.header("📂 Current Document Context")

# Fetch files from Drive (Read-only view)
files = list_data_files() 

if not files:
    st.sidebar.info("No documents found in the shared folder yet.")
else:
    # Note: We are just displaying the files, not allowing deletion from Drive here.
    st.sidebar.markdown("**Documents informing the context:**")
    for f in files:
        st.sidebar.markdown(f"📄 {f['name']}")

st.divider()

# --- Main Area: Chat Interface ---
# st.header(f"💬 Prompt Refinement: {st.session_state.current_session}")

# Get the messages for the active session
active_messages = st.session_state.sessions[st.session_state.current_session]

# 2. Display previous messages for the active session
for message in active_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Handle new query submission via st.chat_input
query = st.chat_input("Enter your medical question:")

if query:
    # --- A. Display User Message ---
    # Add user message to history
    active_messages.append({"role": "user", "content": query})
    # Display the user message immediately
    with st.chat_message("user"):
        st.markdown(query)

    # --- B. Get and Display Assistant Response ---
    with st.chat_message("assistant"):
        with st.spinner("Claude is thinking..."):
            # Pass the query to the workflow function
            answer = generate_response(query)
        
        # Display the final response
        st.markdown(answer)
        
    # --- C. Store Assistant Response ---
    # Add assistant message to history so it persists
    active_messages.append({"role": "assistant", "content": answer})

    # Update the session state with the modified active_messages list (important for dictionaries)
    st.session_state.sessions[st.session_state.current_session] = active_messages