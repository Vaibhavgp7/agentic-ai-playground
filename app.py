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
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("user_role", None)
    st.session_state.setdefault("conversation_id", None)
    st.session_state.setdefault("vector_store_ready", False)

def render_history():
    """Render the chat history."""
    for msg in st.session_state.messages:
        if msg.type == "human":
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif msg.type == "ai":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

def chat_round(user_input):
    """Handle a single round of chat."""
    st.session_state.messages.append(HumanMessage(content=user_input))

    agent_messages = []
    for msg in st.session_state.messages:
        role = "user" if msg.type == "human" else "assistant"
        agent_messages.append({"role": role, "content": msg.content})

    #response = build_chain(llm).invoke({"input": user_input, "history": st.session_state.messages})
    result = get_agent().invoke({"messages": agent_messages})
    last_msg = result["messages"][-1]
    if last_msg:
        response = AIMessage(content=last_msg.content)
    else:
        response = AIMessage(content="I'm sorry, I couldn't generate a response. Please try again.")

    st.session_state.messages.append(AIMessage(content=response.content))
    st.session_state.conversations[st.session_state.conversation_id] = st.session_state.messages

def start_new_conversation():
    conversation_id = str(uuid4())
    initial_msgs = [AIMessage(content="Hi! Ask me anything.")]
    st.session_state.conversation_id = conversation_id
    st.session_state.messages = initial_msgs
    st.session_state.conversations[conversation_id] = initial_msgs

def load_conversation(conv_id: str):
    """Load a specific conversation thread into the active session state."""
    if conv_id in st.session_state.conversations:
        st.session_state.conversation_id = conv_id
        # Copy that thread's messages into the active messages list
        st.session_state.messages = st.session_state.conversations[conv_id]


def main():
    st.set_page_config(page_title="LangChain Bot", page_icon="🤖")
    st.title("LangChain Bot")
    st.caption("A simple chatbot using LangChain.")

    load_dotenv()
    init_session()

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

        if not st.session_state.conversations:
            st.selectbox("Thread", options=["(no threads yet)"], disabled=True)
        else:
            conv_ids = list(st.session_state.conversations.keys())
            try:
                current_index = conv_ids.index(st.session_state.conversation_id)
            except ValueError:
                current_index = len(conv_ids) - 1  # Default to the last conversation if current ID is not found

            selected_id = st.selectbox("Thread", options=conv_ids, index=current_index)
            
            if selected_id != st.session_state.conversation_id:
                load_conversation(selected_id)
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