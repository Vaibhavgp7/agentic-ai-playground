import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

# Load environment variables

def get_database() -> SQLDatabase:
    """Initialize the SQLDatabase instance pointing to the project root ecommerce.db."""
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")   
    db_path = project_root / "ecommerce.db"
    
    # Generate the standard SQLite connection URI string
    db_uri = f"sqlite:///{db_path}"
    return SQLDatabase.from_uri(db_uri)

def get_sql_tools() -> list:
    """Initialize the SQLDatabaseToolkit and return its operational query tools."""
    db = get_database()
    
    llm = ChatOpenAI(
        model_name=os.environ["MODEL_NAME"],
        temperature=0,
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )
    
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()