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

from langchain_bot.context import SessionContext
from langchain_bot.action_tools import get_action_tools
from langchain.agents.middleware import HumanInTheLoopMiddleware, dynamic_prompt

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
    
    standard_tools = [search_policies] + get_sql_tools() + get_gmail_tools()
    action_tools = get_action_tools()
    all_tools = standard_tools + action_tools
    print("[AGENT TOOLS]", [tool.name for tool in all_tools])
    
    interrupt_config = {tool_item.name: True for tool_item in action_tools}
    for tool_item in standard_tools:
        interrupt_config[tool_item.name] = False
    
  
        
    all_tools = standard_tools + action_tools

    agent_middleware = get_logging_middleware() + [
        HumanInTheLoopMiddleware(interrupt_on=interrupt_config)
    ]
    
    
    
    return create_agent(
        model=llm,
        tools=all_tools,
        # system_prompt=system_prompt,
        checkpointer=get_checkpointer(),
        middleware=[dynamic_system_prompt] + agent_middleware,
        context_schema=SessionContext
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

@dynamic_prompt
def dynamic_system_prompt(request):
    context = request.runtime.context

    return f"""
    You are a concise e-commerce support assistant.

    AUTHENTICATED CUSTOMER:
    - Email: {context.user_email}
    - Role: {context.role}

    RULES:
    - Use context.user_email for all customer-specific operations.
    - Never use an order ID, product name, or conversation ID as an email.
    - Use SQL only for database/customer/order verification.
    - Inspect the database schema before writing SQL.
    - Never expose another customer's data.

    TOOL PURPOSES:
    - search_policies: ONLY for general policy/FAQ questions.
    - SQL tools: ONLY for database queries and verification.
    - send_gmail_notification: ONLY for sending customer emails.
    - cancel_order_action/create_return_action: perform the approved business action.

    RETURN/CANCELLATION FLOW:
    - Verify the customer and request using SQL.
    - Call the appropriate action tool.
    - After HITL approval, when the action tool returns SUCCESS and either request is approved or rejected, in both cases:
        1. Immediately call send_gmail_notification.
        2. Then give the final response.
    - After action success, DO NOT call search_policies.
    - After action success, DO NOT perform unnecessary SQL queries.
    - Never claim an email was sent unless send_gmail_notification actually succeeds.

    RETURN:
    - If multiple products exist and the customer did not specify one, ask which product.
    - Never choose a product yourself.
    - Use the exact product name provided by the customer.

    Be concise and never invent information.
    """