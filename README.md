Implementation Notes

In the db initialization script add table pending_actions creation

1. Dynamic Prompt + SessionContext with SQL Database Toolkit

SessionContext provides the authenticated customer's information, such as their email and role, to the agent at runtime.

However, the SQL Database Toolkit does not automatically understand or enforce that context. Its SQL tools can query the database, but they do not inherently know:

which customer is authenticated,

which email must be used for customer-specific queries,

which tables/relationships should be used,

or that data must be restricted to the current customer.

Therefore, a dynamic prompt is used to inject the current SessionContext into the agent's system instructions on every request.

For example:

Authenticated customer:
Email: {context.user_email}
Role: {context.role}

Use the authenticated email for customer-specific queries.
Never expose another customer's data.
Inspect the database schema before writing SQL.

So the responsibilities are:

SessionContext → carries the runtime user information.

Dynamic prompt → tells the LLM how to use that information safely when using the SQL toolkit.

SQL Database Toolkit → actually performs the database operations.

SessionContext alone is data; the dynamic prompt tells the model how that data must be applied.

2. @st.fragment for HITL Result Updates

The customer and admin applications run as separate Streamlit processes.

When an admin approves a return/cancellation, the LangGraph checkpoint is updated, but the customer's browser does not automatically rerun.

The existing render_history() function reads the latest checkpoint:

@st.fragment(run_every=2)
def render_history():
    ...

@st.fragment(run_every=2) causes only this part of the customer UI to rerun every two seconds.

Therefore:

Customer requests a return.

HITL interrupts and waits for admin approval.

Admin approves the action.

The same conversation checkpoint is updated.

The customer's fragment detects the updated checkpoint.

The final assistant response appears automatically.

This removes the need for the customer to manually refresh or log in again.