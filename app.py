import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from uuid import uuid4
from langchain_bot.auth import authenticate_user

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

    if "messages" not in st.session_state:
        st.session_state.messages = [AIMessage(content="Hi! Ask me anything.")]

def render_history():
    """Render the chat history."""
    for msg in st.session_state.messages:
        if msg.type == "human":
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif msg.type == "ai":
            with st.chat_message("assistant"):
                st.markdown(msg.content)

def chat_round(llm, user_input):
    """Handle a single round of chat."""
    st.session_state.messages.append(HumanMessage(content=user_input))
    response = build_chain(llm).invoke({"input": user_input, "history": st.session_state.messages})
    st.session_state.messages.append(AIMessage(content=response.content))

def main():
    st.set_page_config(page_title="LangChain Bot", page_icon="🤖")
    st.title("LangChain Bot")
    st.caption("A simple chatbot using LangChain.")

    load_dotenv()
    init_session()
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
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or role.")
        return

    with st.sidebar:
        st.header("Conversations")
        if not st.session_state.conversations:
            st.selectbox("Thread", options=["(no threads yet)"], disabled=True)
        else:
            st.selectbox("Thread", options=list(st.session_state.conversations.keys()))

    current_conv_id = st.session_state.conversation_id if st.session_state.conversation_id else "—"
    st.info(f"Logged in as: **{st.session_state.user_email}** | Role: **{st.session_state.user_role}** | Chat ID: **{current_conv_id}**")
    
    render_history()
    llm = get_llm()
    if prompt := st.chat_input("Ask a question"):
        with st.chat_message("assistant"), st.spinner("Thinking..."):
            chat_round(llm, prompt)
        st.rerun()

if __name__ == "__main__": main()