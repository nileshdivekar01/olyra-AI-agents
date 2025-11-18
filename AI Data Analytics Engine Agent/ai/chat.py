import os
import re
import json
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv 
from prompts.manager import generate_dynamic_system_prompt, PROMPTS_FILE

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    st.warning("OPENAI_API_KEY environment variable not set. Set it before running.")
    client = None
else:
    client = OpenAI(api_key=OPENAI_API_KEY)


def load_or_generate_prompt(df: pd.DataFrame = None) -> str:
    """Load custom prompt from file, or generate dynamic one from dataset."""
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            custom_prompt = data.get("system_prompt", "")
            if custom_prompt.strip():
                return custom_prompt
    except FileNotFoundError:
        pass
    except Exception as e:
        st.warning(f"Error reading {PROMPTS_FILE}: {e}")
    
    if df is not None:
        return generate_dynamic_system_prompt(df)
    
    return "You are an expert data analyst assistant."


def save_prompt_to_json(prompt: str, file_path: str = PROMPTS_FILE) -> bool:
    """Save the updated prompt to JSON file."""
    try:
        data = {"system_prompt": prompt}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving prompt: {e}")
        return False


def call_openai_chat(system: str, user_prompt: str, model: str = OPENAI_MODEL, max_tokens: int = 1000) -> str:
    """Call OpenAI Chat API."""
    if not client:
        return "Missing API key."
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI request failed: {e}"


