# ruff: noqa: ERA001, E501
"""Base settings to build other settings files upon."""

from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ
import ldap
from django_auth_ldap.config import GroupOfNamesType, LDAPSearch

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# aura/
APPS_DIR = BASE_DIR / "aura"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
# from django.utils.translation import gettext_lazy as _
# LANGUAGES = [
#     ('en', _('English')),
#     ('fr-fr', _('French')),
#     ('pt-br', _('Portuguese')),
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Maximum time in seconds Django can keep the database connections opened.
# Set the value to 0 to disable connection persistence, database connections
# will be closed after each request.
# For Django 4, the default value was changed to 0 as persistent DB connections
# are not supported.
DB_CONN_MAX_AGE = env.int("DB_CONN_MAX_AGE", default=0)
DATABASE_URL = env("DATABASE_URL")
DATABASE_CONNECTION_DEFAULT_NAME = "default"
# TODO: For local envs will be activated in separate PR.
# This variable should be set to `replica`
DATABASE_CONNECTION_REPLICA_NAME = "replica"
DATABASES = {
    DATABASE_CONNECTION_DEFAULT_NAME: dj_database_url.config(
        # default="postgres://{POSTGRES_USER}:aura@localhost:5432/aura",
        conn_max_age=DB_CONN_MAX_AGE,
    ),
    DATABASE_CONNECTION_REPLICA_NAME: dj_database_url.config(
        env="DATABASE_REPLICA_URL",
        # default="postgres://posrgres:aura@localhost:5432/aura",
        # TODO: We need to add read only user to aura,
        # and we need to update docs.
        # default="postgres://aura_read_only:aura@localhost:5432/aura",
        conn_max_age=DB_CONN_MAX_AGE,
        test_options={"MIRROR": DATABASE_CONNECTION_DEFAULT_NAME},
    ),
}
DATABASES[DATABASE_CONNECTION_DEFAULT_NAME]["ATOMIC_REQUESTS"] = True

DATABASE_ROUTERS = ["aura.core.db_routers.PrimaryReplicaRouter"]


# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# channels
ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("aura.localhost", 6379)],
        },
    },
}
# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "recurrence",
    "taggit",
    "channels",
    "import_export",
    "viewflow",
]

LOCAL_APPS = [
    "aura.users",
    "aura.core",
    # Your stuff: custom apps go here
    "aura.mentalhealth",
    "aura.assessments",
    "aura.communication",
    "aura.networking",
    "aura.patientflow",
    "aura.analytics",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "aura.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "aura.users.backend.AuraAuthBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "aura.core.request_middleware.RequestMiddleware",
    "aura.core.performance_middleware.PerformanceMonitoringMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "aura.users.middleware.LDAPSSOMiddleware",
    "aura.users.middleware.UserAuditLogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "aura.core.performance_middleware.DatabaseQueryTrackingMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "aura.users.context_processors.allauth_settings",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
# XXX: set this to True once you have a valid SSL certificate
SESSION_COOKIE_HTTPONLY = False
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
# ref: https://stackoverflow.com/a/19008548/20358555
CSRF_COOKIE_HTTPONLY = False
# CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Yusuf Adel""", "yusufadell.dev@gmail.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# https://cookiecutter-django.readthedocs.io/en/latest/settings.html#other-environment-settings
# Force the `admin` sign in process to go through the `django-allauth` workflow
DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "aura.core.logging_filters.RequestContextFilter",
        },
        "sampling": {
            "()": "aura.core.logging_filters.SamplingFilter",
        },
        "security": {
            "()": "aura.core.logging_filters.SecurityFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(asctime)s %(name)s %(levelname)s %(correlation_id)s "
                "%(user_id)s %(client_ip)s %(method)s %(path)s "
                "%(request_duration)s %(db_queries)s %(memory_percent)s "
                "%(security_event)s %(environment)s %(service_name)s "
                "%(message)s %(pathname)s %(lineno)d"
            ),
        },
        "console": {
            "format": (
                "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] "
                "[%(correlation_id)s] [%(user_id)s@%(client_ip)s] "
                "%(message)s"
            ),
        },
        "security": {
            "format": (
                "[SECURITY] %(asctime)s %(levelname)s %(correlation_id)s "
                "%(user_id)s %(client_ip)s %(threat_type)s %(message)s"
            ),
        },
    },
    "handlers": {
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context", "security"],
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["request_context", "sampling"],
        },
        "security": {
            "class": "aura.core.logging_handlers.StructuredFileHandler",
            "filename": BASE_DIR / "logs" / "security.log",
            "formatter": "security",
            "filters": ["request_context", "security"],
            "maxBytes": 100 * 1024 * 1024,  # 100MB
            "backupCount": 10,
            "level": "WARNING",
        },
        "metrics": {
            "class": "aura.core.logging_handlers.MetricsHandler",
            "level": "INFO",
            "filters": ["request_context"],
        },
        "async_file": {
            "class": "aura.core.logging_handlers.AsyncBufferedHandler",
            "target_handler": {
                "class": "aura.core.logging_handlers.StructuredFileHandler",
                "filename": BASE_DIR / "logs" / "application.log",
                "formatter": "json",
                "maxBytes": 500 * 1024 * 1024,  # 500MB
                "backupCount": 20,
            },
            "buffer_size": 1000,
            "flush_interval": 5.0,
            "filters": ["request_context", "security"],
        },
    },
    "loggers": {
        "root": {
            "level": "INFO",
            "handlers": ["console", "metrics"],
        },
        "django": {
            "level": "INFO",
            "handlers": ["console", "async_file"],
            "propagate": False,
        },
        "django.security": {
            "level": "WARNING",
            "handlers": ["security", "console"],
            "propagate": False,
        },
        "celery": {
            "level": "INFO",
            "handlers": ["console", "async_file"],
            "propagate": False,
        },
        "gunicorn": {
            "level": "INFO",
            "handlers": ["console", "async_file"],
            "propagate": False,
        },
        "aura": {
            "level": "DEBUG",
            "handlers": ["console", "async_file", "metrics"],
            "propagate": False,
        },
        "aura.security": {
            "level": "INFO",
            "handlers": ["security", "console"],
            "propagate": False,
        },
        "aura.performance": {
            "level": "INFO",
            "handlers": ["metrics", "async_file"],
            "propagate": False,
        },
    },
}

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
REDIS_SSL = REDIS_URL.startswith("rediss://")

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
CELERY_RESULT_EXTENDED = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# https://github.com/celery/celery/pull/6122
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 5 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True
# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "email"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_USERNAME_REQUIRED = False
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ADAPTER = "aura.users.adapters.AccountAdapter"
# https://docs.allauth.org/en/latest/account/forms.html
ACCOUNT_FORMS = {"signup": "aura.users.forms.UserSignupForm"}
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_ADAPTER = "aura.users.adapters.SocialAccountAdapter"
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_FORMS = {"signup": "aura.users.forms.UserSocialSignupForm"}

