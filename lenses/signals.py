from __future__ import absolute_import, unicode_literals

from django.conf import settings
from kombu import BrokerConnection
from kombu.common import maybe_declare
from kombu.pools import producers

#from .models import BacktestResult
from .queues import notifications_exchange, notifications_queue 


def send_notification(notification):
    #print 'recd note'
    with BrokerConnection(settings.AMQP_URL) as connection:
        with producers[connection].acquire(block=True) as producer:
            maybe_declare(notifications_exchange, producer.channel)
            producer.publish(
                notification,
                exchange='notifications',
                routing_key='notifications',
                declare=[notifications_queue]
            )





