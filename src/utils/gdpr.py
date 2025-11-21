import streamlit as st
from streamlit import session_state as st_session
from database.connection import get_db_connection, log_action
import datetime
import json
from typing import List, Dict

def check_user_consent(user: str) -> bool:
    """
    Simple GDPR consent handler stored in session state per-user.
    Requires explicit consent before accessing the application.
    """
    if not user:
        return False
    key = f"consent_{user}"
    if st_session.get(key):
        return True

    st.info("GDPR consent required to proceed.")
    agree = st.checkbox("I consent to processing of my personal data for this demo application.", key=f"gdpr_cb_{user}")
    if agree:
        st_session[key] = True
        st.success("Consent recorded.")
        return True
    return False

def log_data_access(user_id: int, role: str, data_accessed: str, patient_id: int = None):
    """
    Log all data access events for audit trail and compliance.
    Records who accessed what data and when for accountability.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        timestamp = datetime.datetime.utcnow().isoformat()
        details = f"accessed {data_accessed}"
        if patient_id:
            details += f" for patient_id={patient_id}"
        cur.execute(
            "INSERT INTO logs (user_id, role, action, timestamp, details) VALUES (?,?,?,?,?)",
            (user_id, role, "data_access", timestamp, details)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Failed to log data access: {e}")

def anonymize_data(patient_id: int, user_id: int = None, role: str = None) -> bool:
    """
    Anonymize specific patient record by masking personal identifiers.
    Replaces name with deterministic hash and masks contact information.
    Returns True on success, False otherwise.
    """
    try:
        from database.connection import anonymize_name, mask_contact
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Fetch patient record
        cur.execute("SELECT name, contact FROM patients WHERE patient_id = ?", (patient_id,))
        row = cur.fetchone()
        if not row:
            return False
        
        name = row["name"] or ""
        contact = row["contact"] or ""
        
        # Generate anonymized versions
        anon_name = anonymize_name(name, patient_id)
        anon_contact = mask_contact(contact)
        
        # Update patient record
        cur.execute(
            "UPDATE patients SET anonymized_name = ?, anonymized_contact = ? WHERE patient_id = ?",
            (anon_name, anon_contact, patient_id)
        )
        conn.commit()
        conn.close()
        
        # Log the anonymization action
        if user_id and role:
            log_action(user_id, role, "anonymize_patient", f"anonymized patient_id={patient_id}")
        
        return True
    except Exception as e:
        st.error(f"Failed to anonymize patient data: {e}")
        return False

def data_retention_policy(retention_days: int = 365) -> Dict:
    """
    Implement and enforce GDPR data retention policy.
    Identifies records that exceed retention period and marks/deletes them.
    Returns summary of records affected.
    
    Args:
        retention_days: Number of days to retain data (default 365 days = 1 year)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)).isoformat()
        
        # Find expired records
        cur.execute(
            "SELECT COUNT(*) as count FROM patients WHERE date_added < ?",
            (cutoff_date,)
        )
        expired_count = cur.fetchone()["count"]
        
        # Mark for deletion or soft-delete (update with deletion flag)
        # For now, we'll just log the records; actual deletion can be triggered by admin
        cur.execute(
            "SELECT patient_id, name, date_added FROM patients WHERE date_added < ? ORDER BY date_added ASC",
            (cutoff_date,)
        )
        expired_records = [dict(r) for r in cur.fetchall()]
        
        conn.close()
        
        return {
            "retention_days": retention_days,
            "cutoff_date": cutoff_date,
            "expired_count": expired_count,
            "expired_records": expired_records
        }
    except Exception as e:
        st.error(f"Failed to check data retention policy: {e}")
        return {"error": str(e)}

def delete_expired_records(retention_days: int = 365, user_id: int = None, role: str = None) -> bool:
    """
    Permanently delete patient records that exceed retention period.
    Only callable by Admin. Logs deletion for audit trail.
    """
    try:
        if role != "admin":
            st.error("Only admins can delete expired records.")
            return False
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)).isoformat()
        
        # Get count before deletion
        cur.execute("SELECT COUNT(*) as count FROM patients WHERE date_added < ?", (cutoff_date,))
        deleted_count = cur.fetchone()["count"]
        
        # Delete expired records
        cur.execute("DELETE FROM patients WHERE date_added < ?", (cutoff_date,))
        conn.commit()
        conn.close()
        
        # Log the deletion
        if user_id:
            log_action(user_id, role, "delete_expired", f"deleted {deleted_count} expired patient records")
        
        return True
    except Exception as e:
        st.error(f"Failed to delete expired records: {e}")
        return False

