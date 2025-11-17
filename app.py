import streamlit as st
from drive_manager import list_data_files, get_drive_service, api_get_files_in_folder, FOLDER_ID_PATIENT_DATA
from workflow import generate_response # Assuming this is your Claude integration

# --- Streamlit Configuration ---
st.set_page_config(page_title="Health Tutor Console", layout="wide")
st.title("Prompt Refinement Console")

# --- Custom CSS Injection for Fixed Footer and Scrollable History ---
st.markdown("""
<style>
/* 1. Make the chat history container scrollable and set max height */
/* The height is calculated to fill the space above the fixed footer */
.scrollable-chat-history {
    max-height: calc(100vh - 220px); 
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 10px; /* Space for the scrollbar */
}

/* 2. Style for the fixed container at the bottom */
.st-fixed-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    background-color: #ffffff; /* Match Streamlit's background */
    padding: 10px 0;
    border-top: 1px solid #e6e6e6;
    /* Streamlit's main content area often has a max-width, this wrapper ensures content aligns */
}

/* 3. Wrapper to center the content within the fixed footer */
.fixed-content-wrapper {
    max-width: 730px; /* Adjust this to match Streamlit's default main content width */
    margin-left: auto;
    margin-right: auto;
    padding: 0 1rem; /* Padding inside the wrapper */
}

/* 4. Add padding to the main content block to prevent overlap with the fixed footer */
/* Targeting a common Streamlit block container class for global padding */
div.block-container {
    padding-bottom: 200px; /* Ensure space for the fixed bottom area (presets + chatbox) */
}

/* Hide the native sticky chat input that Streamlit might try to render separately */
.stChatInput {
    position: static !important;
}

</style>
""", unsafe_allow_html=True)


# --- 1. Initialize Session State for Multi-Session Chat ---
if "sessions" not in st.session_state:
    # Key is session name, value is the list of messages
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"

active_messages = st.session_state.sessions[st.session_state.current_session]

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

# -------------------- CHAT HISTORY (SCROLLABLE AREA) --------------------

# Start the scrollable chat history div
st.markdown('<div class="scrollable-chat-history">', unsafe_allow_html=True)

# Render all messages
for message in active_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# End the scrollable chat history div
st.markdown('</div>', unsafe_allow_html=True)


# -------------------- FIXED BOTTOM AREA (Presets + Chatbox) --------------------
# Start the fixed footer wrapper
st.markdown('<div class="st-fixed-footer"><div class="fixed-content-wrapper">', unsafe_allow_html=True)

st.markdown("### Quick Questions")

preset_questions = [
    "Prepare me for my doctor's visit",
    "What's my health summary?",
    "What should I ask my doctor?",
    "Summarize my recent metrics",
]

cols = st.columns(len(preset_questions))

# Track clicked preset question
if "preset_query" not in st.session_state:
    st.session_state.preset_query = None

for i, q in enumerate(preset_questions):
    if cols[i].button(q, key=f"preset_btn_{i}"): # Added key for stability
        st.session_state.preset_query = q
        # Ensure the view scrolls to the top of the history when a preset is clicked
        st.rerun()

# Always show chatbox
chatbox_input = st.chat_input("Enter your medical question:")

# Close the fixed footer wrapper
st.markdown('</div></div>', unsafe_allow_html=True)


# -------------------- DECIDE FINAL QUERY & PROCESS --------------------
query = None

if st.session_state.preset_query:
    query = st.session_state.preset_query
    st.session_state.preset_query = None
elif chatbox_input:
    query = chatbox_input

# -------------------- PROCESS QUERY --------------------
if query:
    active_messages.append({"role": "user", "content": query})

    # The user message must be shown in the history area (which will be re-rendered on rerun)
    # Rerunning immediately handles showing the user query in the scrollable history

    with st.chat_message("assistant"):
        with st.spinner("Claude is thinking..."):
            answer = generate_response(query)
        st.markdown(answer)

    active_messages.append({"role": "assistant", "content": answer})

    st.session_state.sessions[st.session_state.current_session] = active_messages
    st.rerun() # Rerun to update the entire chat history in the scrollable container