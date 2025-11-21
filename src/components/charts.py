from matplotlib import pyplot as plt
import pandas as pd
import streamlit as st

def plot_patient_statistics(patient_data):
    df = pd.DataFrame(patient_data)
    if df.empty:
        st.info("No patient statistics available.")
        return
    st.subheader("Patient Statistics")
    # st.bar_chart(df['count'], x=df['category'])
    st.bar_chart(df, x="category", y="count")
    

def plot_appointment_trends(appointment_data):
    df = pd.DataFrame(appointment_data)
    st.subheader("Appointment Trends")
    fig, ax = plt.subplots()
    ax.plot(df['date'], df['appointments'], marker='o')
    ax.set_title('Appointments Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Appointments')
    st.pyplot(fig)

def plot_staff_performance(staff_data):
    df = pd.DataFrame(staff_data)
    st.subheader("Staff Performance")
    st.line_chart(df['performance'], x=df['staff_member'])