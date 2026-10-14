import re
import pandas as pd
from .config import SCHEMA_FIELDS
from .document_loader import normalize_filename


def normalize_for_match(value):
    if pd.isna(value) or value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value).strip()).casefold()
    return value.strip(" ,.")


def evaluate(train_df, predictions_df):

    # Ground truth columns
    truth_cols = ["File Name"] + SCHEMA_FIELDS
    truth = train_df[truth_cols].copy()

    # Prediction columns
    pred_cols = ["File Name"] + SCHEMA_FIELDS
    pred = predictions_df[pred_cols].copy()

    # Normalize filenames
    truth["File Name"] = (
        truth["File Name"]
        .astype(str)
        .str.strip()
    )

    pred["File Name"] = (
        pred["File Name"]
        .astype(str)
        .str.strip()
    )

    # Rename columns
    truth = truth.rename(
        columns={
            field: f"{field}_truth"
            for field in SCHEMA_FIELDS
        }
    )

    pred = pred.rename(
        columns={
            field: f"{field}_pred"
            for field in SCHEMA_FIELDS
        }
    )

    # Merge
    merged_df = pd.merge(
        truth,
        pred,
        on="File Name",
        how="left"
    )

    # Evaluation
    evaluation_results = []

    for field in SCHEMA_FIELDS:

        truth_col = f"{field}_truth"
        pred_col = f"{field}_pred"

        eligible = merged_df[truth_col].notna()

        truth_values = (
            merged_df.loc[eligible, truth_col]
            .astype(str)
            .str.strip()
        )

        pred_values = (
            merged_df.loc[eligible, pred_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        correct = (truth_values == pred_values).sum()

        eligible_count = eligible.sum()

        recall = (
            correct / eligible_count * 100
            if eligible_count > 0
            else 0
        )

        evaluation_results.append({
            "Field": field,
            "Correct": correct,
            "Eligible": eligible_count,
            "Exact-match recall (%)": round(recall, 2)
        })

    evaluation_summary_df = pd.DataFrame(
        evaluation_results
    )

    return evaluation_summary_df, merged_df

def failure_cases(merged):
    tables = {}
    for field in SCHEMA_FIELDS:
        truth_col, pred_col = f"{field}_truth", f"{field}_pred"
        mask = merged[truth_col].notna() & (merged[truth_col].astype(str).str.strip() != merged[pred_col].fillna("").astype(str).str.strip())
        cols = ["File Name_truth", truth_col, pred_col, "Extraction Status"]
        tables[field] = merged.loc[mask, [c for c in cols if c in merged.columns]].copy()
    return tables
