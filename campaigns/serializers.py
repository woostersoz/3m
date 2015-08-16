from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from campaigns.models import Campaign, MktoCampaign

class CampaignSerializer(DocumentSerializer):       
    company_id = drfme_serial.IntegerField()
    campaigns = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = Campaign
        fields = ('company_id', 'campaigns', 'updated_date', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Campaign(**attrs)
    
class MktoCampaignSerializer(DocumentSerializer):       
    active = drfme_serial.CharField()
    createdAt = drfme_serial.DateTimeField()
    id = drfme_serial.IntegerField()
    name = drfme_serial.CharField()
    programName =  drfme_serial.CharField()
    type =  drfme_serial.CharField()
    updatedAt = drfme_serial.DateTimeField()
    workspaceName = drfme_serial.CharField()
    
    class Meta:
        model = MktoCampaign
        fields = ('company_code', 'campaigns', 'updated_date', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return MktoCampaign(**attrs)