# django-rest-framework
# -------------------------------------------------------------------------------
# django-rest-framework - https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "aura.core.authentication.JWTCookieAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "URL_FIELD_NAME": "url",
    # pagination
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
}

# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
CORS_URLS_REGEX = r"^/api/.*$"

# By Default swagger ui is available only to admin user(s). You can change permission classes to change that
# See more configuration options at https://drf-spectacular.readthedocs.io/en/latest/settings.html#settings
SPECTACULAR_SETTINGS = {
    "TITLE": "AURA API",
    "DESCRIPTION": "Documentation of API endpoints of AURA",
    "VERSION": "2.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SCHEMA_PATH_PREFIX": "/api/",
    "SWAGGER_UI_CONFIG": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "filter": True,
        "defaultModelsExpandDepth": 2,
    },
    "SERVE_INCLUDE_SCHEMA": True,
    "SERVE_PUBLIC": True,
    "SERVE_URLCONF": "config.urls",
}

# Performance Monitoring Configuration
# ------------------------------------------------------------------------------
SLOW_REQUEST_THRESHOLD = env.float("SLOW_REQUEST_THRESHOLD", default=2.0)  # 2 seconds
DB_QUERY_THRESHOLD = env.int("DB_QUERY_THRESHOLD", default=20)  # 20 queries
PERFORMANCE_MONITORING_ENABLED = env.bool(
    "PERFORMANCE_MONITORING_ENABLED", default=True
)

# Logging Environment Configuration
# ------------------------------------------------------------------------------
ENVIRONMENT = env("ENVIRONMENT", default="development")
SERVICE_NAME = env("SERVICE_NAME", default="aura")
VERSION = env("VERSION", default="1.0.0")

# Your stuff...
# ------------------------------------------------------------------------------

# Taggit
TAGGIT_CASE_INSENSITIVE = True

# Analytics Configuration
# ------------------------------------------------------------------------------
ANALYTICS_CONFIG = {
    "primary": "database",  # For development - simple and reliable
    "backends": [
        {
            "name": "database",
            "class": "aura.analytics.backends.database.DatabaseAnalytics",
            "options": {"enable_batching": True, "batch_size": 100, "max_retries": 3},
        }
    ],
    "health_check_interval": 300,  # 5 minutes
    "enable_health_monitoring": True,
    "fail_silently": True,  # Never break application flow
}

# Analytics Alert Configuration
ANALYTICS_ALERT_EMAILS = [email for name, email in ADMINS]
ANALYTICS_ALERT_SMS = []  # Add phone numbers for SMS alerts

# Analytics Data Retention (days)
ANALYTICS_DATA_RETENTION_DAYS = 365


