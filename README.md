# Banking and Fraud Detection Demo

This is an educational Django banking application. It demonstrates account management, deposits, withdrawals, transfers, transaction logging, and an experimental fraud-screening hook. It is not a real banking system and must not process real customer data or money.

## Local Setup

Requirements: Python 3.14+, `uv`, Docker Compose, and a Redis server listening on `127.0.0.1:6379`.

```sh
cp .env.example .env
uv sync --frozen
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py runserver
```

The application runs at `http://127.0.0.1:8000`. Compose starts PostgreSQL only; Django and Redis run on the host. PostgreSQL is bound to `127.0.0.1:5433` by default to avoid colliding with a local PostgreSQL installation. Change `POSTGRES_PORT` in `.env` if that port is already in use. Compose reads the database name and credentials from `.env`.

Run tests with:

```sh
uv run python manage.py test
```

Stop PostgreSQL with `docker compose down`. Its named volume keeps database data between restarts. `docker compose down -v` deletes that data.

`.env` is ignored by Git. `.env.example` contains development-only values; replace the secret and database credentials before using any shared environment. Production must set `DEBUG=false`, a strong `SECRET_KEY`, appropriate `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, secure database credentials, and real email settings. Do not use Django's development server in production.

## Current Fraud Model Limitations

The notebook's dataset contains 10,305 rows and 93 fraud labels. Every sender and receiver card number is unique, and the label rates are low. The notebook uses those card numbers as numeric features, drops transaction time, and applies SMOTE before splitting the resampled data into training and test sets. That leaks synthetic training information into evaluation and makes the reported scores unreliable.

The checked-in `fraud_detection_model.pickle` also cannot be loaded with the project's current scikit-learn version: its saved decision-tree node format is incompatible. A correctly time-ordered 80/20 experiment using SMOTE on training data only produced average precision 0.009 against a 0.0068 fraud prevalence; at a 0.5 threshold, precision was 0.0055 and recall was 0.0714. This is not useful screening performance. Transfers therefore fail closed when the model cannot score them; the app does not silently treat a failed score as a safe transaction.

Before replacing the model, create reproducible synthetic transactions with behavior that can actually predict fraud, such as recent transaction velocity, amount relative to normal account activity, new beneficiaries, device changes, and location changes. Split chronologically before resampling, fit all preprocessing only on training data, compare against a simple baseline, and choose thresholds using precision-recall and the cost of false positives. Persist model version, score, decision, and reason codes with each assessment. Do not use raw card numbers as model features or log full card numbers; use tokenized identifiers and masked display values.

## Improvement Priorities

1. **Complete the ledger model.** Balances are currently mutable account fields. Move toward immutable debit/credit ledger entries, enforce non-negative balances at the database boundary, and make transfer requests idempotent so retries cannot move money twice.
2. **Separate assessment from action.** A fraud score should usually trigger a hold, step-up verification, or review queue with an audit trail. Automatically blocking a customer based on an unvalidated classifier is too aggressive for real use.
3. **Add behavioral context and tests.** Store only necessary, privacy-reviewed signals. Test simultaneous withdrawals/transfers, stale balances, duplicate requests, rollback behavior, and account ownership boundaries.
4. **Harden the application.** Review account recovery, session and CSRF behavior, secret management, upload validation, permissions, database constraints, and retention of sensitive data before exposing it beyond a local demo.
5. **Add background processing only when needed.** The current Django app and in-process Python scorer are a sensible starting point. Kafka is not justified for this single-process demo. If scoring or notifications later need asynchronous retries, begin with a transactional outbox and a worker; introduce a broker only when throughput, independent consumers, or replay requirements justify its operational cost.

The application now keeps each deposit and withdrawal's balance update, transaction row, and audit log in one database transaction; transfers lock both accounts in stable order. Profile views and edits are scoped to the signed-in owner.
