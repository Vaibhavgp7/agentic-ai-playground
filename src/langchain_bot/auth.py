from typing_extensions import TypedDict, Optional
import sqlite3
from pathlib import Path


class UserRecord(TypedDict):
    email: str
    full_name: str
    role: str

def authenticate_user(email: str, password: str, role: Optional[str] = None) -> Optional[UserRecord]:

    db_path = Path(__file__).resolve().parents[2] / "ecommerce.db"

    query = "SELECT email, full_name, role FROM users WHERE email = ? AND password = ?"
    params = [email, password]

    # Append optional role filter dynamically
    if role:
        query += " AND role = ?"
        params.append(role)

    # Execute query and parse output
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row  # Enables column fetching by name
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()

    return dict(row) if row else None