A Django-based online banking system with user authentication, account management, money transfers, transaction
workflows, real-time notifications, and fraud detection powered by a machine learning model.

## Overview

Kwetu Bank is a full-stack banking web application built with Django. It provides a simple digital banking experience
for customers to:

- register and manage personal accounts
- log in securely and update profile details
- deposit and withdraw funds
- send money to other users
- view dashboard summaries and recent transactions
- receive notifications and alerts
- review fraud-risk signals for transfers

The project also includes a machine learning fraud model and real-time updates using Django Channels and Redis.

## Tech Stack

- Python 3.14+
- Django 6+
- PostgreSQL
- Redis
- Django Channels + Daphne
- HTML, CSS, JavaScript
- scikit-learn, pandas, joblib-based fraud detection pipeline

## Key Features

- Secure account registration and password reset flow
- Profile management with next-of-kin data
- Dashboard with account overview and transaction summaries
- Deposit, withdrawal, and transfer services
- Fraud detection screening before transfers are processed
- Real-time notification center with read/unread tracking
- Admin-friendly project configuration via Django admin and Baton
- Email-based authentication and password reset support
- Docker-based local PostgreSQL and Mailpit setup

## Project Structure

```text
bank_system/
├── accounts/                  # Authentication, profile, password reset logic
├── bank/                     # Banking dashboard, transfers, notifications, ML integration
├── data/                     # Local data and Mailpit persistence
├── dataset and notebook/     # Fraud model assets and notebook
├── ml_training/             # Model training scripts
├── media/                   # Uploaded profile images
├── Online_Banking_System/    # Django project settings and URLs
├── static/                  # CSS, JS, images
├── templates/               # App templates and shared layout
├── docker-compose.yml       # Local Postgres + Mailpit services
├── manage.py                # Django management entrypoint
├── pyproject.toml           # Python dependencies
├── README.md                # Project documentation
└── requirements-like config in pyproject.toml
```

## Prerequisites

Before starting, make sure you have:

- Python 3.14+
- uv installed
- PostgreSQL running locally or via Docker
- Redis running locally or via Docker
- Git

## Local Development Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd bank_system
```

2. Install Python dependencies:

```bash
uv sync
```

3. Create a `.env` file in the project root with the required environment variables. Example:

```env
DEBUG=true
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
POSTGRES_DB=bank
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
DB_CONN_MAX_AGE=60
REDIS_URL=redis://127.0.0.1:6379/0
CHANNEL_REDIS_URL=redis://127.0.0.1:6379/1
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=false
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DJANGO_LOG_LEVEL=INFO
```

4. Start the supporting services:

```bash
docker compose up -d postgres mailpit
```

This starts:

- PostgreSQL on `localhost:5433`
- Mailpit SMTP on `localhost:1025`
- Mailpit web UI on `http://localhost:8025`

> Redis is required for caching and Channels. If you are not already running Redis locally, start it separately or
> uncomment the Redis service in `docker-compose.yml` before running the app.

5. Apply migrations:

```bash
uv run python manage.py migrate
```

6. Start the development server:

```bash
uv run python manage.py runserver
```

Then open:

- http://127.0.0.1:8000/

## Optional: Fraud Model Setup

The project uses a fraud detection model from the `dataset and notebook/models` folder.

If needed, you can retrain or regenerate the model using the scripts and notebook in:

- `ml_training/train_fraud_model.py`
- `dataset and notebook/fraud_detection_ml_pipeline.ipynb`

The model path is configured via `FRAUD_MODEL_SOURCE` in the Django settings, defaulting to the local joblib file stored
in the project.

## Running Tests

Run the test suite with:

```bash
uv run python manage.py test
```

To run a targeted test module:

```bash
uv run python manage.py test bank.tests.test_realtime_notifications
```

## Useful Commands

Create a superuser:

```bash
uv run python manage.py createsuperuser
```

Collect static files for production:

```bash
uv run python manage.py collectstatic --noinput
```

Check project URLs and routes:

```bash
uv run python manage.py check
```

## Environment Notes

- The app uses `EMAIL_HOST` and `EMAIL_PORT` for password reset messages and notifications.
- Mailpit is useful for local development because it captures outbound emails without sending them externally.
- Redis is required for Django cache and the channel layer used by real-time notification features.
- The app is configured for Nairobi time (`Africa/Nairobi`) and uses a custom `Account` model as the user model.

## Production Considerations

This project is configured for local development convenience, not a hardened production deployment. Before deploying to
production, review:

- `SECRET_KEY` management
- secure `DEBUG` settings
- production database credentials and SSL settings
- Redis and cache configuration
- email provider configuration
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- static/media handling and Whitenoise configuration

## License

This project is provided as a learning/demo application. Please check the repository or project owner for any licensing
details.

## Contributing

Contributions are welcome. For a clean workflow:

1. create a feature branch
2. make focused changes
3. run tests
4. open a pull request with a clear summary

## Troubleshooting

### Database connection errors

Verify PostgreSQL is running and ensure the database credentials in `.env` match your local service configuration.

### Redis errors or WebSocket issues

Check whether Redis is available at the URL configured in `REDIS_URL` and `CHANNEL_REDIS_URL`.

### Emails not appearing

Use Mailpit at `http://localhost:8025` to inspect outbound messages during development.

### Missing environment variables

Ensure your `.env` file includes all values expected by `Online_Banking_System/settings.py` before running the app.

---

For development and onboarding, this project is best run with `uv` and Docker to manage the Python environment and local
services cleanly.
