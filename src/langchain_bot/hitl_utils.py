from langchain_bot.sql_tools import get_database
from langchain_bot.agent import get_agent, get_thread_config
from langchain_bot.context import SessionContext
from sqlalchemy import text
from langgraph.types import Command


def handle_interrupt(result, thread_id: str, user_email: str) -> str:
    """Detect an interrupted action and save it as a pending admin request."""

    interrupts = result.get("__interrupt__")

    if not interrupts:
        return ""

    interrupt_value = interrupts[0].value
    action_requests = interrupt_value.get("action_requests", [])

    if not action_requests:
        return ""

    next_action = action_requests[0]
    tool_name = next_action.get("name", "unknown_action")
    tool_args = next_action.get("args", {})

    # Convert tool names to the values allowed by pending_actions.action_type
    if tool_name == "create_return_action":
        action_type = "CREATE_RETURN"
    elif tool_name == "cancel_order_action":
        action_type = "CANCEL_ORDER"
    else:
        return f"Unknown action type: {tool_name}"

    db = get_database()
    engine = db._engine

    with engine.connect() as connection:

        exists = connection.execute(
            text("""
                SELECT id
                FROM pending_actions
                WHERE thread_id = :tid
                  AND status = 'PENDING'
            """),
            {"tid": thread_id}
        ).fetchone()

        if not exists:
            connection.execute(
                text("""
                    INSERT INTO pending_actions
                    (
                        thread_id,
                        user_email,
                        action_type,
                        order_id,
                        product_name,
                        reason,
                        status
                    )
                    VALUES (
                        :tid,
                        :email,
                        :act,
                        :oid,
                        :prod,
                        :reas,
                        'PENDING'
                    )
                """),
                {
                    "tid": thread_id,
                    "email": user_email,
                    "act": action_type,
                    "oid": tool_args.get("order_id"),
                    "prod": tool_args.get("product_name"),
                    "reas": tool_args.get(
                        "reason",
                        "No reason provided"
                    )
                }
            )

            connection.commit()

    return (
        "⏳ **Request Received**: Your request requires manual "
        "administrator authorization review. An admin has been notified."
    )


def resume_with_decision(
    thread_id: str,
    user_email: str,
    decision: str,
    reason: str = ""
) -> str:
    """Resume the interrupted agent after an administrator decision."""

    db = get_database()
    engine = db._engine

    # Check that this thread has a pending action
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT action_type
                FROM pending_actions
                WHERE thread_id = :tid
                  AND status = 'PENDING'
            """),
            {"tid": thread_id}
        ).fetchone()

        if not row:
            return "No active pending request found for this thread session."

        action_name = row[0]

    # Get conversation ID from:
    # user_email:conversation_id
    conv_id = (
        thread_id.split(":", 1)[1]
        if ":" in thread_id
        else thread_id
    )

    # Re-create the SAME SessionContext used by the customer app
    ctx = SessionContext(
        user_email=user_email,
        conversation_id=conv_id,
        role="customer"
    )

    config = get_thread_config(
        user_email,
        conv_id
    )

    agent = get_agent()

    # Resume the interrupted graph WITH SessionContext
    if decision.lower() == "approve":

        result = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "type": "approve"
                        }
                    ]
                }
            ),
            config=config,
            context=ctx
        )

        status_update = "APPROVED"

        messages = result.get("messages", [])

        if messages:
            last_message = messages[-1]
            output_msg = getattr(
                last_message,
                "content",
                "Action approved and executed successfully."
            )
        else:
            output_msg = (
                f"Successfully approved and executed "
                f"action '{action_name}'."
            )

    else:

        result = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "type": "reject",
                            "message": reason or "Rejected by administrator."
                        }
                    ]
                }
            ),
            config=config,
            context=ctx
        )

        status_update = "REJECTED"

        output_msg = (
            f"Request rejected. "
            f"Notice sent to user: {reason or 'No reason provided.'}"
        )

    # Update pending action status
    with engine.connect() as connection:

        connection.execute(
            text("""
                UPDATE pending_actions
                SET
                    status = :stat,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = :tid
                  AND status = 'PENDING'
            """),
            {
                "stat": status_update,
                "tid": thread_id
            }
        )

        connection.commit()

    return output_msg


def list_pending_actions(status="PENDING") -> list:
    """Retrieve pending actions from the database."""

    db = get_database()
    engine = db._engine

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    thread_id,
                    user_email,
                    action_type,
                    order_id,
                    product_name,
                    reason,
                    created_at
                FROM pending_actions
                WHERE status = :s
            """),
            {"s": status}
        )

        return [dict(row) for row in result.mappings()]