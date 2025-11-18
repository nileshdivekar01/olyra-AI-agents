import os
import streamlit as st
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from data.loader import load_csv, dataset_brief, generate_intelligent_summary
from ai.chat import (
    load_or_generate_prompt,
    save_prompt_to_json,
    call_openai_chat,
    parse_query_from_response,
    compute_math_query,
    filter_dataframe
)
from visuals.charts import (
    plot_histogram,
    plot_scatter,
    plot_correlation_heatmap
)
from prompts.manager import PROMPTS_FILE

load_dotenv()

DEFAULT_CSV_PATH = "doctor.csv"

st.set_page_config(page_title="AI Data Analytics Engine", layout="wide")

with st.sidebar:
    st.header("Settings")
    max_sample = st.number_input("Rows to show in sample", value=5, min_value=1, step=1)
    show_heatmap = st.checkbox("Show correlation heatmap", value=True)
    
    st.markdown("---")
    
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    
    st.markdown("---")
    
    with st.expander("AI Prompt Editor (Advanced)", expanded=False):
        st.markdown("**Edit the system prompt** or let AI auto-generate based on your data:")
        
        st.info("Leave blank to auto-generate smart prompts based on your data!")
        
        try:
            import json
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                current_custom_prompt = data.get("system_prompt", "")
        except:
            current_custom_prompt = ""

        edited_prompt = st.text_area(
            "Custom System Prompt (optional)",
            value=current_custom_prompt,
            height=250,
            help="Leave empty to auto-generate intelligent prompts based on your dataset",
            key="prompt_editor",
            placeholder="Leave blank for auto-generated prompts..."
        )
        
        col_save, col_clear = st.columns(2)
        
        with col_save:
            if st.button("Save Custom", type="primary", use_container_width=True):
                if save_prompt_to_json(edited_prompt):
                    st.success("Saved!")
                    st.rerun()
        
        with col_clear:
            if st.button("Clear (Use Auto)", use_container_width=True):
                if save_prompt_to_json(""):
                    st.success("Will auto-generate!")
                    st.rerun()

if uploaded_file:
    df = load_csv(uploaded_file)
    st.success(f"Loaded: {uploaded_file.name}")
else:
    if os.path.exists(DEFAULT_CSV_PATH):
        df = pd.read_csv(DEFAULT_CSV_PATH, low_memory=False)
        st.info(f"Using example dataset: {DEFAULT_CSV_PATH}")
    else:
        st.warning("Please upload a CSV file to begin analysis")
        st.stop()

st.title("AI Data Analytics Engine")
st.markdown("Upload any CSV file to explore, visualize, and chat with your data using AI.")

st.subheader("Dataset Overview")
st.markdown(generate_intelligent_summary(df))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Rows", f"{df.shape[0]:,}")
with col2:
    st.metric("Total Columns", df.shape[1])
with col3:
    st.metric("Missing Values", int(df.isna().sum().sum()))

st.dataframe(df.head(max_sample), use_container_width=True)

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

st.markdown("---")
st.subheader("Interactive Visualizations")

tab1, tab2, tab3, tab4 = st.tabs(["Histogram", "Scatter", "Bar", "Pie"])

with tab1:
    if numeric_cols:
        col = st.selectbox("Select numeric column", numeric_cols)
        st.plotly_chart(plot_histogram(df, col), use_container_width=True)
    else:
        st.info("No numeric columns available for histogram.")

with tab2:
    if len(numeric_cols) >= 2:
        x = st.selectbox("X-axis", numeric_cols, key="xaxis")
        y = st.selectbox("Y-axis", numeric_cols, key="yaxis")
        color = st.selectbox("Color by (optional)", [None] + cat_cols, index=0)
        st.plotly_chart(plot_scatter(df, x, y, color if color else None), use_container_width=True)
    else:
        st.info("Need at least two numeric columns for scatter plot.")

