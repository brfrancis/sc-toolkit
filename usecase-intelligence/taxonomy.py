"""
Use case taxonomy — loaded from data/use_cases.csv
Source: all_blueprint_use_cases.csv
355 use cases across Finance, Supply Chain, IT, Marketing, Human Resources.

Usage:
    from usecase_intelligence.taxonomy import load_taxonomy, get_use_case_names

    taxonomy = load_taxonomy()
    # Returns: {function: {department: [use_case, ...]}}

    names = get_use_case_names()
    # Returns: flat sorted list of all use case names
"""

import os
import pandas as pd
from functools import lru_cache

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "use_cases.csv")


@lru_cache(maxsize=1)
def load_taxonomy() -> dict:
    """
    Load use cases from CSV into a nested dict:
        {function -> {department -> [use_case_name, ...]}}
    """
    df = pd.read_csv(DATA_PATH)
    taxonomy = {}
    for _, row in df.iterrows():
        func = row["Function"]
        dept = row["Department"]
        uc   = row["Use Case"]
        taxonomy.setdefault(func, {}).setdefault(dept, []).append(uc)
    return taxonomy


@lru_cache(maxsize=1)
def get_use_case_names() -> list:
    """Return a flat sorted list of all use case names."""
    df = pd.read_csv(DATA_PATH)
    return sorted(df["Use Case"].tolist())


@lru_cache(maxsize=1)
def get_use_cases_df() -> pd.DataFrame:
    """Return the full use cases DataFrame."""
    return pd.read_csv(DATA_PATH)


def get_department(use_case: str) -> tuple:
    """Return (Function, Department) for a given use case name."""
    df = get_use_cases_df()
    match = df[df["Use Case"] == use_case]
    if match.empty:
        return (None, None)
    return (match.iloc[0]["Function"], match.iloc[0]["Department"])


def get_use_cases_by_function(function: str) -> list:
    """Return all use cases for a given function."""
    df = get_use_cases_df()
    return df[df["Function"] == function]["Use Case"].tolist()
