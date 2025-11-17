import streamlit as st
from drive_manager import list_data_files
from workflow import generate_response

# --- Streamlit Configuration ---
st.set_page_config(page_title="Health Tutor Console", layout="wide")
st.title("Prompt Refinement Console")

# --- Initialize Session State ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {"Session 1": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Session 1"

# --- Sidebar: Document Management (Read-Only) ---
st.sidebar.header("📂 Current Document Context")

files = list_data_files()

if not files:
    st.sidebar.info("No documents found in the shared folder yet.")
else:
    st.sidebar.markdown("**Documents informing the context:**")
    for f in files:
        st.sidebar.markdown(f"📄 " + f["name"])

st.divider()

# --- Main Area: Chat Interface ---

active_messages = st.session_state.sessions[st.session_state.current_session]

# FIXED BOTTOM BAR CSS
st.markdown("""
<style>
.bottom-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    padding: 10px 20px 15px 20px;
    background: white;
    border-top: 1px solid #ddd;
    z-index: 999;
}

.chat-space {
    padding-bottom: 130px; /* EXACT height of bottom bar */
    margin-bottom: 0;
}
</style>
""", unsafe_allow_html=True)


# ---------------- CHAT HISTORY ----------------
st.markdown('<div class="chat-space">', unsafe_allow_html=True)

for message in active_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- FIXED BOTTOM BAR ----------------
st.markdown('<div class="bottom-bar">', unsafe_allow_html=True)

# Quick Questions
st.markdown("** Quick Questions**")

preset_questions = [
    "Prepare me for my doctor's visit",
    "What's my health summary?",
    "What should I ask my doctor?",
    "Summarize my recent metrics",
]

cols = st.columns(len(preset_questions))

if "preset_query" not in st.session_state:
    st.session_state.preset_query = None

for i, q in enumerate(preset_questions):
    if cols[i].button(q, key=f"preset_{i}"):
        st.session_state.preset_query = q
        st.rerun()

# Chat input (ALWAYS visible)
chatbox_input = st.chat_input("Enter your medical question:")

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- DECIDE QUERY ----------------
query = None

if st.session_state.preset_query:
    query = st.session_state.preset_query
    st.session_state.preset_query = None
elif chatbox_input:
    query = chatbox_input

# ---------------- PROCESS QUERY ----------------
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