# LDAP Configuration
# ------------------------------------------------------------------------------
# Test LDAP server: https://www.forumsys.com/2022/05/10/online-ldap-test-server/
AUTH_LDAP_SERVER_URI = env("DJANGO_LDAP_SERVER_URI")

AUTH_LDAP_BIND_DN = env("AUTH_LDAP_BIND_DN")
AUTH_LDAP_BIND_PASSWORD = env("DJANGO_LDAP_PASSWORD")
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "ou=users,dc=example,dc=com",
    ldap.SCOPE_SUBTREE,
    "(uid=%(user)s)",
)

# Set up the basic group parameters.
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "ou=groups,dc=example,dc=com",
    ldap.SCOPE_SUBTREE,
    "(objectClass=groupOfNames)",
)
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")

# group restrictions
AUTH_LDAP_REQUIRE_GROUP = "cn=enabled,ou=groups,dc=example,dc=com"
AUTH_LDAP_DENY_GROUP = "cn=disabled,ou=groups,dc=example,dc=com"

# Populate the Django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

# User flags based on group membership
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "cn=active,ou=groups,dc=example,dc=com",
    "is_staff": "cn=staff,ou=groups,dc=example,dc=com",
    "is_superuser": "cn=superuser,ou=groups,dc=example,dc=com",
}

# Use LDAP group membership to calculate group permissions.
AUTH_LDAP_FIND_GROUP_PERMS = True

# Cache distinguished names and group memberships for an hour to minimize
# LDAP traffic.
AUTH_LDAP_CACHE_TIMEOUT = 3600

# REST Custom Authentication
API_TOKEN_USE_AND_UPDATE_HASH_RATE = 0.5
USE_JWT = True
SESSION_LOGIN = False


JWT_AUTH_COOKIE = "aura-jwt"  # "jwt-auth"
JWT_AUTH_REFRESH_COOKIE = None
JWT_AUTH_REFRESH_COOKIE_PATH = "/"
JWT_AUTH_SECURE = False
JWT_AUTH_HTTPONLY = False  # If you want to prevent client-side JavaScript from having access to the cookie
JWT_AUTH_SAMESITE = "Lax"
JWT_AUTH_COOKIE_DOMAIN = None
JWT_AUTH_RETURN_EXPIRATION = True
JWT_AUTH_COOKIE_USE_CSRF = False
JWT_AUTH_COOKIE_ENFORCE_CSRF_ON_UNAUTHENTICATED = False

# set expiration times for JWT tokens
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# RAG
# ------------------------------------------------------------------------------

# Embedding Model Configuration
EMBEDDING_MODEL_DIMENSIONS = env.int("EMBEDDING_MODEL_DIMENSIONS")
EMBED_MODEL_NAME = env("EMBED_MODEL_NAME")
GEMINI_API_KEY = env("GEMINI_API_KEY")
EMBEDDINGS_LOADED = False

# LLama Index Configuration
LLAMA_INDEX_CACHE_DIR = env("LLAMA_INDEX_CACHE_DIR")
LLAMA_GGUFF_MODEL_URL = env("LLAMA_GGUFF_MODEL_URL")
USE_GPU = env.int("USE_GPU")

# Sentry Settings
# settings.py
# import sentry_sdk

# sentry_sdk.init(
#     dsn="https://4c4199f5099472936f54160c0de99544@o1085295.ingest.us.sentry.io/4507687936196608",
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     traces_sample_rate=1.0,
#     # Set profiles_sample_rate to 1.0 to profile 100%
#     # of sampled transactions.
#     # We recommend adjusting this value in production.
#     profiles_sample_rate=1.0,
# )

# Message Configuration
DATA_RETENTION_PERIOD = 365

# IP Address
GEOIP_PATH_MMDB: str | None = BASE_DIR / "geoip" / "test.mmdb"

# Django Import Export # https://django-import-export.readthedocs.io/en/latest/
# ------------------------------------------------------------------------------
from import_export.formats.base_formats import CSV  # noqa: E402
from import_export.formats.base_formats import XLSX  # noqa: E402

# from import_export.formats.base_formats import YAML

IMPORT_EXPORT_USE_TRANSACTIONS = True  # Can be overridden on a Resource class by setting the `use_transactions` class attribute.
IMPORT_EXPORT_IMPORT_PERMISSION_CODE = ["therapist_import_patient"]
IMPORT_EXPORT_CHUNK_SIZE = 100  # Can be overridden on a Resource class by setting the `chunk_size` class attribute.
# IMPORT_EXPORT_FORMATS = [XLSX, CSV, YAML]
IMPORT_FORMATS = [CSV, XLSX]
EXPORT_FORMATS = [CSV]

IMPORT_EXPORT_IMPORT_IGNORE_BLANK_LINES = True  # https://django-import-export.readthedocs.io/en/latest/installation.html#import-export-import-ignore-blank-lines
