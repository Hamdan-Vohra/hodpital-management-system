import streamlit as st
from datetime import datetime
from database.connection import get_db_connection
from utils.gdpr import get_gdpr_compliance_report

def display_dashboard():
    st.title("Hospital Management Dashboard")
    
    # Check GDPR compliance
    if not get_gdpr_compliance_report():
        st.warning("This application is not compliant with GDPR requirements.")
        return

    # Database connection
    conn = get_db_connection()
    
    # Fetch system status
    system_status = conn.execute("SELECT status FROM system_status").fetchone()
    st.subheader("System Status")
    st.write(f"Current Status: {system_status[0]}")

    # Fetch user activity
    user_activity = conn.execute("SELECT user_id, activity, timestamp FROM user_activity ORDER BY timestamp DESC LIMIT 10").fetchall()
    st.subheader("Recent User Activity")
    for activity in user_activity:
        st.write(f"User ID: {activity[0]}, Activity: {activity[1]}, Time: {datetime.fromtimestamp(activity[2])}")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    display_dashboard()