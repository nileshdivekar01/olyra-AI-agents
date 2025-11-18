import streamlit as st
import pandas as pd
from data_handler.data_handler import save_hr_data

def show_employee_data(df):
    with st.expander("View Employee Data"):
        st.dataframe(df, use_container_width=True)

def add_employee_form(df, csv_path):
    st.markdown("### Add New Employee")
    with st.form("add_form"):
        new_employee = {
            "Employee_ID": st.text_input("Employee ID"),
            "full_name": st.text_input("Full Name"),
            "role": st.text_input("Role"),
            "department": st.text_input("Department"),
            "shift": st.selectbox("Shift", ["Morning", "Evening", "Night"]),
            "leave_balance": st.number_input("Leave Balance", 0, 30, 10),
            "manager": st.text_input("Manager"),
            "employment_type": st.selectbox("Employment Type", ["Full-time", "Part-time"]),
            "email": st.text_input("Email"),
            "location": st.text_input("Location")
        }

        submitted = st.form_submit_button("Add Employee")

        if submitted:
            if new_employee["Employee_ID"] in df["Employee_ID"].values:
                st.error("Employee ID already exists.")
            else:
                df = pd.concat([df, pd.DataFrame([new_employee])], ignore_index=True)
                save_hr_data(df, csv_path)

def update_leave_form(df, csv_path):
    st.markdown("### Update Leave Balance")

    emp_id = st.selectbox("Select Employee ID", df["Employee_ID"])
    new_balance = st.number_input("New Leave Balance", 0, 30, 10)

    if st.button("Update Leave"):
        df.loc[df["Employee_ID"] == emp_id, "leave_balance"] = new_balance
        save_hr_data(df, csv_path)
