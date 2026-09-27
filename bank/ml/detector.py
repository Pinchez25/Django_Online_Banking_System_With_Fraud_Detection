from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings

from .features import TransactionFeatureBuilder


class FraudModelUnavailable(RuntimeError):
    """Raised when the fraud model cannot be loaded or cannot score a transaction."""


@dataclass(frozen=True, slots=True)
class FraudResult:
    probability: float
    threshold: float
    model_version: str
    model_name: str

    @property
    def is_fraud(self) -> bool:
        return self.probability >= self.threshold


@lru_cache(maxsize=1)
def _load_bundle(model_path: str):
    try:
        bundle = joblib.load(Path(model_path))
    except (FileNotFoundError, ImportError, ModuleNotFoundError, OSError, ValueError) as error:
        raise FraudModelUnavailable("The fraud detection model could not be loaded.") from error

    required_keys = {"model", "feature_columns", "fraud_threshold"}
    if not isinstance(bundle, dict) or not required_keys.issubset(bundle):
        raise FraudModelUnavailable("The fraud detection model bundle is invalid.")

    return bundle


class FraudDetector:
    def __init__(self, feature_builder: TransactionFeatureBuilder | None = None):
        self.feature_builder = feature_builder or TransactionFeatureBuilder()
        self.model_path = str(settings.FRAUD_MODEL_PATH)

    def evaluate(self, *, sender, receiver, amount, transaction_date) -> FraudResult:
        bundle = _load_bundle(self.model_path)
        features = self.feature_builder.build(
            sender=sender,
            receiver=receiver,
            amount=amount,
            transaction_date=transaction_date,
        )

        feature_columns = bundle["feature_columns"]
        missing_columns = set(feature_columns) - features.keys()
        if missing_columns:
            raise FraudModelUnavailable(
                f"The fraud model expects missing features: {sorted(missing_columns)}"
            )

        feature_frame = pd.DataFrame(
            [[features[column] for column in feature_columns]],
            columns=feature_columns,
        )

        try:
            probability = float(bundle["model"].predict_proba(feature_frame)[0, 1])
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
            raise FraudModelUnavailable("The fraud detection model could not score the transaction.") from error

        return FraudResult(
            probability=probability,
            threshold=float(bundle["fraud_threshold"]),
            model_version=str(bundle.get("model_version", "unknown")),
            model_name=str(bundle.get("model_name", "unknown")),
        )
