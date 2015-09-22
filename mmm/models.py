from __future__ import unicode_literals
from django.db import models
from django.dispatch import receiver

from mongoengine import *
from mongoengine import signals
import datetime
from bson import json_util
import json


# Create your models here.


class ExportFile(Document):

    company_id = IntField()
    owner_id = ObjectIdField()
    file_name = StringField()
    source = StringField()
    source_type = StringField()
    file = FileField()
    type = StringField()
    updated_date = DateTimeField(default=datetime.datetime.utcnow)

    meta = {'collection': 'exportFile', 'indexes': ['company_id', 'type', 'owner_id', 'source_type'], 
                'ordering':['-updated_date']}

