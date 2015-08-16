from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from leads.models import Lead, MktoLead

class LeadSerializer(DocumentSerializer):       
    company_id = drfme_serial.IntegerField()
    leads = drfme_serial.DictField()
    activities = drfme_serial.DictField()
    lists = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = Lead
        fields = ('company_id', 'leads', 'activities', 'lists', 'updated_date', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Lead(**attrs)
    
class MktoLeadSerializer(DocumentSerializer):       
    company = drfme_serial.CharField()
    email = drfme_serial.EmailField()
    firstName = drfme_serial.CharField()
    id = drfme_serial.IntegerField()
    lastName = drfme_serial.CharField()
    leadSource = drfme_serial.CharField()
    leadStatus = drfme_serial.CharField()
    
    class Meta:
        model = MktoLead
        fields = ('email', 'firstName', 'lastName', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return MktoLead(**attrs)

