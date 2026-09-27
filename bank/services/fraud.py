from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from bank.ml.detector import FraudDetector, FraudResult


@dataclass(frozen=True, slots=True)
class FraudAssessment:
    result: FraudResult
    assessed_at: object


class FraudService:
    def __init__(self, detector: FraudDetector | None = None):
        self.detector = detector or FraudDetector()

    def assess_transfer(self, *, sender, receiver, amount) -> FraudAssessment:
        assessed_at = timezone.now()
        result = self.detector.evaluate(
            sender=sender,
            receiver=receiver,
            amount=amount,
            transaction_date=assessed_at,
        )
        return FraudAssessment(result=result, assessed_at=assessed_at)
