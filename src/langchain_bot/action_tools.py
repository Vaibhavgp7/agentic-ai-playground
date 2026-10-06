from typing import List

from langchain.tools import tool, BaseTool
from langchain.tools import ToolRuntime
from langchain_bot.context import SessionContext
from langchain_bot.sql_tools import get_database
from sqlalchemy import text


@tool
def cancel_order_action(
    order_id: str,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """
    CRITICAL ACTION: Cancels a customer order and processes a refund.
    Requires administrator approval.
    """

    context: SessionContext = runtime.context

    db = get_database()
    engine = db._engine

    with engine.connect() as connection:

        order = connection.execute(
            text("""
                SELECT o.status
                FROM orders o
                JOIN users u
                    ON o.user_id = u.id
                WHERE o.id = :oid
                  AND u.email = :email
            """),
            {
                "oid": order_id,
                "email": context.user_email
            }
        ).fetchone()

        if not order:
            return (
                f"Access Denied: Order ID {order_id} "
                f"does not belong to user {context.user_email}."
            )

        if order[0] != "PLACED":
            return (
                f"Rejection: Only orders with status 'PLACED' "
                f"can be canceled. Current status is '{order[0]}'."
            )

        connection.execute(
            text("""
                UPDATE orders
                SET status = 'CANCELLED'
                WHERE id = :oid
            """),
            {"oid": order_id}
        )

        connection.execute(
            text("""
                UPDATE payments
                SET status = 'REFUNDED'
                WHERE order_id = :oid
            """),
            {"oid": order_id}
        )

        connection.commit()

    return (
        f"Success: Order {order_id} has been fully "
        f"canceled and refunded successfully."
    )


@tool
def create_return_action(
    order_id: str,
    product_name: str,
    reason: str,
    runtime: ToolRuntime[SessionContext]
) -> str:
    """
    CRITICAL ACTION: Creates a product return and refund.
    Requires administrator approval.
    """

    context: SessionContext = runtime.context

    db = get_database()
    engine = db._engine

    with engine.connect() as connection:

        # 1. Verify order belongs to authenticated user
        order = connection.execute(
            text("""
                SELECT o.id, o.user_id, o.status
                FROM orders o
                JOIN users u
                    ON o.user_id = u.id
                WHERE o.id = :oid
                  AND u.email = :email
            """),
            {
                "oid": order_id,
                "email": context.user_email
            }
        ).fetchone()

        if not order:
            return (
                f"Access Denied: Order ID {order_id} "
                f"does not belong to user {context.user_email}."
            )

        if order[2] in ["PLACED", "CANCELLED"]:
            return (
                f"Rejection: Order status is '{order[2]}'. "
                f"Please cancel the order instead of processing "
                f"a return request."
            )

        # 2. Find the exact order item using the product name
        order_item = connection.execute(
            text("""
                SELECT oi.id
                FROM order_items oi
                JOIN products p
                    ON oi.product_id = p.id
                WHERE oi.order_id = :oid
                  AND p.name = :product_name
                LIMIT 1
            """),
            {
                "oid": order_id,
                "product_name": product_name
            }
        ).fetchone()

        if not order_item:
            return (
                f"Product '{product_name}' was not found "
                f"in order {order_id}."
            )

        order_item_id = order_item[0]

        # 3. Create return using the ACTUAL returns schema
        connection.execute(
            text("""
                INSERT INTO returns (
                    order_id,
                    order_item_id,
                    user_id,
                    reason,
                    status,
                    requested_at,
                    resolved_at,
                    admin_id
                )
                VALUES (
                    :oid,
                    :order_item_id,
                    :user_id,
                    :reason,
                    'APPROVED',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    NULL
                )
            """),
            {
                "oid": order_id,
                "order_item_id": order_item_id,
                "user_id": order[1],
                "reason": reason
            }
        )

        # 4. Refund payment
        connection.execute(
            text("""
                UPDATE payments
                SET status = 'REFUNDED'
                WHERE order_id = :oid
            """),
            {"oid": order_id}
        )

        connection.commit()

    return (
        f"Success: Return request for product "
        f"'{product_name}' on Order {order_id} "
        f"has been processed successfully."
    )


def get_action_tools() -> List[BaseTool]:
    """Returns the destructive tools requiring HITL approval."""

    return [
        cancel_order_action,
        create_return_action
    ]