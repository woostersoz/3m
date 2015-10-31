from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer
