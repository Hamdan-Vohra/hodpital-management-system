import streamlit as st
from streamlit import session_state as st_session
from database.connection import get_patients, add_patient, log_action
from utils.gdpr import anonymize_data
from utils.gdpr import log_data_access

def view_patients():
    st.title("Patient Records")

    user = st_session.get("user")
    role = st_session.get("role", "")
    user_id = st_session.get("user_id")

    patients = get_patients()
    
    # Display existing patients
    st.markdown("### Patient List")
    if not patients:
        st.info("No patient records found.")
    else:
        for p in patients:
            pid = p["patient_id"]
            st.subheader(f"Patient ID: {pid}")

            # Admin can see raw data + anonymized
            if role == "admin":
                st.write(f"Name: {p.get('name')}")
                st.write(f"Contact: {p.get('contact')}")
                st.write(f"Diagnosis: {p.get('diagnosis')}")
                st.write(f"Anonymized Name: {p.get('anonymized_name') or '(not anonymized)'}")
                st.write(f"Anonymized Contact: {p.get('anonymized_contact') or '(not anonymized)'}")
                log_data_access(user_id, role, "patient_record", patient_id=pid)

            # Doctor sees anonymized view only
            elif role == "doctor":
                st.write(f"Anonymized Name: {p.get('anonymized_name') or '(not anonymized)'}")
                st.write(f"Anonymized Contact: {p.get('anonymized_contact') or '(not anonymized)'}")
                st.write(f"Diagnosis: {p.get('diagnosis')}")
                log_data_access(user_id, role, "patient_record", patient_id=pid)

            # Receptionist cannot view sensitive raw identifiers
            elif role == "receptionist":
                st.write(f"Anonymized Name: {p.get('anonymized_name') or '(masked)'}")
                st.write(f"Anonymized Contact: {p.get('anonymized_contact') or '(masked)'}")
                st.write(f"Diagnosis: {p.get('diagnosis')}")
                log_data_access(user_id, role, "patient_record", patient_id=pid)

            else:
                st.write("Role not recognized. Minimal view shown.")
                st.write(f"Anonymized Name: {p.get('anonymized_name') or '(masked)'}")

            # Admin or authorized staff can anonymize a single patient
            cols = st.columns([1, 3])
            if cols[0].button("Anonymize", key=f"anon_{pid}"):
                if role in ("admin", "doctor"):
                    ok = anonymize_data(pid, user_id=user_id, role=role)
                    if ok:
                        st.success(f"Patient {pid} anonymized.")
                    else:
                        st.error("Failed to anonymize patient.")
                else:
                    st.error("Only admin/doctor can anonymize records.")

            st.markdown("---")

    # Add patient record button (only for admin and receptionist)
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    
    can_add = role in ("admin", "receptionist")
    
    with col2:
        if st.button("➕ Add Patient Record", disabled=not can_add):
            st_session.show_add_patient_form = True
    
    if not can_add:
        if role:
            st.info(f"⚠️ Role '{role}' does not have permission to add patient records.")
        else:
            st.info("⚠️ You must be logged in with appropriate role to add patient records.")
    # Show form only if button was clicked
    if st_session.get("show_add_patient_form", False):
        st.markdown("### Add Patient Record")
        with st.form("add_patient_form"):
            name = st.text_input("Full Name", placeholder="Enter patient full name")
            contact = st.text_input("Contact Number", placeholder="e.g., 0300-1234567")
            diagnosis = st.text_area("Diagnosis", placeholder="Enter diagnosis details", height=100)
            
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("✓ Add Patient Record")
            with col_cancel:
                cancel = st.form_submit_button("✗ Cancel")
            
            if cancel:
                st_session.show_add_patient_form = False
                st.rerun()
            
            if submitted:
                # Form validation
                errors = []
                
                if not name or not name.strip():
                    errors.append("Full name is required.")
                if not contact or not contact.strip():
                    errors.append("Contact number is required.")
                if not diagnosis or not diagnosis.strip():
                    errors.append("Diagnosis is required.")
                
                # Validate name (only letters, spaces, hyphens)
                if name and name.strip():
                    if not all(c.isalpha() or c.isspace() or c == '-' for c in name):
                        errors.append("Name should only contain letters, spaces, and hyphens.")
                
                # Validate contact (must have at least 11 digits)
                if contact and contact.strip():
                    digits_in_contact = sum(1 for c in contact if c.isdigit())
                    if digits_in_contact < 11:
                        errors.append("Contact number must contain at least 11 digits.")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        # Add patient to database
                        patient_id = add_patient(
                            name=name.strip(),
                            contact=contact.strip(),
                            diagnosis=diagnosis.strip(),
                            added_by_user_id=user_id,
                            role=role
                        )
                        st.success(f"✓ Patient record added successfully (ID: {patient_id})")
                        st_session.show_add_patient_form = False
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add patient record: {e}")

if __name__ == "__main__":
    view_patients()