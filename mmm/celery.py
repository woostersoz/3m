from __future__ import absolute_import

import os
#import django

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mmm.settings')

from django.conf import settings
#django.setup()

app = Celery('mmm', backend='amqp', broker='amqp://')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# @app.Task(bind=True)
# def debug_task(self):
#     print('Request: {0!r}'.format(self.request))