def parse_query_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON query from AI response."""
    if not response or "QUERY:" not in response:
        return None
    try:
        query_part = response.split("QUERY:")[1].strip()
        json_match = re.search(r'\{.*\}', query_part, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        return None
    return None


def compute_math_query(df: pd.DataFrame, question: str) -> Optional[str]:
    """Detect and compute simple math operations like avg, sum, max, min."""
    q = question.lower()

    operations = {
        "average": "mean",
        "avg": "mean",
        "mean": "mean",
        "sum": "sum",
        "total": "sum",
        "maximum": "max",
        "max": "max",
        "minimum": "min",
        "min": "min",
        "largest": "max",
        "smallest": "min",
        "count": "count",
        "how many": "count",
        "number of": "count"
    }

    op = None
    for word, func in operations.items():
        if word in q:
            op = func
            break

    if not op:
        return None

    matched_col = None
    for col in df.columns:
        clean_col = col.lower().replace("_", "").replace(" ", "")
        clean_q = q.replace("_", "").replace(" ", "")
        if clean_col in clean_q:
            matched_col = col
            break

    if not matched_col:
        return None

    try:
        series = pd.to_numeric(df[matched_col], errors="coerce")
        result = None
        if op == "mean":
            result = series.mean()
        elif op == "sum":
            result = series.sum()
        elif op == "max":
            result = series.max()
        elif op == "min":
            result = series.min()
        elif op == "count":
            result = series.count()

        if pd.isna(result):
            return None
        return f"The **{op}** of `{matched_col}` is **{result:.2f}**."
    except Exception as e:
        return f"Could not compute {op} for {matched_col}: {e}"


def looks_like_identifier(colname: str, series: pd.Series) -> bool:
    """Heuristic: columns containing 'id' or mostly integers with few unique values -> likely identifier."""
    name_lower = colname.lower()
    if "id" in name_lower or "code" in name_lower:
        return True

    if not pd.api.types.is_numeric_dtype(series):
        return True

    uniq_frac = series.dropna().nunique() / max(1, len(series))
    if pd.api.types.is_integer_dtype(series) and uniq_frac < 0.05:
        return True
    return False


def compute_value_for_column(filtered: pd.DataFrame, ref_col: str, agg: str):
    """Compute aggregate (mean, max, min) of ref_col safely."""
    if ref_col not in filtered.columns:
        return None
        
    ser = pd.to_numeric(filtered[ref_col], errors="coerce")
    if agg in ("avg", "mean"):
        return ser.mean()
    if agg in ("max", "maximum"):
        return ser.max()
    if agg in ("min", "minimum"):
        return ser.min()
    if agg in ("sum", "total"):
        return ser.sum()
    return None


def compute_dynamic_value(filtered: pd.DataFrame, col: str, raw_val):
    """Interpret values like number, 'average', or {'avg':'$Col'}."""
    if isinstance(raw_val, (int, float)):
        return float(raw_val)

    if isinstance(raw_val, str):
        rv = raw_val.strip().lower()
        if rv in ("average", "mean"):
            return pd.to_numeric(filtered[col], errors="coerce").mean()
        if rv in ("max", "maximum"):
            return pd.to_numeric(filtered[col], errors="coerce").max()
        if rv in ("min", "minimum"):
            return pd.to_numeric(filtered[col], errors="coerce").min()

        asnum = pd.to_numeric(raw_val, errors="coerce")
        if not pd.isna(asnum):
            return float(asnum)
        return None

    if isinstance(raw_val, dict):
        for k, v in raw_val.items():
            agg = k.lower()
            if isinstance(v, str) and v.startswith("$"):
                ref_col = v[1:].strip()
                if ref_col in filtered.columns:
                    return compute_value_for_column(filtered, ref_col, agg)
            if isinstance(v, (int, float)):
                return float(v)
        return None
    return None


def normalize_op(op_raw: str) -> str:
    """Normalize operator string."""
    if not isinstance(op_raw, str):
        return ""
    op = op_raw.lower()
    if op.startswith("$"):
        op = op[1:]
    return op


def filter_dataframe(df: pd.DataFrame, query_dict: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
    """Filter dataframe based on query dictionary and return filtered df with warnings."""
    filtered = df.copy()
    warnings_msgs = []
    
    try:
        for col, condition in query_dict.items():
            if col not in filtered.columns:
                warnings_msgs.append(f"Column '{col}' not found in dataset.")
                continue

            if isinstance(condition, dict):
                op_raw = list(condition.keys())[0]
                raw_val = condition[op_raw]
                op = normalize_op(op_raw)

                dyn_val = compute_dynamic_value(filtered, col, raw_val)

                if dyn_val is None and isinstance(raw_val, dict):
                    for v in raw_val.values():
                        if isinstance(v, str) and v.startswith("$"):
                            ref = v[1:].strip()
                            if ref in filtered.columns:
                                if looks_like_identifier(ref, filtered[ref]):
                                    fallback_mean = pd.to_numeric(filtered[col], errors="coerce").mean()
                                    warnings_msgs.append(
                                        f"Ref column '{ref}' looks like an identifier — comparing to its aggregate is likely meaningless. "
                                        f"Falling back to mean of '{col}' ({fallback_mean:.2f})."
                                    )
                                    dyn_val = fallback_mean
                                else:
                                    agg_key = list(raw_val.keys())[0]
                                    dyn_val = compute_value_for_column(filtered, ref, agg_key)
                                    break

                if dyn_val is None:
                    warnings_msgs.append(f"Could not resolve comparison value for `{col}` with raw `{raw_val}`.")
                    continue

                left_ser = pd.to_numeric(filtered[col], errors="coerce")
                if op in ("gt",):
                    filtered = filtered[left_ser > dyn_val]
                elif op in ("lt",):
                    filtered = filtered[left_ser < dyn_val]
                elif op in ("gte",):
                    filtered = filtered[left_ser >= dyn_val]
                elif op in ("lte",):
                    filtered = filtered[left_ser <= dyn_val]
                elif op in ("eq",):
                    filtered = filtered[left_ser == dyn_val]
                else:
                    warnings_msgs.append(f"Unsupported operator '{op_raw}' for column '{col}'.")
            else:
                filtered = filtered[filtered[col].astype(str).str.contains(str(condition), case=False, na=False)]

    except Exception as e:
        warnings_msgs.append(f"Error during filtering: {e}")
    
    return filtered, warnings_msgs