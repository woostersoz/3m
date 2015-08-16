from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from activities.models import Activity

class ActivitySerializer(DocumentSerializer):       
    company_id = drfme_serial.IntegerField()
    lead_id = drfme_serial.CharField()
    activities = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = Activity
        fields = ('company_id', 'lead_id', 'updated_date', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Activity(**attrs)
    
