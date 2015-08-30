"""
Django settings for 3m project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
from __future__ import absolute_import
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.conf.global_settings import EMAIL_USE_SSL, EMAIL_BACKEND,\
    EMAIL_SUBJECT_PREFIX
#from mmm.views import TimezoneMiddleware

# from django.conf.global_settings import STATIC_ROOT, STATICFILES_DIRS,\
#     SERVER_EMAIL
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

#celery and rabbitmq settings 
import djcelery
djcelery.setup_loader()

AMQP_URL = "amqp://guest:guest@localhost//"
BROKER_URL = "amqp://guest:guest@localhost:5672//" #don't delete - used by notifications
CELERY_IMPORTS = ("leads.tasks", "campaigns.tasks", "activities.tasks",)
#CELERY_RESULT_BACKEND = 'amqp'
CELERY_RESULT_PERSISTENT = True
CELERY_SEND_TASK_ERROR_EMAILS = True
#CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERY_RESULT_BACKEND='djcelery.backends.cache:CacheBackend'
CELERY_SEND_EVENTS = True

#AMQP_URL = 'amqp://guest:guest@localhost:5672//'

ADMINS = (("Satya Krishnaswamy", "satya@claritix.io"),) #("RG Subramanyan", "rg@claritix.io"),
SERVER_EMAIL = "admin@claritix.io"
EMAIL_HOST = 'smtp.office365.com'
EMAIL_HOST_USER = 'satya@claritix.io'
EMAIL_HOST_PASSWORD = 'Sudha123!'
EMAIL_PORT = '587'
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_SUBJECT_PREFIX = '[Claritix] '

#mongodb settings

from mongoengine import *
connect(db='3m')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'r6avvk+)vw78#ye!%f@g)*3*ao=7ivfp1-178(5b=j(_gs+%&d'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'mongoengine.django.mongo_auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
#    'haystack',
    'mmm',
    'django_extensions',
    'crispy_forms',
    'socketio_runserver',
    'djangular',
    'djcelery',
    'rest_framework',
    'rest_framework_mongoengine',
    'rest_framework_swagger',
    'compressor',
    'mongonaut',
    'authentication',
    'campaigns',
    'integrations',
    'leads',
    'collab',
    'company',
    'superadmin',
    'analytics',
    'activities',
    'contacts',
    'opportunities',
    'accounts',
    'social',
    'dashboards',
    'websites'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'mmm.views.TimezoneMiddleware',
)

# TEMPLATE_CONTEXT_PROCESSORS = (
#      'django.contrib.auth.context_processors.auth',
#      'mmm.context_processors.extra_context',
#       'django.contrib.messages.context_processors.messages',       
#      )
# TEMPLATE_CONTEXT_PROCESSORS = (
#    'django.contrib.auth.context_processors.auth',
#    'django.template.context_processors.debug', #changed from core to template
#    'django.template.context_processors.i18n', #changed from core to template
#    'django.template.context_processors.media', #changed from core to template
#    'django.template.context_processors.static', #changed from core to template
#    'django.template.context_processors.tz', #changed from core to template
#    'django.contrib.collab.context_processors.collab',
# #    'social.apps.django_app.context_processors.backends',
# #    'social.apps.django_app.context_processors.login_redirect',
# )

AUTHENTICATION_BACKENDS = (
#    'social.backends.facebook.FacebookOAuth2',
#    'social.backends.google.GoogleOAuth2',
#    'social.backends.twitter.TwitterOAuth',
     #'django.contrib.auth.backends.ModelBackend',
     'mongoengine.django.auth.MongoEngineBackend',
)

ROOT_URLCONF = 'mmm.urls'

WSGI_APPLICATION = 'mmm.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': '3m',
#         'USER': 'satya',
#         'PASSWORD': 'sudha123',
#         'HOST': '127.0.0.1',
        'ENGINE': 'django.db.backends.dummy'
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True

#LOGIN_URL = '/login'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = 'staticfiles'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

COMPRESS_ENABLED = os.environ.get('COMPRESS_ENABLED', False)

#TEMPLATE_DIRS = (os.path.join(BASE_DIR, 'templates'), os.path.join(os.path.join(BASE_DIR, 'static'), 'templates'), )
#os.path.join(BASE_DIR, 'templates'), 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
            #[os.path.join(BASE_DIR, 'templates')],
            os.path.join(BASE_DIR, 'templates'), os.path.join(os.path.join(BASE_DIR, 'static'), 'templates'), os.path.join(os.path.join(BASE_DIR, STATIC_ROOT), 'templates') 
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                #'django.contrib.collab.context_processors.collab',
                'django.contrib.messages.context_processors.messages'
            ],
        },
    },
]

LOGIN_REDIRECT_URL = '/thirdauth'

SOCIAL_AUTH_FACEBOOK_KEY = '1407487046231082'
SOCIAL_AUTH_FACEBOOK_SECRET = '418b62930f13486a3201d107849a5ae7'

SOCIAL_AUTH_TWITTER_KEY = 'q0TCPrHaJtL4xhtF3UQwY2BUI'
SOCIAL_AUTH_TWITTER_SECRET = 'rXAGnErm3Gpgfji0UxAx6DdW0o5y9YXzTx6Ki5K3qnQfW4B2nY'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DATETIME_FORMAT': None
}
#AUTH_USER_MODEL = 'authentication.Account'
AUTH_USER_MODEL = ('mongo_auth.MongoUser')
MONGOENGINE_USER_DOCUMENT = 'authentication.models.CustomUser' #'mongoengine.django.auth.User
SESSION_ENGINE = 'mongoengine.django.sessions'

#remove the below for Production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# HAYSTACK_CONNECTIONS = {
#     'default': {
#         'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
#         'URL': 'http://127.0.0.1:8983/solr'
#         # ...or for multicore...
#         # 'URL': 'http://127.0.0.1:8983/solr/mysite',
#     },
# }

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # daily cron job at midnight
    'daily-job': {
        'task': 'superadmin.tasks.dailyCronJob',
        'schedule': crontab(minute='*/2') #(hour='00', minute='05') 
                  },
                       }

BASE_URL = 'http://localhost:8000'

#MONGONAUT_JQUERY = os.path.join(BASE_DIR, 'static') + '/theme/assets/global/plugins/jquery.min.js' 
#MONGONAUT_TWITTER_BOOTSTRAP = os.path.join(BASE_DIR, 'static') + '/theme/assets/global/plugins/bootstrap/css/bootstrap.min.css'

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': True,
#     'formatters': {
#         'verbose': {
#             'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'NOTSET',
#             'class': 'logging.StreamHandler',
#             'formatter': 'verbose'
#         }
#     },
#     'loggers': {
#         '': {
#             'handlers': ['console'],
#             'level': 'NOTSET',
#         },
#         'django.request': {
#             'handlers': ['console'],
#             'propagate': False,
#             'level': 'ERROR'
#         }
#     }
# }