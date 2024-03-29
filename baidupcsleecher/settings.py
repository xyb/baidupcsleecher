"""
Django settings for baidupcsleecher project.

Generated by 'django-admin startproject' using Django 4.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""
from os import getenv
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-#!3cy4zxd!l60is$niy6byal#5(h^59v6-tu92y7covgo9rmb4",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(getenv("DJANGO_DEBUG", 1)))

if getenv("DJANGO_ALLOWED_HOSTS"):
    ALLOWED_HOSTS = getenv("DJANGO_ALLOWED_HOSTS").split(",")
else:
    ALLOWED_HOSTS = ["*"]

if getenv("CORS_ALLOWED_ORIGINS"):
    CORS_ALLOWED_ORIGINS = getenv("CORS_ALLOWED_ORIGINS").split(",")
elif getenv("CORS_ALLOW_ALL_ORIGINS"):
    CORS_ALLOW_ALL_ORIGINS = True

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "rest_framework",
    "django_htmx",
    "task",
    "ui",
]
if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")

# baidupcsleecher settings
DATA_DIR = Path(getenv("DATA_DIR", "/tmp/baidupcsleecher")).resolve()
REMOTE_LEECHER_DIR = str(Path(getenv("REMOTE_LEECHER_DIR", "/leecher")).resolve())
RUNNER_SLEEP_SECONDS = int(getenv("RUNNER_SLEEP_SECONDS", "5"))
SAMPLE_SIZE = int(getenv("SAMPLE_SIZE", "10240"))
FULL_DOWNLOAD_IMMEDIATELY = bool(int(getenv("FULL_DOWNLOAD_IMMEDIATELY", 0)))
RETRY_TIMES_LIMIT = int(getenv("RETRY_TIMES_LIMIT", 5))
# shared link transfer policy: always, if_not_present
TRANSFER_POLICY = getenv("TRANSFER_POLICY", "if_not_present")
PAN_BAIDU_BDUSS = getenv("PAN_BAIDU_BDUSS", "")
PAN_BAIDU_COOKIES = getenv("PAN_BAIDU_COOKIES", "")
# do not download these path
IGNORE_PATH_RE = getenv("IGNORE_PATH_RE", ".*__MACOSX.*|.*spam.*")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "drf_link_header_pagination.LinkHeaderPagination",
    "PAGE_SIZE": int(getenv("API_PAGE_SIZE", "20")),
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]
if DEBUG:
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "baidupcsleecher.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "debug": DEBUG,
        },
    },
]

WSGI_APPLICATION = "baidupcsleecher.wsgi.application"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
}


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": getenv("DB_USER", "postgres"),
        "PASSWORD": getenv("DB_PASSWORD", ""),
        "HOST": getenv("DB_HOST", ""),
        "PORT": getenv("DB_PORT", ""),
    },
}
if "mysql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"]["OPTIONS"] = {
        # fix mysql error 1452
        "init_command": "SET foreign_key_checks = 0;",
        # fix mysql emoji issue
        "charset": "utf8mb4",
    }


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = getenv("DJANGO_STATIC_URL", "static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
