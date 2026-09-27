"""Train the fraud model used by the Django integration.

Usage:
    python train_fraud_model.py --data bank_transactions.csv --output models/fraud_detection_pipeline.joblib

The sender/receiver identifiers are used only as grouping keys to construct
historical behavioural features. They are NOT model input columns.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score

RANDOM_STATE = 42
MODEL_VERSION = "2.0.0"
FEATURE_COLUMNS = [
    "transaction_amount",
    "transaction_hour",
    "transaction_day_of_week",
    "is_weekend",
    "sender_transaction_count",
    "receiver_transaction_count",
    "sender_average_amount",
    "receiver_average_amount",
    "sender_unique_receivers",
    "receiver_unique_senders",
    "amount_vs_sender_average",
    "amount_vs_receiver_average",
]


def new_history_state():
    return {
        "sender_count": {},
        "receiver_count": {},
        "sender_amount_sum": {},
        "receiver_amount_sum": {},
        "sender_receivers": {},
        "receiver_senders": {},
    }


def copy_history_state(state):
    return {
        "sender_count": dict(state["sender_count"]),
        "receiver_count": dict(state["receiver_count"]),
        "sender_amount_sum": dict(state["sender_amount_sum"]),
        "receiver_amount_sum": dict(state["receiver_amount_sum"]),
        "sender_receivers": {key: set(value) for key, value in state["sender_receivers"].items()},
        "receiver_senders": {key: set(value) for key, value in state["receiver_senders"].items()},
    }


def transform_with_history(transactions, history_state=None, update_history=True):
    state = history_state if history_state is not None else new_history_state()
    feature_rows = []

    for row in transactions.sort_values("transaction_date").itertuples(index=False):
        sender = row.sender_card_number
        receiver = row.receiver_cc_number
        amount = float(row.transaction_amount)

        sender_count = state["sender_count"].get(sender, 0)
        receiver_count = state["receiver_count"].get(receiver, 0)
        sender_average = state["sender_amount_sum"].get(sender, 0.0) / sender_count if sender_count else 0.0
        receiver_average = state["receiver_amount_sum"].get(receiver, 0.0) / receiver_count if receiver_count else 0.0

        feature_rows.append({
            "transaction_amount": amount,
            "transaction_hour": row.transaction_hour,
            "transaction_day_of_week": row.transaction_day_of_week,
            "is_weekend": row.is_weekend,
            "sender_transaction_count": sender_count,
            "receiver_transaction_count": receiver_count,
            "sender_average_amount": sender_average,
            "receiver_average_amount": receiver_average,
            "sender_unique_receivers": len(state["sender_receivers"].get(sender, set())),
            "receiver_unique_senders": len(state["receiver_senders"].get(receiver, set())),
            "amount_vs_sender_average": amount / sender_average if sender_average > 0 else 0.0,
            "amount_vs_receiver_average": amount / receiver_average if receiver_average > 0 else 0.0,
        })

        if update_history:
            state["sender_count"][sender] = sender_count + 1
            state["receiver_count"][receiver] = receiver_count + 1
            state["sender_amount_sum"][sender] = state["sender_amount_sum"].get(sender, 0.0) + amount
            state["receiver_amount_sum"][receiver] = state["receiver_amount_sum"].get(receiver, 0.0) + amount
            state["sender_receivers"].setdefault(sender, set()).add(receiver)
            state["receiver_senders"].setdefault(receiver, set()).add(sender)

    return pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS), state


def metrics(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    return {
        "precision": precision_score(y_true, predictions, zero_division=0),
        "recall": recall_score(y_true, predictions, zero_division=0),
        "f1": f1_score(y_true, predictions, zero_division=0),
        "pr_auc": average_precision_score(y_true, probabilities),
        "roc_auc": roc_auc_score(y_true, probabilities),
    }


def make_class_weighted_model():
    return RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def make_smote_model():
    return ImbPipeline([
        ("smote", SMOTE(random_state=RANDOM_STATE)),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])


def main(data_path: Path, output_path: Path):
    df = pd.read_csv(data_path)
    required = {"sender_card_number", "receiver_cc_number", "transaction_amount", "transaction_date", "is_fraud"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    if df["transaction_date"].isna().any():
        raise ValueError("Some transaction_date values could not be parsed.")
    df = df.sort_values("transaction_date").reset_index(drop=True)
    df["transaction_hour"] = df["transaction_date"].dt.hour
    df["transaction_day_of_week"] = df["transaction_date"].dt.dayofweek
    df["is_weekend"] = (df["transaction_day_of_week"] >= 5).astype(int)

    n = len(df)
    train_end = int(n * 0.60)
    validation_end = int(n * 0.80)
    train_df = df.iloc[:train_end].copy()
    validation_df = df.iloc[train_end:validation_end].copy()
    test_df = df.iloc[validation_end:].copy()

    train_features, history = transform_with_history(train_df)
    validation_features, history = transform_with_history(validation_df, copy_history_state(history))
    test_history = copy_history_state(history)
    test_features, _ = transform_with_history(test_df, test_history, update_history=False)

    y_train = train_df["is_fraud"].to_numpy()
    y_validation = validation_df["is_fraud"].to_numpy()
    y_test = test_df["is_fraud"].to_numpy()

    candidates = [
        ("Class-weighted Random Forest", make_class_weighted_model()),
        ("Random Forest + SMOTE", make_smote_model()),
    ]
    scored = []
    for name, model in candidates:
        model.fit(train_features, y_train)
        probabilities = model.predict_proba(validation_features)[:, 1]
        scored.append((name, model, probabilities, metrics(y_validation, probabilities, 0.5)))

    candidate_name, _, candidate_probabilities, candidate_metrics = max(
        scored, key=lambda item: item[3]["pr_auc"]
    )

    threshold_table = []
    for threshold in np.linspace(0.05, 0.95, 91):
        threshold_table.append({
            "threshold": float(threshold),
            **metrics(y_validation, candidate_probabilities, float(threshold)),
        })
    best = max(threshold_table, key=lambda row: row["f1"])
    best_threshold = float(best["threshold"])

    development_df = pd.concat([train_df, validation_df], ignore_index=True)
    development_features, _ = transform_with_history(development_df)
    final_model = make_smote_model() if candidate_name == "Random Forest + SMOTE" else make_class_weighted_model()
    final_model.fit(development_features, np.concatenate([y_train, y_validation]))
    test_probabilities = final_model.predict_proba(test_features)[:, 1]
    test_metrics = metrics(y_test, test_probabilities, best_threshold)

    bundle = {
        "model": final_model,
        "feature_columns": FEATURE_COLUMNS,
        "fraud_threshold": best_threshold,
        "model_name": candidate_name,
        "model_version": MODEL_VERSION,
        "random_state": RANDOM_STATE,
        "feature_contract_version": "1",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_path)

    print(f"Candidate: {candidate_name}")
    print(f"Validation threshold: {best_threshold:.3f}")
    print("Untouched test metrics:")
    for key, value in test_metrics.items():
        print(f"  {key}: {value:.4f}")
    print(f"Saved: {output_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("bank_transactions.csv"))
    parser.add_argument("--output", type=Path, default=Path("models/fraud_detection_pipeline.joblib"))
    args = parser.parse_args()
    main(args.data, args.output)
