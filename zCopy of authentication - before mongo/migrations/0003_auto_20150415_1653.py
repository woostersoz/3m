# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_auto_20150415_1647'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='company',
            options={'managed': False},
        ),
    ]
