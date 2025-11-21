import streamlit as st
from streamlit import session_state as st_session
from database.connection import get_db_connection, log_action
from utils.gdpr import check_user_consent
import hashlib
import datetime

def _anon_label(name: str) -> str:
    if not name:
        return "(unknown)"
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return f"ANON_{h[:8]}"

def _ensure_appointments_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        date TEXT,
        time TEXT,
        status TEXT,
        created_by INTEGER,
        created_at TEXT
    )
    """)
    conn.commit()

def display_appointments():
    st.title("Appointment Management")

    user = st_session.get("user")
    role = st_session.get("role")
    user_id = st_session.get("user_id")

    # GDPR consent check
    if not check_user_consent(user):
        st.error("GDPR consent required to view appointments.")
        return

    conn = get_db_connection()
    _ensure_appointments_table(conn)
    cur = conn.cursor()

    # Fetch appointments
    cur.execute("SELECT appointment_id, patient_name, date, time, status FROM appointments ORDER BY appointment_id DESC")
    rows = cur.fetchall()

    if rows:
        st.markdown("### Appointments")
        for r in rows:
            aid = r["appointment_id"]
            patient_name = r["patient_name"] or ""
            # RBAC: only admin sees raw patient names; others see anonymized label
            display_name = patient_name if role == "admin" else _anon_label(patient_name)
            st.write(f"- ID: {aid} | Patient: {display_name} | Date: {r['date']} | Time: {r['time']} | Status: {r['status']}")
    else:
        st.info("No appointments found.")

    st.markdown("---")
    st.markdown("### Add Appointment")
    with st.form("add_appointment_form"):
        patient_input = st.text_input("Patient Name or ID")
        date_val = st.date_input("Date", value=datetime.date.today())
        time_val = st.time_input("Time", value=datetime.datetime.now().time().replace(second=0, microsecond=0))
        status = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])
        submitted = st.form_submit_button("Submit")
        if submitted:
            if not patient_input or not str(patient_input).strip():
                st.error("Please enter a patient name or patient ID.")
            else:
                try:
                    # Determine if input is an ID or a name
                    patient_input_str = str(patient_input).strip()
                    found = None
                    # try ID lookup
                    try:
                        pid_lookup = int(patient_input_str)
                        cur.execute("SELECT patient_id, name FROM patients WHERE patient_id = ?", (pid_lookup,))
                        row = cur.fetchone()
                        if row:
                            found = dict(row)
                    except ValueError:
                        # not an integer, treat as name
                        pass

                    # if not found by id, try case-insensitive name match
                    if not found:
                        cur.execute("SELECT patient_id, name FROM patients WHERE lower(name) = lower(?)", (patient_input_str,))
                        matches = cur.fetchall()
                        if not matches:
                            # try partial match
                            cur.execute("SELECT patient_id, name FROM patients WHERE lower(name) LIKE lower(?)", (f"%{patient_input_str}%",))
                            matches = cur.fetchall()
                        if not matches:
                            st.error("Patient not found. Please create the patient record first (Patients page) or try a different name/ID.")
                            conn.close()
                        else:
                            if len(matches) > 1:
                                # multiple matches: pick first but notify user
                                found = dict(matches[0])
                                st.warning(f"Multiple patients matched the name. Using ID {found['patient_id']} / Name '{found['name']}'.")
                            else:
                                found = dict(matches[0])

                    if found:
                        # use canonical patient name from DB
                        canonical_name = found.get("name") or patient_input_str
                        created_at = datetime.datetime.utcnow().isoformat()
                        cur.execute(
                            "INSERT INTO appointments (patient_name, date, time, status, created_by, created_at) VALUES (?,?,?,?,?,?)",
                            (canonical_name, date_val.isoformat(), time_val.isoformat(), status, user_id, created_at)
                        )
                        conn.commit()
                        appointment_id = cur.lastrowid
                        log_action(user_id, role, "create_appointment", f"appointment_id={appointment_id} patient_id={found.get('patient_id')}")
                        st.success(f"Appointment created (id={appointment_id}) for patient '{canonical_name}'.")
                except Exception as e:
                    st.error(f"Failed to create appointment: {e}")

    conn.close()

def main():
    if not st.session_state.get("user"):
        st.warning("You need to be logged in to view appointments.")

        if st.button("Back to Login"):
            st.switch_page("Main.py")

        return

    display_appointments()

if __name__ == "__main__":
    main()