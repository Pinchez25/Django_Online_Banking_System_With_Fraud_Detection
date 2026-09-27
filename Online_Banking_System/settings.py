import os
from pathlib import Path
from datetime import datetime
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"}
SECRET_KEY = os.getenv("SECRET_KEY")


ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

AUTH_USER_MODEL = 'accounts.Account'
LOGIN_URL = reverse_lazy('accounts:login')
INSTALLED_APPS = [
    'baton',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'bank.apps.BankConfig',
    'accounts.apps.AccountsConfig',
    'django_browser_reload',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_user_agents',
    'axes',
    'preventconcurrentlogins',
    'django_extensions',
    'baton.autodiscover',
]
AXES_LOCKOUT_URL = reverse_lazy('account-locked')

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_FAIL_SILENTLY = not DEBUG

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    }
}

USER_AGENTS_CACHE = 'default'

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    'django_user_agents.middleware.UserAgentMiddleware',
    'preventconcurrentlogins.middleware.PreventConcurrentLoginsMiddleware',
    'axes.middleware.AxesMiddleware',

]
# DEFENDER_LOGIN_FAILURE_LIMIT = 3
# DEFENDER_LOCKOUT_URL = '/locked/'
# DEFENDER_REDIS_URL = 'redis://localhost:6379/0'
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# AXES_USE_USER_AGENT = True
ROOT_URLCONF = "Online_Banking_System.urls"

SESSION_EXPIRE_SECONDS = 300
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_TIMEOUT_REDIRECT = reverse_lazy('accounts:login')
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates']
        ,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'accounts.context_processor.authentication_forms',

            ],
        },
    },
]

MAXIMUM_TRANSACTION_AMOUNT = 1000000
MINIMUM_TRANSACTION_AMOUNT = 10

MINIMUM_WITHDRAW_AMOUNT = 10
MAXIMUM_WITHDRAW_AMOUNT = 1000000

MINIMUM_DEPOSIT_AMOUNT = 10

WSGI_APPLICATION = "Online_Banking_System.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        default=f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', '')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'bank')}",
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "60")),
    )
}

LOCAL_MODEL_PATH = (
    BASE_DIR
    / "dataset and notebook"
    / "models"
    / "fraud_detection_pipeline.joblib"
)

FRAUD_MODEL_SOURCE = os.getenv("MODEL_PATH") or LOCAL_MODEL_PATH
FRAUD_ALERT_EMAIL = ""

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", },
]
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-GB"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = False

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ["EMAIL_PORT"])
EMAIL_USE_TLS = os.environ["EMAIL_USE_TLS"].lower() == "true"
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]

BATON = {
    'SITE_HEADER': 'Online Bank',
    'SITE_TITLE': 'Kwetu Bank',
    'INDEX_TITLE': 'Kwetu Bank Administration',
    'COPYRIGHT': f'copyright © {datetime.now().year} <a href="https://www.github.com/Pinchez25">Pinchez</a>',
    'POWERED_BY': '<a href="https://www.github.com/Pinchez25">Peter Thua</a>',
    'SUPPORT_HREF': 'https://www.github.com/Pinchez25'
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static'
]
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = 'media/'
# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

GRAPH_MODELS = {
    'all_applications': True,
    'graph_models': True,
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
