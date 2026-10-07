# LangChain E-Commerce Support Agent

An AI-powered e-commerce customer support application built with **LangChain 1.x, LangGraph, Streamlit, SQLite, ChromaDB, and Gmail**.

The project has two Streamlit interfaces:

- Customer chat application
- Admin dashboard for Human-in-the-Loop (HITL) approvals

The main design is **agent-centric**: the Streamlit applications are thin UI layers while the LangChain agent handles SQL, RAG, Gmail, and business actions.

---

## Features

- Customer login using email and password
- Admin login
- Multiple customer conversations using UUIDs
- Persistent conversation state with a LangGraph SQLite checkpointer
- SQL-based questions about orders, payments, returns, etc.
- RAG-based e-commerce policy and FAQ questions
- Order cancellation
- Product return requests
- Human approval before destructive actions
- Admin approval/rejection of pending actions
- Gmail confirmation notifications
- Email logging in SQLite
- LangChain middleware logging
- Automatic customer UI refresh after HITL approval

---

## Project Structure

```text
project/
│
├── app.py
├── app_admin.py
├── ecommerce_setup.sql
├── ecommerce.db
├── .env
├── credentials.json
├── token.pickle
│
├── returns_policy.txt
├── shipping_policy.txt
├── faq_returns_and_cancellations.txt
|
└── src/
    └── langchain_bot/
        ├── __init__.py
        ├── agent.py
        ├── action_tools.py
        ├── auth.py
        ├── context.py
        ├── db_init.py
        ├── gmail_tools.py
        ├── hitl_utils.py
        ├── logging_middleware.py
        ├── rag_tools.py
        └── sql_tools.py
```
---
## Implementation Notes

- Dynamic Prompt + SessionContext with SQL Database Toolkit

SessionContext provides the authenticated customer's information, such as their email and role, to the agent at runtime and the tools using ToolRuntime

However, the prebuilt SQL Database Toolkit does not automatically understand or enforce that context.
Therefore, a dynamic prompt is used to inject the current SessionContext into the agent's system instructions on every request.


- @st.fragment for HITL Result Updates

The customer and admin applications run as separate Streamlit processes.

When an admin approves a return/cancellation, the LangGraph checkpoint is updated, but the customer's browser does not automatically rerun.

The existing render_history() function reads the latest checkpoint every 2 seconds, to update the assitant response.

---
# Env format
```text
OPENAI_API_KEY=your-key"
MODEL_NAME=gpt-5.4-mini
MODEL_PROVIDER=openai
CHECKPOINTS_DB_PATH=checkpoints.sqlite
```