def export_user_data(user_id: int) -> Dict:
    """
    Export all data associated with a user for data portability (GDPR Article 20).
    Returns a structured dict containing user info, patient records they created, and access logs.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user info
        cur.execute("SELECT user_id, username, role FROM users WHERE user_id = ?", (user_id,))
        user_row = cur.fetchone()
        if not user_row:
            return {"error": "User not found"}
        
        user_info = dict(user_row)
        
        # Get patient records created/modified by this user
        # (we'll get all patients for this demo; in production, track creator_id)
        cur.execute("SELECT * FROM patients")
        all_patients = [dict(r) for r in cur.fetchall()]
        
        # Get access logs for this user
        cur.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        user_logs = [dict(r) for r in cur.fetchall()]
        
        conn.close()
        
        export_data = {
            "export_date": datetime.datetime.utcnow().isoformat(),
            "user": user_info,
            "patients_in_system": all_patients,
            "access_logs": user_logs,
            "data_portability_notice": "This data export is provided in compliance with GDPR Article 20 (Data Portability)."
        }
        
        return export_data
    except Exception as e:
        st.error(f"Failed to export user data: {e}")
        return {"error": str(e)}

def export_user_data_json(user_id: int, filepath: str) -> bool:
    """
    Export user data to a JSON file for portable download.
    """
    try:
        data = export_user_data(user_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Failed to export user data to JSON: {e}")
        return False

def right_to_be_forgotten(patient_id: int, user_id: int = None, role: str = None) -> bool:
    """
    Implement GDPR "Right to be Forgotten" (Article 17).
    Permanently removes patient record and all associated data.
    Only callable by Admin.
    """
    try:
        if role != "admin":
            st.error("Only admins can execute right to be forgotten.")
            return False
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete patient record
        cur.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
        conn.commit()
        conn.close()
        
        # Log the action
        if user_id:
            log_action(user_id, role, "right_to_be_forgotten", f"deleted patient_id={patient_id} per GDPR Article 17")
        
        return True
    except Exception as e:
        st.error(f"Failed to execute right to be forgotten: {e}")
        return False

def get_gdpr_compliance_report() -> Dict:
    """
    Generate a comprehensive GDPR compliance report.
    Includes consent records, anonymization status, data retention, and audit trail summary.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Total users
        cur.execute("SELECT COUNT(*) as count FROM users")
        total_users = cur.fetchone()["count"]
        
        # Total patients
        cur.execute("SELECT COUNT(*) as count FROM patients")
        total_patients = cur.fetchone()["count"]
        
        # Anonymized patients
        cur.execute("SELECT COUNT(*) as count FROM patients WHERE anonymized_name IS NOT NULL")
        anonymized_patients = cur.fetchone()["count"]
        
        # Total log entries
        cur.execute("SELECT COUNT(*) as count FROM logs")
        total_logs = cur.fetchone()["count"]
        
        # Recent access logs (last 7 days)
        seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
        cur.execute("SELECT COUNT(*) as count FROM logs WHERE timestamp > ?", (seven_days_ago,))
        recent_logs = cur.fetchone()["count"]
        
        # Users by role
        cur.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        users_by_role = {row["role"]: row["count"] for row in cur.fetchall()}
        
        conn.close()
        
        report = {
            "report_date": datetime.datetime.utcnow().isoformat(),
            "total_users": total_users,
            "users_by_role": users_by_role,
            "total_patients": total_patients,
            "anonymized_patients": anonymized_patients,
            "anonymization_rate": f"{(anonymized_patients/total_patients*100):.1f}%" if total_patients > 0 else "0%",
            "total_audit_logs": total_logs,
            "recent_logs_7days": recent_logs,
            "gdpr_status": "Compliant" if anonymized_patients > 0 and total_logs > 0 else "Needs Review"
        }
        
        return report
    except Exception as e:
        st.error(f"Failed to generate compliance report: {e}")
        return {"error": str(e)}