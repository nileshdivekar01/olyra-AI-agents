import io
from typing import Dict, Any
import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data
def load_csv(file_bytes: io.BytesIO) -> pd.DataFrame:
    """Load CSV file with fallback encoding."""
    try:
        file_bytes.seek(0)
        df = pd.read_csv(file_bytes)
        return df
    except Exception:
        file_bytes.seek(0)
        df = pd.read_csv(file_bytes, encoding='latin1', low_memory=False)
        return df

def dataset_brief(df: pd.DataFrame, n_sample: int = 5) -> Dict[str, Any]:
    """Generate a comprehensive brief of the dataset."""
    brief = {
        'n_rows': len(df),
        'n_cols': len(df.columns),
        'columns': []
    }
    
    for col in df.columns:
        col_info = {
            "name": str(col),
            "dtype": str(df[col].dtype),
            "n_missing": int(df[col].isna().sum())
        }
        
        if pd.api.types.is_numeric_dtype(df[col]):
            nonnull = df[col].dropna()
            if not nonnull.empty:
                col_info.update({
                    'mean': float(nonnull.mean()),
                    'median': float(nonnull.median()),
                    'std': float(nonnull.std()),
                    'min': float(nonnull.min()),
                    'max': float(nonnull.max()),
                })
        else:
            nonnull = df[col].dropna().astype(str)
            col_info.update({
                'n_unique': int(nonnull.nunique()),
                'top_values': list(nonnull.value_counts().head(5).index.astype(str))
            })
        
        brief['columns'].append(col_info)
    
    brief['sample_rows'] = df.head(n_sample).to_dict(orient='records')
    return brief

def generate_intelligent_summary(df: pd.DataFrame) -> str:
    """Generate a generic summary that works for any dataset."""
    insights = [f"**Dataset Overview**: {len(df):,} rows, {df.shape[1]} columns"]
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        insights.append(f"**Numeric Columns**: {len(numeric_cols)}")
    
    cat_cols = df.select_dtypes(exclude=[np.number]).columns
    if len(cat_cols) > 0:
        insights.append(f"**Categorical Columns**: {len(cat_cols)}")
    
    missing_pct = (df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100
    if missing_pct > 0:
        insights.append(f"**Missing Data**: {missing_pct:.1f}%")
    
    if len(df.columns) > 0:
        first_col = df.columns[0]
        if df[first_col].dtype == 'object':
            unique_count = df[first_col].nunique()
            insights.append(f"**'{first_col}' has {unique_count} unique values**")
    return "\n\n".join(insights)