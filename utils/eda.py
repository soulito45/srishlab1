"""
eda.py
------
Core auto-EDA (Exploratory Data Analysis) engine.
Given a pandas DataFrame, produces a rich dictionary of statistics,
data-quality signals and Plotly-ready chart JSON that the Flask
templates / JS front-end can render.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import json


MISSING_VALUES = ["", " ", "NA", "N/A", "na", "n/a", "null", "NULL", "None", "none", "-", "--"]
MAX_ANALYSIS_ROWS = 250_000
MAX_ANALYSIS_COLUMNS = 200


def clean_dataframe(df):
    """Clean common spreadsheet problems and return the frame and a change report."""
    report = {
        "original_rows": int(len(df)),
        "original_columns": int(len(df.columns)),
        "trimmed_cells": 0,
        "converted_numeric_columns": [],
        "converted_date_columns": [],
        "removed_empty_rows": 0,
        "removed_empty_columns": [],
        "removed_unnamed_columns": [],
        "rows_with_unnamed_data": 0,
        "removed_duplicate_rows": 0,
    }

    # Make blank or repeated headers usable for grouping, filtering, and charts.
    headers = []
    seen_headers = {}
    for position, column in enumerate(df.columns, start=1):
        header = str(column).strip() or f"Column_{position}"
        count = seen_headers.get(header, 0) + 1
        seen_headers[header] = count
        headers.append(header if count == 1 else f"{header}_{count}")
    df.columns = headers

    for column in df.select_dtypes(include=["object", "string"]).columns:
        before = df[column].copy()
        trimmed = before.map(lambda value: isinstance(value, str) and value != value.strip())
        df[column] = df[column].map(lambda value: value.strip() if isinstance(value, str) else value)
        report["trimmed_cells"] += int(trimmed.sum())
        df[column] = df[column].replace(MISSING_VALUES, np.nan)

    # Convert columns that are overwhelmingly numeric, including common CSV formatting.
    for column in df.select_dtypes(include=["object", "string"]).columns:
        normalized = df[column].astype("string").str.replace(r"[$€£₹,]", "", regex=True)
        normalized = normalized.str.replace("%", "", regex=False)
        numeric = pd.to_numeric(normalized, errors="coerce")
        non_empty = df[column].notna().sum()
        if non_empty and numeric.notna().sum() / non_empty >= 0.8:
            df[column] = numeric
            report["converted_numeric_columns"].append(column)

    # Parse date-like fields only when conversion is reliable enough to avoid corrupting text.
    for column in df.select_dtypes(include=["object", "string"]).columns:
        if not any(token in column.lower() for token in ("date", "time", "timestamp")):
            continue
        parsed = pd.to_datetime(df[column], errors="coerce", format="mixed")
        valid_ratio = parsed.notna().sum() / max(df[column].notna().sum(), 1)
        if valid_ratio >= 0.8:
            df[column] = parsed
            report["converted_date_columns"].append(column)

    empty_rows = df.isna().all(axis=1)
    report["removed_empty_rows"] = int(empty_rows.sum())
    df = df.loc[~empty_rows].copy()

    unnamed_columns = [column for column in df.columns if str(column).lower().startswith("unnamed:")]
    if unnamed_columns:
        report["removed_unnamed_columns"] = unnamed_columns
        report["rows_with_unnamed_data"] = int(df[unnamed_columns].notna().any(axis=1).sum())
        df = df.drop(columns=unnamed_columns)

    empty_columns = df.columns[df.isna().all()].tolist()
    report["removed_empty_columns"] = empty_columns
    if empty_columns:
        df = df.drop(columns=empty_columns)

    before_duplicates = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report["removed_duplicate_rows"] = int(before_duplicates - len(df))
    report["final_rows"] = int(len(df))
    report["final_columns"] = int(len(df.columns))
    report["total_changes"] = sum([
        report["trimmed_cells"], report["removed_empty_rows"],
        len(report["removed_empty_columns"]), len(report["removed_unnamed_columns"]),
        report["rows_with_unnamed_data"], report["removed_duplicate_rows"],
        len(report["converted_numeric_columns"]), len(report["converted_date_columns"]),
    ])
    return df, report


def load_dataframe_with_report(filepath):
    """Load a CSV or Excel file and return its cleaned frame with quality metrics."""
    malformed_rows_skipped = 0

    def skip_bad_line(_bad_line):
        nonlocal malformed_rows_skipped
        malformed_rows_skipped += 1
        return None

    if filepath.lower().endswith(".csv"):
        try:
            df = pd.read_csv(filepath, encoding="utf-8", na_values=MISSING_VALUES, keep_default_na=True,
                             engine="python", on_bad_lines=skip_bad_line)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="latin1", na_values=MISSING_VALUES, keep_default_na=True,
                             engine="python", on_bad_lines=skip_bad_line)
    else:
        df = pd.read_excel(filepath, na_values=MISSING_VALUES, keep_default_na=True)

    if len(df) > MAX_ANALYSIS_ROWS or len(df.columns) > MAX_ANALYSIS_COLUMNS:
        raise ValueError(
            f"The file is too large to analyze. Maximum: {MAX_ANALYSIS_ROWS:,} rows "
            f"and {MAX_ANALYSIS_COLUMNS} columns."
        )

    cleaned, report = clean_dataframe(df)
    report["malformed_rows_skipped"] = malformed_rows_skipped
    report["total_changes"] += malformed_rows_skipped
    if cleaned.empty or cleaned.shape[1] == 0:
        raise ValueError("The file contains no usable data rows or columns.")
    return cleaned, report


def load_dataframe(filepath):
    """Load and clean a CSV or Excel file, returning only the analysis-ready frame."""
    df, _ = load_dataframe_with_report(filepath)
    return df


def basic_overview(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "str", "category", "bool"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    return {
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "datetime_cols": datetime_cols,
        "total_missing": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
    }


def column_profile(df):
    """Per-column profile: dtype, missing %, unique count, sample values."""
    profiles = []
    n = len(df)
    for col in df.columns:
        series = df[col]
        missing = int(series.isnull().sum())
        missing_pct = round((missing / n) * 100, 2) if n else 0
        dtype = str(series.dtype)

        profile = {
            "name": col,
            "dtype": dtype,
            "missing": missing,
            "missing_pct": missing_pct,
            "unique": int(series.nunique()),
        }

        if pd.api.types.is_numeric_dtype(series):
            desc = series.describe()
            profile.update({
                "zeros": int(series.eq(0).sum()),
                "mean": round(float(desc.get("mean", 0)), 2) if not pd.isna(desc.get("mean", np.nan)) else None,
                "std": round(float(desc.get("std", 0)), 2) if not pd.isna(desc.get("std", np.nan)) else None,
                "min": round(float(desc.get("min", 0)), 2) if not pd.isna(desc.get("min", np.nan)) else None,
                "max": round(float(desc.get("max", 0)), 2) if not pd.isna(desc.get("max", np.nan)) else None,
            })
        else:
            top = series.mode()
            profile["top_value"] = str(top.iloc[0]) if not top.empty else "N/A"

        profiles.append(profile)
    return profiles


def missing_value_chart(df):
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        return None
    fig = px.bar(
        x=missing.values, y=missing.index, orientation="h",
        labels={"x": "Missing Values", "y": "Column"},
        title="Missing Values by Column",
        color=missing.values, color_continuous_scale="Reds"
    )
    fig.update_layout(template="plotly_dark", height=max(300, len(missing) * 35),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       coloraxis_showscale=False)
    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def correlation_heatmap(df):
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return None
    corr = numeric_df.corr().round(2)
    fig = px.imshow(
        corr, text_auto=True, aspect="auto",
        color_continuous_scale="RdBu_r", title="Correlation Heatmap"
    )
    fig.update_layout(template="plotly_dark", height=500,
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def numeric_distribution_charts(df, max_cols=6):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()[:max_cols]
    charts = {}
    for col in numeric_cols:
        fig = px.histogram(df, x=col, nbins=30, title=f"Distribution of {col}",
                            color_discrete_sequence=["#7c5cff"])
        fig.update_layout(template="plotly_dark", height=320,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=30, r=20, t=45, b=30))
        charts[col] = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return charts


def categorical_top_values(df, max_cols=6, top_n=8):
    cat_cols = df.select_dtypes(include=["object", "str", "category", "bool"]).columns.tolist()[:max_cols]
    charts = {}
    for col in cat_cols:
        counts = df[col].dropna().astype(str).value_counts().head(top_n)
        if counts.empty:
            continue
        fig = px.bar(x=counts.index, y=counts.values, title=f"Top values in {col}",
                     labels={"x": col, "y": "Count"}, color_discrete_sequence=["#22d3ee"])
        fig.update_layout(template="plotly_dark", height=320,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=30, r=20, t=45, b=30))
        charts[col] = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return charts


def build_custom_chart(df, chart_type, x_col, y_col=None, agg_func=None):
    """
    Build a single Plotly chart JSON based on user-selected options
    for the interactive chart-builder page.
    """
    try:
        if chart_type in ("bar", "line") and y_col and agg_func:
            grouped = df.groupby(x_col, dropna=False)[y_col].agg(agg_func).reset_index()
            if chart_type == "bar":
                grouped = grouped.sort_values(by=y_col, ascending=False)
            elif pd.api.types.is_datetime64_any_dtype(grouped[x_col]):
                grouped = grouped.sort_values(by=x_col, ascending=True)
            grouped = grouped.head(30)
            if chart_type == "bar":
                fig = px.bar(grouped, x=x_col, y=y_col, color=y_col,
                             color_continuous_scale="Viridis",
                             title=f"{agg_func.title()} of {y_col} by {x_col}")
            else:
                fig = px.line(grouped, x=x_col, y=y_col, markers=True,
                               title=f"{agg_func.title()} of {y_col} by {x_col}")

        elif chart_type == "scatter" and y_col:
            fig = px.scatter(df, x=x_col, y=y_col, color=y_col,
                              color_continuous_scale="Plasma",
                              title=f"{x_col} vs {y_col}")

        elif chart_type == "pie":
            counts = df[x_col].astype(str).value_counts().head(12).reset_index()
            counts.columns = [x_col, "count"]
            fig = px.pie(counts, names=x_col, values="count", title=f"Share of {x_col}",
                         hole=0.45)

        elif chart_type == "box" and y_col:
            fig = px.box(df, x=x_col, y=y_col, color=x_col, title=f"{y_col} distribution by {x_col}")

        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_col, nbins=30, title=f"Distribution of {x_col}")

        else:
            return {"error": "Invalid chart configuration."}

        fig.update_layout(template="plotly_dark", height=460,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    except Exception as e:
        return {"error": str(e)}


def build_grouped_bar_chart(grouped, x_col, y_col, agg_func):
    """Render an already aggregated result without aggregating it a second time."""
    if x_col not in grouped.columns or y_col not in grouped.columns:
        return {"error": "Invalid grouped chart columns."}
    try:
        display = grouped.head(30)
        fig = px.bar(display, x=x_col, y=y_col, title=f"{agg_func.title()} of {y_col}")
        fig.update_layout(template="plotly_dark", height=460,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    except Exception as e:
        return {"error": str(e)}
