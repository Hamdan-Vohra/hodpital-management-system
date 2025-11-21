import streamlit as st
from database.connection import get_db_connection, log_action
import hashlib
from typing import Optional, Tuple

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_user_by_username(username: str) -> Optional[dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def verify_user(username: str, password: str) -> bool:
    row = get_user_by_username(username)
    if not row:
        return False
    return row["password_hash"] == _hash_password(password)

def get_user_role(username: str) -> Optional[str]:
    row = get_user_by_username(username)
    return row["role"] if row else None

def _user_count() -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM users")
    r = cur.fetchone()
    conn.close()
    return int(r["c"]) if r else 0

def _create_user(username: str, password: str, role: str = "admin") -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, _hash_password(password), role)
        )
        conn.commit()
        user_id = cur.lastrowid
        return user_id
    except Exception:
        return None
    finally:
        conn.close()

def authenticate_user() -> Tuple[Optional[str], Optional[str]]:
    """
    Streamlit login UI. If no users exist, shows a registration form to create the first user.
    Returns (username, password) on successful login/registration else (None, None).
    Also logs login/registration actions.
    """
    st.header("Sign in")

    # If no users exist, offer initial registration (bootstrap)
    if _user_count() == 0:
        st.warning("No users found — create the first account (recommended role: admin).")
        with st.form("register_first_user"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            role = st.selectbox("Role", options=["admin", "doctor", "receptionist"], index=0)
            create = st.form_submit_button("Create account")
            if create:
                if not new_username or not new_password:
                    st.error("Provide username and password.")
                elif new_password != confirm:
                    st.error("Passwords do not match.")
                else:
                    uid = _create_user(new_username, new_password, role)
                    if uid:
                        log_action(uid, role, "create_user", f"bootstrapped user {new_username} role={role}")
                        st.success(f"User {new_username} created. Please login.")
                    else:
                        st.error("Failed to create user (maybe username exists).")
    else:
            # After registration, fall through to login UI
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if not username or not password:
                st.error("Enter both username and password.")
                return None, None
            try:
                if verify_user(username, password):
                    # record login
                    user = get_user_by_username(username)
                    user_id = user["user_id"] if user else None
                    log_action(user_id, user.get("role") if user else "unknown", "login", f"user {username} logged in")
                    st.success(f"Welcome, {username}")
                    return username, password
                else:
                    st.error("Invalid credentials.")
                    return None, None
            except Exception as e:
                st.error(f"Login error: {e}")
                return None, None
    return None, None