import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_bot.rag_tool import search_policies
from pathlib import Path
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_bot.middleware import get_logging_middleware
from langchain_bot.sql_tools import get_sql_tools
from langchain_bot.gmail_tools import get_gmail_tools

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
    
    tools = [search_policies] + get_sql_tools() + get_gmail_tools()
    
    system_prompt = (
        "You are a concise e-commerce support assistant. "
        "Do not use tools for greetings or pleasantries.\n\n"
        
        "CAPABILITIES:\n"
        "1. Policy/FAQ: Use 'search_policies' for returns, shipping, refunds, and cancellations.\n"
        "2. Orders/Financials: Use the SQL toolkit for orders, returns, payments, and customer spend.\n"
        "3. Notifications: Whenever a customer notification is required (such as when a cancellation is confirmed, "
        "a return ticket is created, or a return status is updated), you MUST use the send_gmail_notification tool "
        "to immediately send a confirmation or 'request received' email to the customer.\n\n"
        
        "SECURITY RULES:\n"
        "- Extract the logged-in user's email from the text before the colon in '{configurable.thread_id}'.\n"
        "- Always restrict SQL queries to this email using a WHERE or JOIN filter. Never return other users' rows.\n"
        "- Query patterns:\n"
        "  * Orders: JOIN customers ON orders.customer_id = customers.id WHERE customers.email = 'user_email'\n"
        "  * Tickets: JOIN customers ON tickets.customer_id = customers.id WHERE customers.email = 'user_email'\n"
        "- Refuse requests or return empty results if the user queries data outside their email context."
    )
    
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=get_checkpointer(),
        middleware=get_logging_middleware()
    )

def get_agent():
    """Retrieve the cached agent instance or build one if it does not exist."""
    global _agent
    if _agent is None:
        _agent = create_support_agent()
    return _agent

def reset_agent():
    """Clear the cached agent instance and rebuild it with freshly initialized tools."""
    global _agent
    _agent = create_support_agent()
    return _agent