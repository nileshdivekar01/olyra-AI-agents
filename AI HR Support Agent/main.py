import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
from data_handler.data_handler import load_hr_data, save_hr_data
from llm.llm_handler import query_openai
from ui.ui_components import show_employee_data, add_employee_form, update_leave_form

load_dotenv()

CSV_FILE_PATH = os.getenv("HR_CSV_PATH")

st.set_page_config(page_title="AI HR Support Agent (Healthcare)", layout="wide")
st.title("AI HR Support Agent (Healthcare)")
st.caption("24/7 virtual HR assistant for hospital staff — built with Streamlit + OpenAI")

st.sidebar.header("Settings")
csv_user_path = st.sidebar.text_input("CSV File Path", value=CSV_FILE_PATH)
if st.sidebar.button("Reload Data"):
    CSV_FILE_PATH = csv_user_path
    st.cache_data.clear()

df = load_hr_data(CSV_FILE_PATH)

if df.empty:
    st.warning("No data found. Please check your CSV path and reload.")
else:
    st.success(f"Loaded {len(df)} employee records from CSV.")
    show_employee_data(df)

st.markdown("### Ask the AI HR Assistant")
user_input = st.text_area("Type your HR question (e.g., 'Show ICU nurses with <10 leave balance'):")

if st.button("Get Response"):
    if user_input.strip():
        with st.spinner("Thinking..."):
            response = query_openai(user_input, df)
        st.markdown("**AI Response:**")
        st.write(response)
    else:
        st.warning("Please enter a question.")

st.markdown("---")
st.subheader("Manage HR Data")
tab1, tab2 = st.tabs(["Add Employee", "Update Leave Balance"])

with tab1:
    add_employee_form(df, CSV_FILE_PATH)

with tab2:
    update_leave_form(df, CSV_FILE_PATH)

st.markdown("---")
st.caption("Built using Streamlit and OpenAI | 2025 Healthcare HR AI")
