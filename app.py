import streamlit as st
from drive_manager import list_data_files
from workflow import generate_response
from datetime import datetime

# --- Streamlit Configuration ---
st.set_page_config(page_title="Health Tutor Console", layout="wide")

# --- Custom CSS for Right Panel ---
# --- Custom CSS (merged theme) ---
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom styling */
    .stApp {
        background-color: white;
    }
    
    [data-testid="stSidebar"] {
        background-color: #EFEFEF;
        width: 20vw;
        min-width: 20vw;
    }
    
    [data-testid="stSidebar"][aria-expanded="true"] {
        width: 20vw;
        min-width: 20vw;
    }

    .stMain {
        padding-right: 20vw;
    }
    
    .main-container {
        background-color: white;
        padding: 2rem 3rem;
        border-radius: 10px;
        margin: 1rem;
        margin-right: 20vw;
    }
    
    .greeting-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1E1E1E;
        margin-bottom: 0.3rem;
    }
    
    .date-display {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    .action-button {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        font-size: 1.05rem;
        width: 100%;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s;
        color: #1E1E1E;
    }
    
    .action-button:hover {
        border-color: #4A90E2;
        box-shadow: 0 2px 8px rgba(74, 144, 226, 0.2);
    }
    
    .stButton > button {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        font-size: 1.05rem;
        width: 100%;
        color: #1E1E1E;
        transition: all 0.2s;
    }

    
    .stButton > button:hover {
        border-color: #4A90E2;
        box-shadow: 0 2px 8px rgba(74, 144, 226, 0.2);
        background: white;
    }
    
    .alert-box {
        background-color: #E3F2FD;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .alert-count {
        font-size: 2rem;
        color: #E74C3C;
        font-weight: 600;
    }
    
    .sidebar-section {
        margin-bottom: 2rem;
    }
    
    .chat-message {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .right-sidebar {
        background-color: #dceaf7;
        padding: 2rem 1.5rem;
        border-radius: 10px;
        min-height: 100vh;
    }

    .stAppHeader {
    display: none;
    }
    
    /* Apply background to the entire right column container */
    .element-container:has(.right-sidebar) {
        background-color: #dceaf7 !important;
    }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Force all normal text in the main content to be black */
div[data-testid="stVerticalBlock"] * {
    color: #1E1E1E !important;
}

/* Fix gray text inside preset buttons */
.stButton > button {
    color: #1E1E1E !important;
}

/* Fix chat bubbles text */
.stChatMessageContent p, .stChatMessageContent div {
    color: #1E1E1E !important;
}
</style>
""", unsafe_allow_html=True)



# st.title("Prompt Refinement Console")

# --- Initialize Session State ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"
if "preset_query" not in st.session_state:
    st.session_state.preset_query = None
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False


# --- Sidebar: Document Management (Read-Only) ---
# st.sidebar.header("📂 Current Document Context")
# if st.sidebar.button("🔍 Test Patient Data API"):
#     from workflow import fetch_patient_data
#     data = fetch_patient_data()
#     st.sidebar.write("API Returned:")
#     st.sidebar.json(data)

# files = list_data_files()

# if not files:
#     st.sidebar.info("No documents found in the shared folder yet.")
# else:
#     st.sidebar.markdown("**Documents informing the context:**")
#     for f in files:
#         st.sidebar.markdown(f"📄 " + f["name"])
with st.sidebar:
    st.markdown("<h3>💬 Chat History</h3>", unsafe_allow_html=True)


st.divider()

# --- Main Layout: Chat + Right Panel ---
# Greeting + Date

main_col, right_col = st.columns([8, 2])

with main_col:

    # Greeting + Date (THIS GOES HERE)
    today = datetime.now().strftime("%B %d, %Y")
    st.markdown(
    f"""
    <div style='text-align: left; margin-bottom: 20px;'>
        <h2 style='color: black; margin-bottom: 5px;'>Hello!</h2>
        <p style='font-size: 18px; color: gray;'>{today}</p>
    </div>
    """,
    unsafe_allow_html=True
)



    active_messages = st.session_state.sessions[st.session_state.current_session]

    for message in active_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    preset_questions = [
        "📅 Give me my 30-day health report",
        "🏥 Help me prepare for my Care Provider visit",
        "❤️ Give me my heart health status",
        "📄 Explain my alerts",
    ]

    if "preset_query" not in st.session_state:
        st.session_state.preset_query = None

    # Center the buttons using columns
    left_col = st.container()

    with left_col:
        for i, q in enumerate(preset_questions):
            if st.button(q, key=f"preset_{i}", use_container_width=True):
                st.session_state.preset_query = q
                st.rerun()


    # Decide final query
    query = None
    if st.session_state.preset_query:
        query = st.session_state.preset_query
        st.session_state.preset_query = None

    # PROCESS QUERY
    if query:
        active_messages.append({"role": "user", "content": query})

        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Claude is thinking..."):
                answer = generate_response(query)

            st.markdown(answer)

        active_messages.append({"role": "assistant", "content": answer})
        st.session_state.sessions[st.session_state.current_session] = active_messages

# Right panel CSS (shown on all screens)
st.markdown("""
<style>
.right-panel {
    position: fixed;
    top: 0px; 
    right: 0px;
    width: 20vw;
    background: #dceaf7;
    padding: 2rem 1.5rem;
    box-shadow: 0px 3px 10px rgba(0,0,0,0.2);
    z-index: 999;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}

.right-panel .alert-section {
    background-color: #dceaf7;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 3rem;
    width: 100%;
}

.right-panel .alert-icon {
    font-size: 3rem;
    margin-bottom: 0.5rem;
}

.right-panel .alert-count {
    font-size: 2rem;
    color: #E74C3C;
    font-weight: 600;
}

.right-panel .action-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 2rem;
    font-size: 1.1rem;
    color: #1E1E1E;
    font-weight: 500;
    width: 100%;
}

.right-panel .action-icon {
    font-size: 2rem;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)
# Right panel HTML (shown on all screens)
st.markdown("""
<div class="right-panel">
    <div class="alert-section">
        <div class="alert-icon">📢</div>
        <div class="alert-count">2 Alerts</div>
    </div>
    <div class="action-item">
        <div class="action-icon">🔬</div>
        <span>Share with Carepod</span>
    </div>
    <div class="action-item">
        <div class="action-icon">📸</div>
        <span>Add Health Photos</span>
    </div>
    <div class="action-item">
        <div class="action-icon">📊</div>
        <span>View Dashboard</span>
    </div>
</div>
""", unsafe_allow_html=True)
