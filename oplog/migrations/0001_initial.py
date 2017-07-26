# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OpLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.CharField(max_length=64)),
                ('op', models.CharField(max_length=16)),
                ('app', models.CharField(max_length=32)),
                ('app_version', models.CharField(max_length=128)),
                ('time', models.DateTimeField()),
                ('message', models.CharField(max_length=512)),
            ],
        ),
    ]
