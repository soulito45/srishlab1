"""
query_engine.py
----------------
A safe, no-eval query engine that lets end users filter and group
a DataFrame through simple structured parameters coming from the UI
(instead of writing raw pandas/SQL code themselves).
"""

import pandas as pd

OPERATORS = {
    "equals": lambda s, v: s.astype(str).str.lower() == str(v).lower(),
    "not_equals": lambda s, v: s.astype(str).str.lower() != str(v).lower(),
    "greater_than": lambda s, v: pd.to_numeric(s, errors="coerce") > float(v),
    "less_than": lambda s, v: pd.to_numeric(s, errors="coerce") < float(v),
    "greater_equal": lambda s, v: pd.to_numeric(s, errors="coerce") >= float(v),
    "less_equal": lambda s, v: pd.to_numeric(s, errors="coerce") <= float(v),
    "contains": lambda s, v: s.astype(str).str.contains(str(v), case=False, na=False, regex=False),
}


def apply_filters(df, filters):
    """
    filters: list of dicts -> [{"column": "Price", "operator": "greater_than", "value": "1000"}, ...]
    All filters are combined with AND logic.
    """
    result = df.copy()
    applied = []
    for f in filters:
        if not isinstance(f, dict):
            raise ValueError("Each filter must be an object.")
        col, op, val = f.get("column"), f.get("operator"), f.get("value")
        if col not in result.columns:
            raise ValueError(f"Unknown filter column: {col}")
        if op not in OPERATORS:
            raise ValueError(f"Unknown filter operator: {op}")
        if val is None or val == "":
            raise ValueError("Filter values cannot be empty.")
        try:
            mask = OPERATORS[op](result[col], val)
            result = result[mask]
            applied.append(f"{col} {op.replace('_', ' ')} {val}")
        except (ValueError, TypeError) as error:
            raise ValueError(f"Invalid value for {op}: {val}") from error
    return result, applied


def apply_group(df, group_col, agg_col, agg_func):
    """Group by group_col, aggregate agg_col using agg_func (sum/mean/count/max/min)."""
    valid_funcs = {"sum", "mean", "count", "max", "min", "median"}
    if agg_func not in valid_funcs or group_col not in df.columns or agg_col not in df.columns:
        return None
    try:
        if agg_func == "count":
            grouped = df.groupby(group_col, dropna=False).size().reset_index(name="count")
            grouped = grouped.sort_values(by="count", ascending=False)
        else:
            grouped = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
            grouped = grouped.sort_values(by=agg_col, ascending=False)
        return grouped
    except Exception:
        return None


def paginate(df, page=1, per_page=25):
    page = max(1, int(page))
    total = len(df)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]
    return page_df, total, total_pages
