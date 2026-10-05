import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from uuid import uuid4
from langchain_bot.auth import authenticate_user
from langchain_bot.agent import get_agent
from langchain_bot.rag_tool import initialize_vector_store
import json
from src.langchain_bot.agent import get_agent, get_thread_config, reset_agent
from langchain_bot.gmail_tools import initialize_gmail, is_gmail_available

THREADS_FILE = None

def get_llm() -> ChatOpenAI:
    """Get the language model."""
    llm = ChatOpenAI(
        model_name=os.environ["MODEL_NAME"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.3
    )
    return llm

def build_chain(llm):
    """Build the chat chain."""
    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="history"),
        ("system",  "You are a concise, helpful assistant. Use prior chat history to stay on context."),
        ("human", "{input}")
    ])
    return prompt | llm

def init_session():
    """Initialize the session state with login and multi-thread tracking."""
    st.session_state.setdefault("conversations", {})
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("user_role", None)
    st.session_state.setdefault("vector_store_ready", False)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("conversation_id", None)
    st.session_state.setdefault("gmail_enabled", False)

def render_history():
    """Render the chat history."""
    config = get_thread_config(st.session_state.user_email, st.session_state.conversation_id)
    snapshot = get_agent().get_state(config)
    for msg in snapshot.values.get("messages", []):
        if msg.type == "human":
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif msg.type == "ai" and msg.content:
            with st.chat_message("assistant"):
                st.markdown(msg.content)
    
def chat_round(user_input):
    """Handle a single round of chat."""
    get_agent().invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config=get_thread_config(st.session_state.user_email, st.session_state.conversation_id)
    )

def start_new_conversation():
    conversation_id = str(uuid4())
    add_thread(st.session_state.user_email, conversation_id)
    st.session_state.conversation_id = conversation_id
    # initial_msgs = [AIMessage(content="Hi! Ask me anything.")]
    # st.session_state.messages = initial_msgs
    # st.session_state.conversations[conversation_id] = initial_msgs

def load_conversation(conv_id: str):
    """Load a specific conversation thread into the active session state."""
    if conv_id in st.session_state.conversations:
        st.session_state.conversation_id = conv_id
        st.session_state.messages = st.session_state.conversations[conv_id]

def load_threads(user_email: str) -> list:
    """Load the metadata list of conversation structures associated with a specific email account."""
    if not os.path.exists(THREADS_FILE):
        return []
    try:
        with open(THREADS_FILE, "r") as f:
            data = json.load(f)
            return data.get(user_email, [])
    except Exception:
        return []

def save_threads(user_email: str, threads: list):
    """Save the full metadata profile record collection mapping for the target identity string."""
    data = {}
    if os.path.exists(THREADS_FILE):
        try:
            with open(THREADS_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    data[user_email] = threads
    with open(THREADS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_thread(user_email: str, conversation_id: str):
    """Register a new conversational reference node profile tracking element without storing text."""
    threads = load_threads(user_email)
    # Deduplicate check
    if not any(t["id"] == conversation_id for t in threads):
        threads.append({
            "id": conversation_id,
            "label": f"Chat {conversation_id[:8]}"
        })
        save_threads(user_email, threads)

def main():
    st.set_page_config(page_title="LangChain Bot", page_icon="🤖")
    st.title("LangChain Bot")
    st.caption("A simple chatbot using LangChain.")

    load_dotenv()
    init_session()
    global THREADS_FILE
    if not THREADS_FILE:
        THREADS_FILE = "chat_threads.json"

    if not st.session_state.gmail_enabled:
        if is_gmail_available():
            st.session_state.gmail_enabled = True
        else:
            st.session_state.gmail_enabled = initialize_gmail()

    if not st.session_state.vector_store_ready:
        with st.spinner("Initializing knowledge base..."):
            try:
                initialize_vector_store()
                st.session_state.vector_store_ready = True
                st.success("Vector store initialized successfully!")
            except Exception as e:
                st.error(f"Failed to initialize knowledge base: {e}")
                st.stop()

    user_email = st.session_state.user_email

    if not user_email:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["customer", "admin"])
            submit = st.form_submit_button("Login")
            if submit:
                if authenticate_user(email, password, role):
                    st.session_state.user_email = email
                    st.session_state.user_role = role
                    user_threads = load_threads(email)
                    if user_threads:
                        st.session_state.conversation_id = user_threads[-1]["id"]
                    else:
                        start_new_conversation()
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or role.")
        return

    with st.sidebar:
        st.header("Conversations")

        if st.button("Start new conversation"):
            start_new_conversation()
            st.rerun()

        user_threads = load_threads(st.session_state.user_email)

        if not user_threads:
            st.selectbox("Thread", options=["(no threads yet)"], disabled=True)
        else:
            thread_ids = [t["id"] for t in user_threads]
            try:
                current_index = thread_ids.index(st.session_state.conversation_id)
            except ValueError:
                current_index = 0

            selected_id = st.selectbox("Thread", options=thread_ids, index=current_index, format_func=lambda x: next(t["label"] for t in user_threads if t["id"] == x))
            
            if selected_id != st.session_state.conversation_id:
                st.session_state.conversation_id = selected_id
                st.rerun()

        st.write("---")
        st.header("System Integrations")
        if st.session_state.gmail_enabled:
            st.success("🟢 Gmail: Enabled")
        else:
            st.warning("🟡 Gmail: Not Configured")
            if st.button("Retry Gmail Connection"):
                st.session_state.gmail_enabled = initialize_gmail()
                if st.session_state.gmail_enabled:
                    reset_agent()  # Force rebuilds the agent graph with the newly active Gmail tools
                    st.success("Gmail connected successfully!")
                    st.rerun()

    current_conv_id = st.session_state.conversation_id if st.session_state.conversation_id else "—"
    st.info(f"Logged in as: **{st.session_state.user_email}** | Role: **{st.session_state.user_role}** | Chat ID: **{current_conv_id}**")
    
    render_history()
    llm = get_llm()
    if prompt := st.chat_input("Ask a question"):
        with st.chat_message("assistant"), st.spinner("Thinking..."):
            chat_round(prompt)
        st.rerun()

if __name__ == "__main__": main()