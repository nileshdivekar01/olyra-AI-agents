import pandas as pd
import numpy as np
import plotly.express as px
from typing import Optional

def plot_histogram(df: pd.DataFrame, col: str):
    """Create a histogram with box plot for a numeric column."""
    return px.histogram(
        df, 
        x=col, 
        marginal="box", 
        nbins=40, 
        title=f"Distribution of {col}"
    )

def plot_scatter(df: pd.DataFrame, x: str, y: str, color: Optional[str] = None):
    """Create a scatter plot with optional color encoding."""
    return px.scatter(
        df, 
        x=x, 
        y=y, 
        color=color, 
        title=f"{y} vs {x}"
    )

def plot_correlation_heatmap(df: pd.DataFrame):
    """Create a correlation heatmap for numeric columns."""
    df_num = df.select_dtypes(include=[np.number])
    
    if df_num.empty or len(df_num.columns) < 2:
        return None
    
    corr = df_num.corr()
    fig = px.imshow(
        corr, 
        text_auto='.2f', 
        aspect="auto", 
        title="Correlation Matrix"
    )
    return fig

def plot_bar_chart(df: pd.DataFrame, x: str, y: str, agg: str = "mean"):
    """Create a bar chart with aggregation."""
    agg_df = df.groupby(x)[y].agg(agg).reset_index()
    return px.bar(
        agg_df, 
        x=x, 
        y=y, 
        title=f"{agg.capitalize()} of {y} by {x}"
    )

def plot_pie_chart(df: pd.DataFrame, col: str, top_n: int = 10):
    """Create a pie chart for categorical column distribution."""
    pie_data = df[col].value_counts().head(top_n).reset_index()
    pie_data.columns = [col, "count"]
    return px.pie(
        pie_data, 
        names=col, 
        values="count", 
        title=f"Distribution of {col}"
    )