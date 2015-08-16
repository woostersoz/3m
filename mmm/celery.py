from __future__ import absolute_import

import os

from celery import Celery

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mmm.settings')

app = Celery('mmm', backend='amqp', broker='amqp://')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# @app.Task(bind=True)
# def debug_task(self):
#     print('Request: {0!r}'.format(self.request))