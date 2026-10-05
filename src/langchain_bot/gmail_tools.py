# src/langchain_bot/gmail_tools.py
import os
import pickle
from datetime import datetime
from typing import List, Any
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import tool, BaseTool
from langchain_google_community.gmail.send_message import GmailSendMessage
from pathlib import Path

# Import the database initializer to grab the connection engine
from langchain_bot.sql_tools import get_database

# Fixed scope to target Gmail send privileges specifically
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Global thread-safe runtime cache for the active API resource
_GMAIL_SERVICE = None

def get_gmail_service() -> Any:
    """Scope gmail.send only; load token.pickle if exists; refresh or run local OAuth server; save token; return Gmail API resource via googleapiclient build."""
    global _GMAIL_SERVICE
    if _GMAIL_SERVICE is not None:
        return _GMAIL_SERVICE

    creds = None
    root = Path(__file__).resolve().parents[2]
    token_path = root / 'token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_json = root / 'credentials.json'
            if not os.path.exists(credentials_json):
                raise FileNotFoundError("Missing credentials.json in project root.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_json), SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    _GMAIL_SERVICE = build('gmail', 'v1', credentials=creds)
    return _GMAIL_SERVICE

def initialize_gmail() -> bool:
    """Try init once, cache service, return False on missing credentials (app still runs)."""
    try:
        service = get_gmail_service()
        return service is not None
    except Exception as e:
        print(f"[GMAIL INIT] Skipped or credentials missing: {e}")
        return False

def is_gmail_available() -> bool:
    """Helper method for UI (Sidebar state checks)."""
    return _GMAIL_SERVICE is not None

def get_gmail_tools() -> List[BaseTool]:
    """Returns the single unified send_gmail_notification tool wrapper or an empty list if unavailable."""
    if not is_gmail_available():
        return []
    return [send_gmail_notification]

@tool
def send_gmail_notification(user_email: str, email_type: str, subject: str, body: str) -> str:
    """
    Unified tool to send customer notifications for cancellations, return tickets, or status updates.
    Arguments:
      - user_email: Customer's destination email address.
      - email_type: Category string (e.g., 'cancellation_confirmed', 'return_ticket_created', 'return_status_updated').
      - subject: Email subject line.
      - body: Main message content body text.
    """
    if not is_gmail_available():
        return "Error: Gmail notification service is not configured or offline."

    try:
        # 1. Fetch our authenticated cached resource service
        service = get_gmail_service()
        
        # 2. Instantiate the standalone LangChain community GmailSendMessage tool
        native_send_tool = GmailSendMessage(api_resource=service)
        
        # 3. Invoke the toolkit's native tool payload structure
        native_send_tool.invoke({
            "to": [user_email],
            "subject": subject,
            "message": body
        })

        # 4. Fetch the database wrapper and grab its core SQLAlchemy engine
        db = get_database()
        engine = db._engine
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with engine.connect() as connection:
            connection.execute(
                "INSERT INTO email_logs (user_email, email_type, subject, timestamp) VALUES (:u, :t, :s, :ts)",
                {"u": user_email, "t": email_type, "s": subject, "ts": timestamp}
            )

        return f"Successfully sent '{email_type}' notification email to {user_email} and logged to DB."

    except Exception as e:
        # Print directly to the terminal console instead of using logging framework
        print(f"[GMAIL TOOL ERROR] Failed sending to {user_email}: {str(e)}")
        return f"Failed to send email notification to {user_email}. Technical reason: {str(e)}"