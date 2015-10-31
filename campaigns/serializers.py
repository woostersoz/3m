from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from campaigns.models import Campaign

class CampaignSerializer(DocumentSerializer):       
    company_id = drfme_serial.IntegerField()
    campaigns = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = Campaign

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Campaign(**attrs)
    
