from streamlit import session_state as st_session
import streamlit as st
from utils.auth import authenticate_user, get_user_role, get_user_by_username
from utils.gdpr import check_user_consent
from database.connection import get_db_connection, get_patients, anonymize_all_patients, add_patient, export_patients_csv, log_action

import tempfile
import os
import datetime

def main_app():
    st.set_page_config(page_title="Hospital Management Dashboard", layout="wide")
    st.title("Hospital Management Dashboard")

    # Authentication
    if "user" not in st_session:
        username, password = authenticate_user()
        if username and password:
            st_session.user = username
            st_session.role = get_user_role(username)
            user_row = get_user_by_username(username)
            st_session.user_id = user_row["user_id"] if user_row else None
            
    if "user" not in st_session:
        st.info("Please login to continue.")
        return

    # GDPR consent
    if not check_user_consent(st_session.user):
        st.warning("You need to provide consent to use this application.")
        return

    # Footer: uptime / last sync (simple)
    if "started_at" not in st_session:
        st_session.started_at = datetime.datetime.utcnow()

    st.sidebar.markdown(f"**User:** {st_session.user}  \n**Role:** {st_session.role}")
    st.sidebar.markdown(f"Started: {st_session.started_at.isoformat()} UTC")

    # Route by role
    if st_session.role == "admin":
        show_admin_dashboard()
    elif st_session.role in ("doctor", "receptionist"):
        show_staff_dashboard()
    else:
        st.error("Unauthorized role.")

def show_admin_dashboard():
    st.subheader("Admin Dashboard")
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown("### Patients")
        patients = get_patients()
        if patients:
            for p in patients:
                st.markdown(f"- ID: {p['patient_id']} | Anon: {p.get('anonymized_name') or '(not anonymized)'} | Contact(anon): {p.get('anonymized_contact') or '(not anonymized)'}")
        else:
            st.info("No patients yet.")
    with col2:
        if st.button("Anonymize all patient data"):
            anonymize_all_patients(triggered_by_user_id=st_session.get("user_id"), role=st_session.get("role"))
            st.success("All patients anonymized. Action logged.")
        if st.button("Export CSV"):
            tmp = tempfile.gettempdir()
            path = os.path.join(tmp, "patients_export.csv")
            export_patients_csv(path)
            with open(path, "rb") as f:
                st.download_button("Download patients CSV", f, file_name="patients_export.csv")
        if st.button("View Audit Logs"):
            show_audit_logs()

def show_staff_dashboard():
    st.subheader("Staff Dashboard")
    patients = get_patients()
    role = st_session.get("role")
    if role == "doctor":
        st.markdown("### Patients (anonymized view)")
        for p in patients:
            st.markdown(f"- ID: {p['patient_id']} | Name: {p.get('anonymized_name') or '(not anonymized)'} | Contact: {p.get('anonymized_contact') or '(not anonymized)'} | Diagnosis: {p.get('diagnosis')}")
            log_action(st_session.get("user_id"), role, "view_patient", f"viewed patient_id={p['patient_id']}")
    elif role == "receptionist":
        st.markdown("### Add patient")
        with st.form("add_patient"):
            name = st.text_input("Full name")
            contact = st.text_input("Contact")
            diagnosis = st.text_area("Diagnosis")
            submitted = st.form_submit_button("Add")
            if submitted:
                pid = add_patient(name, contact, diagnosis, added_by_user_id=st_session.get("user_id"), role=role)
                st.success(f"Patient added with id {pid}")
        st.markdown("Receptionists cannot view sensitive (raw) patient identifiers.")
        # show only anonymized fields if present
        for p in patients:
            anon_name = p.get("anonymized_name") or "(masked)"
            anon_contact = p.get("anonymized_contact") or "(masked)"
            st.markdown(f"- ID: {p['patient_id']} | Name: {anon_name} | Contact: {anon_contact}")
            log_action(st_session.get("user_id"), role, "list_patients", f"listed patient_id={p['patient_id']}")
    else:
        st.error("Role not supported in staff dashboard.")

def show_audit_logs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY log_id DESC LIMIT 200")
    rows = cur.fetchall()
    conn.close()
    st.markdown("### Integrity Audit Log (Admin only)")
    for r in rows:
        st.markdown(f"- [{r['timestamp']}] user_id={r['user_id']} role={r['role']} action={r['action']} details={r['details']}")

if __name__ == "__main__":
    main_app()