from email import message

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
import os

def get_llm() -> ChatOpenAI:
    """Get the language model."""
    llm = ChatOpenAI(
        model_name=os.environ["MODEL_NAME"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.3
    )
    return llm

def init_session():
    """Initialize the session state."""
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
    response = llm.invoke(st.session_state.messages)
    st.session_state.messages.append(AIMessage(content=response.content))

def main():
    st.set_page_config(page_title="LangChain Bot", page_icon="🤖")
    load_dotenv()
    init_session()
    render_history()
    llm = get_llm()
    if prompt := st.chat_input("Ask a question"):
        with st.chat_message("assistant"), st.spinner("Thinking..."):
            chat_round(llm, prompt)
        st.rerun()

if __name__ == "__main__": main()