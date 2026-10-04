import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_bot.rag_tool import search_policies
from pathlib import Path

_agent = None

# 9.2 — create_support_agent()
def create_support_agent():
    """Configure and build the main e-commerce support agent."""
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")

    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
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
        system_prompt=system_prompt
    )

def get_agent():
    """Retrieve the cached agent instance or build one if it does not exist."""
    global _agent
    if _agent is None:
        _agent = create_support_agent()
    return _agent