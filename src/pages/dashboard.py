import streamlit as st
from datetime import datetime
from streamlit import session_state as st_session

from database.connection import get_db_connection, get_patients
from database.connection import log_action
from utils.gdpr import get_gdpr_compliance_report
from components.charts import plot_patient_statistics


def display_dashboard():
    st.title(" Hospital Management Dashboard")

    if not get_gdpr_compliance_report():
        st.error(" This application is NOT GDPR compliant. Access denied.")
        return


    user = st_session.get("user")
    role = st_session.get("role")
    user_id = st_session.get("user_id")

    if not user:
        st.warning("You must be logged in to access the dashboard.")
        return

    st.sidebar.markdown(f"**User:** {user}\n\n**Role:** {role}")


    conn = get_db_connection()
    st.subheader(" System Availability")
    st.write("Database Connection: **Active**")

    now = datetime.utcnow()
    if "started_at" not in st_session:
        st_session.started_at = now

    uptime_seconds = int((now - st_session.started_at).total_seconds())
    uptime_minutes = uptime_seconds // 60

    st.write(f"Uptime: **{uptime_minutes} minutes**")
    st.write(f"Last Sync: **{now.isoformat()} UTC**")


    st.markdown("---")
    st.subheader(" Patient Summary")

    patients = get_patients()
    total_patients = len(patients)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Patients", total_patients)
    col2.metric("Anonymized Records", sum(1 for p in patients if p.get("anonymized_name")))
    col3.metric("Raw Records", sum(1 for p in patients if not p.get("anonymized_name")))

    # Chart data example
    stats_data = [
        {"category": "Total", "count": total_patients},
        {"category": "Anonymized", "count": col2.metric},
    ]
    plot_patient_statistics(stats_data)


    st.markdown("---")
    st.subheader(" Recent Patient Records")

    if not patients:
        st.info("No patient records available.")
    else:
        for p in patients[:10]: 
            pid = p["patient_id"]

            if role == "admin":
                st.write(
                    f"- **ID {pid}** | Name: {p['name']} | Contact: {p['contact']} | Diagnosis: {p['diagnosis']} "
                    f"| Anon: {p.get('anonymized_name')}"
                )
            elif role == "doctor":
                st.write(
                    f"- **ID {pid}** | Name: {p.get('anonymized_name')} | Contact: {p.get('anonymized_contact')} "
                    f"| Diagnosis: {p['diagnosis']}"
                )
            elif role == "receptionist":
                st.write(
                    f"- **ID {pid}** | Name: {p.get('anonymized_name') or '(masked)'} "
                    f"| Contact: {p.get('anonymized_contact') or '(masked)'}"
                )
            else:
                st.write(f"- **ID {pid}** | Restricted view")

            log_action(
                user_id=user_id,
                role=role,
                action="view_patient_preview",
                details=f"pid={pid}"
            )


    if role == "admin":
        st.markdown("---")
        st.subheader(" Integrity Audit Logs")

        cur = conn.cursor()
        cur.execute("SELECT * FROM logs ORDER BY log_id DESC LIMIT 50")
        logs = cur.fetchall()

        if not logs:
            st.info("No logs available.")
        else:
            for log in logs:
                st.write(
                    f"- [{log['timestamp']}] **user_id={log['user_id']}**, role={log['role']} → "
                    f"{log['action']} | {log['details']}"
                )

    conn.close()


if __name__ == "__main__":
    display_dashboard()
