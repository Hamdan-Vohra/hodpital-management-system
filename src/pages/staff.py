import streamlit as st
from streamlit import session_state as st_session
from database.connection import get_db_connection

def display_staff_records():
    conn = get_db_connection()
    cur = conn.cursor()
    # treat users table as staff registry for this demo
    cur.execute("SELECT user_id, username, role FROM users ORDER BY role, username")
    rows = cur.fetchall()
    conn.close()

    st.title("Staff Records")

    if not rows:
        st.info("No staff records found.")
        return

    for r in rows:
        st.subheader(f"Name: {r['username']}")
        st.write(f"Role: {r['role']}")
        st.write(f"User ID: {r['user_id']}")
        st.markdown("---")

def main():
    if not st.session_state.get("user"):
        st.warning("You need to be logged in to view staff details.")

        if st.button("Back to Login"):
            st.switch_page("Main.py")

        return

    display_staff_records()

if __name__ == "__main__":
    main()