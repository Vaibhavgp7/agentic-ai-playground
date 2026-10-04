import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_bot.rag_tool import search_policies
from pathlib import Path
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

_agent = None
_checkpointer = None

project_root = Path(__file__).resolve().parent.parent.parent

def get_checkpointer() -> SqliteSaver:
    """Initialize or retrieve the cached SQLite persistent checkpointer database instance."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
        
    CHECKPOINT_PATH = project_root / os.environ.get("CHECKPOINTS_DB_PATH", "checkpoints.sqlite")
    conn = sqlite3.connect(CHECKPOINT_PATH, check_same_thread=False)
    _checkpointer = SqliteSaver(conn)
    _checkpointer.setup()
    return _checkpointer

def get_thread_config(user_email: str, conversation_id: str) -> dict:
    """Generate the config map needed for executing the agent graph with isolated thread state."""
    return {
        "configurable": {
            "thread_id": f"{user_email}:{conversation_id}"
        },
        "recursion_limit": 20
    }

def create_support_agent():
    """Configure and build the main e-commerce support agent."""
    load_dotenv(dotenv_path=project_root / ".env")
    llm = ChatOpenAI(
        model_name=os.environ["MODEL_NAME"],
        temperature=0.2,
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )
    
    tools = [search_policies]
    
    system_prompt = (
        "You are a concise, helpful e-commerce customer support assistant. "
        "Your primary job is to answer customer questions accurately. "
        "Use the 'search_policies' tool whenever a customer asks about corporate policies, "
        "returns, shipping rules, refunds, or cancellation rules. "
        "Always formulate your response based directly on the facts returned by the tool. "
        "Do not invoke any tools for simple greetings, chit-chat, or pleasantries."
    )
    
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=get_checkpointer()
    )

def get_agent():
    """Retrieve the cached agent instance or build one if it does not exist."""
    global _agent
    if _agent is None:
        _agent = create_support_agent()
    return _agent