import streamlit as st
import pandas as pd

@st.cache_data
def load_hr_data(csv_path):
    """Load HR CSV file."""
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

def save_hr_data(df, csv_path):
    """Save updated HR data to CSV."""
    try:
        df.to_csv(csv_path, index=False)
        st.success("Data saved successfully.")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to save data: {e}")
