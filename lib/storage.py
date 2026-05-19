"""Auto-save and load app state (presence matrix + warnings) to local disk."""

import json
import os
from pathlib import Path

import pandas as pd

from .genera import CANONICAL_GENERA

DATA_DIR = Path(os.getenv("APP_DATA_DIR", "./data"))
MATRIX_PATH = DATA_DIR / "matrix.csv"
WARNINGS_PATH = DATA_DIR / "warnings.json"


def ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def empty_matrix() -> pd.DataFrame:
    """Matrix with the Genus column and no paper columns."""
    return pd.DataFrame({"Genus": CANONICAL_GENERA})


def load_matrix() -> pd.DataFrame:
    if MATRIX_PATH.exists():
        df = pd.read_csv(MATRIX_PATH)
        if "Genus" not in df.columns:
            return empty_matrix()
        # Force boolean for paper columns
        for col in df.columns:
            if col != "Genus":
                df[col] = df[col].fillna(False).astype(bool)
        return df
    return empty_matrix()


def save_matrix(df: pd.DataFrame) -> None:
    ensure_dir()
    df.to_csv(MATRIX_PATH, index=False)


def load_warnings() -> dict:
    if WARNINGS_PATH.exists():
        with open(WARNINGS_PATH) as f:
            return json.load(f)
    return {}


def save_warnings(warnings: dict) -> None:
    ensure_dir()
    with open(WARNINGS_PATH, "w") as f:
        json.dump(warnings, f, indent=2)


def merge_uploaded_csv(current: pd.DataFrame, uploaded: pd.DataFrame) -> pd.DataFrame:
    """
    Merge an uploaded CSV into the current matrix.

    Rules:
    - Genus column is preserved from CANONICAL_GENERA (rows fixed).
    - Any unknown genera in the uploaded CSV are dropped (silently — they'd be warnings).
    - Paper columns from the upload are added; if a column already exists, the
      uploaded values OR-merge with current (True if either is True).
    """
    base = empty_matrix()

    # Start with current matrix merged onto canonical
    if not current.empty and "Genus" in current.columns:
        for col in current.columns:
            if col == "Genus":
                continue
            mapping = dict(zip(current["Genus"], current[col].astype(bool)))
            base[col] = base["Genus"].map(mapping).fillna(False).astype(bool)

    if uploaded.empty or "Genus" not in uploaded.columns:
        return base

    for col in uploaded.columns:
        if col == "Genus":
            continue
        mapping = dict(zip(uploaded["Genus"], uploaded[col]))
        uploaded_col = (
            base["Genus"].map(mapping).fillna(False).astype(bool)
        )
        if col in base.columns:
            base[col] = base[col] | uploaded_col
        else:
            base[col] = uploaded_col

    return base


def add_paper_column(df: pd.DataFrame, column_name: str,
                     present_genera: set[str]) -> pd.DataFrame:
    """Add or overwrite a paper column with the given set of present genera."""
    df = df.copy()
    df[column_name] = df["Genus"].isin(present_genera)
    return df


def unique_column_name(df: pd.DataFrame, name: str) -> str:
    """Return `name`, or `name (2)`, `name (3)`, ... if it already exists."""
    if name not in df.columns:
        return name
    i = 2
    while f"{name} ({i})" in df.columns:
        i += 1
    return f"{name} ({i})"