with tab3:
    if cat_cols and numeric_cols:
        import plotly.express as px
        x = st.selectbox("Categorical column", cat_cols, key="barx")
        y = st.selectbox("Numeric column", numeric_cols, key="bary")
        agg = st.selectbox("Aggregation", ["sum", "mean", "count"], index=1)
        agg_df = df.groupby(x)[y].agg(agg).reset_index()
        st.plotly_chart(px.bar(agg_df, x=x, y=y, title=f"{agg.capitalize()} of {y} by {x}"), use_container_width=True)
    else:
        st.info("Need both categorical and numeric columns for bar chart.")

with tab4:
    if cat_cols:
        import plotly.express as px
        col = st.selectbox("Select categorical column", cat_cols, key="pie")
        pie_data = df[col].value_counts().head(10).reset_index()
        pie_data.columns = [col, "count"]
        st.plotly_chart(px.pie(pie_data, names=col, values="count", title=f"Distribution of {col}"), use_container_width=True)
    else:
        st.info("No categorical columns available for pie chart.")

if show_heatmap:
    fig = plot_correlation_heatmap(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("Chat with Your Data")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_question = st.text_input(
    "Ask anything about your data:",
    placeholder="e.g., Plot Age vs Total_Bill or Show list of Diabetes patients"
)

if st.button("Send", type="primary") and user_question:
    import re
    import plotly.express as px
    
    st.session_state.chat_history.append(("user", user_question))

    math_result = compute_math_query(df, user_question)
    if math_result:
        st.session_state.chat_history.append(("assistant", math_result))
    else:
        sys_prompt = load_or_generate_prompt(df)
        context_text = f"Dataset: {len(df)} rows, {len(df.columns)} columns.\nColumns: {', '.join(df.columns)}"
        user_prompt = f"{context_text}\n\nUser question: {user_question}"
        response = call_openai_chat(sys_prompt, user_prompt)
        st.session_state.chat_history.append(("assistant", response))

    plot_match = re.search(r"[Pp]lot\s+([\w\s]+)\s+vs\s+([\w\s]+)", user_question)
    if not plot_match:
        plot_match = re.search(r"[Pp]lot\s+([\w\s]+)\s+against\s+([\w\s]+)", user_question)

    if plot_match:
        x_col = plot_match.group(1).strip()
        y_col = plot_match.group(2).strip()

        def match_column(name):
            for col in df.columns:
                clean = lambda s: s.lower().replace(" ", "").replace("_", "")
                if clean(col) == clean(name):
                    return col
            return None

        x_real = match_column(x_col)
        y_real = match_column(y_col)

        if x_real and y_real:
            st.success(f"Auto-plotting **{x_real} vs {y_real}**")
            fig = px.scatter(df, x=x_real, y=y_real, title=f"{y_real} vs {x_real}")
            st.plotly_chart(fig, use_container_width=True)
            st.session_state.chat_history.append(("plot", (x_real, y_real, fig)))
        else:
            st.warning(f"Couldn't match '{x_col}' or '{y_col}' to dataset columns.")

    if not math_result:
        sys_prompt = load_or_generate_prompt(df)
        context_text = f"Dataset: {len(df)} rows, {len(df.columns)} columns.\nColumns: {', '.join(df.columns)}"
        user_prompt = f"{context_text}\n\nUser question: {user_question}"
        response = call_openai_chat(sys_prompt, user_prompt)
        
        query_dict = parse_query_from_response(response)
        if query_dict:
            filtered, warnings = filter_dataframe(df, query_dict)
            
            for w in warnings:
                st.session_state.chat_history.append(("assistant", f"{w}"))
            
            if len(filtered) > 0:
                st.session_state.chat_history.append(("dataframe", filtered))
            else:
                st.session_state.chat_history.append(("assistant", "No records match the filter criteria."))

if st.session_state.chat_history:
    st.markdown("### Conversation History")
    for idx, (role, content) in enumerate(st.session_state.chat_history):
        if role == "user":
            st.markdown(f"**You:** {content}")
        elif role == "assistant":
            st.markdown(f"**AI:** {content}")
        elif role == "dataframe":
            st.dataframe(content, use_container_width=True)
            st.caption(f"Showing {len(content)} matching records")
        elif role == "plot":
            x_real, y_real, fig = content
            st.plotly_chart(fig, use_container_width=True, key=f"chat_plot_{idx}")
            st.caption(f"Persistent plot: {y_real} vs {x_real}")

    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()