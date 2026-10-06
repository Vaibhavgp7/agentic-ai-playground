from pydantic import BaseModel, Field

class SessionContext(BaseModel):
    """Execution context injected directly into tools for identity-aware security."""
    user_email: str = Field(description="The email of the currently logged-in user.")
    conversation_id: str = Field(description="The unique session identifier for the conversation thread.")
    role: str = Field(default="customer", description="The access authorization role (customer or admin).")