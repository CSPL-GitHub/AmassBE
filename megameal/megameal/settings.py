from pathlib import Path
import os



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-r%$bwvsi%dfond($50n1y!9_n*&a&s#b5ps=*^i=1fz285*wkk'


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


ALLOWED_HOSTS = ['*']


# Required for excel file handling in core app
HOST = os.environ.get("HOST", default="http://localhost:8001/")


INSTALLED_APPS = [
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'core',
    'useradmin',
    'kiosk',
    'order',
    'koms',
    'woms',
    'realtime',
    'pos',
    'nextjs',
    'inventory',
    'sop',
]


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'megameal.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'static',
            os.path.join(BASE_DIR,'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'megameal.wsgi.application'
ASGI_APPLICATION = 'megameal.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases


DATABASES = {
    # Development
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'megameal_dev',
        'USER': 'root',
        'PASSWORD': 'Root@123',
        'HOST': 'localhost', # 213.210.36.38
        'PORT': '5432',
    }

    # Testing
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': 'megameal_test',
    #     'USER': 'root',
    #     'PASSWORD': 'Root@123',
    #     'HOST': 'localhost', # 213.210.36.38
    #     'PORT': '5432',
    # }

    # Production
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': 'megameal_prod',
    #     'USER': 'root',
    #     'PASSWORD': 'Root@123',
    #     'HOST': 'localhost', # 213.210.36.38
    #     'PORT': '5432',
    # }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'

STATIC_ROOT = os.path.join(BASE_DIR,'static')
STATIC_DIR = os.path.join(BASE_DIR,'static')

STATICFILES_DIRS = ('static/admin-lte/',)


MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


PROJECT_APP = os.path.basename(BASE_DIR)


allowed_origins = [
    "http://0.0.0.1:8001",
]

CORS_ORIGIN_ALLOW = True
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = allowed_origins
CORS_ORIGIN_WHITELIST = allowed_origins
CORS_ALLOWED_ORIGINS = allowed_origins
CSRF_TRUSTED_ORIGINS = allowed_origins


# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587 #587=TLS, 465=SSL
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'kaneki.kenki.1999@gmail.com'
EMAIL_HOST_PASSWORD = 'siwt lgyz vsdj vbcf'


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
