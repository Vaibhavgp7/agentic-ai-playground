import streamlit as st
from dotenv import load_dotenv
import os
from langchain_bot.auth import authenticate_user
from src.langchain_bot.hitl_utils import list_pending_actions, resume_with_decision
from src.langchain_bot.gmail_tools import initialize_gmail, is_gmail_available
from src.langchain_bot.agent import reset_agent
def main():
    st.set_page_config(page_title="Admin Control Center", page_icon="🛡️", layout="wide")
    st.title("🛡️ Admin HITL Operations Panel")
    load_dotenv()
    
    if "admin_email" not in st.session_state:
        st.subheader("Administrator Authorization Gateway")
        with st.form("admin_login"):
            email = st.text_input("Admin Email ID")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Authenticate Access")
            
            if submit:
                # Force user authentication to check for 'admin' privileges
                if authenticate_user(email, password, "admin"):
                    st.session_state.admin_email = email
                    st.success("Authentication completed successfully!")
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid administrator credentials profile.")
        return

    # Authorized Layout View Section
    st.sidebar.info(f"Authorized Operator: {st.session_state.admin_email}")
    if st.sidebar.button("Term Session Logout"):
        del st.session_state.admin_email
        st.rerun()
        
    st.header("Pending Requests Awaiting Verification")
    filter_status = st.selectbox("Filter Status Bucket", ["PENDING", "APPROVED", "REJECTED"], index=0)
    
    pending_items = list_pending_actions(status=filter_status)
    
    if not pending_items:
        st.info(f"Clean ledger: No records found with status '{filter_status}'.")
        return
        
    for idx, item in enumerate(pending_items):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 3, 2])
            
            with col1:
                st.markdown(f"**Customer:** {item['user_email']}")
                st.markdown(f"**Action Target:** `{item['action_type']}`")
                st.markdown(f"**Created On:** {item['created_at']}")
                
            with col2:
                st.markdown(f"**Target Order ID:** {item['order_id']}")
                if item['product_name']:
                    st.markdown(f"**Product Item:** {item['product_name']}")
                st.markdown(f"**Stated Reason:** *{item['reason']}*")
                
            with col3:
                if filter_status == "PENDING":
                    rej_reason = st.text_input("Rejection notes (Optional)", key=f"rej_{idx}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Approve", key=f"app_btn_{idx}"):
                        msg = resume_with_decision(item['thread_id'], item['user_email'], "approve")
                        st.success(msg)
                        st.rerun()
                        
                    if c2.button("❌ Reject", key=f"rej_btn_{idx}"):
                        msg = resume_with_decision(item['thread_id'], item['user_email'], "reject", reason=rej_reason)
                        st.warning(msg)
                        st.rerun()
                else:
                    st.metric("Status State Label", filter_status)

if __name__ == "__main__":
    main()