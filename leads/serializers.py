from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from leads.models import Lead

class LeadSerializer(DocumentSerializer):       
#     company_id = drfme_serial.IntegerField()
#     leads = drfme_serial.DictField()
#     activities = drfme_serial.DictField()
#     lists = drfme_serial.DictField()
#     contacts = drfme_serial.DictField()
#     opportunities = drfme_serial.DictField()
#     statuses = drfme_serial.DictField()
#     source_first_name =  drfme_serial.CharField()
#     source_last_name = drfme_serial.CharField()
#     source_email = drfme_serial.CharField()
#     source_company = drfme_serial.CharField()
#     source_created_date = drfme_serial.CharField()
#     source_status = drfme_serial.CharField()
#     source_stage = drfme_serial.CharField()
#     source_source = drfme_serial.CharField()
#     updated_date = drfme_serial.DateTimeField()
#     
    class Meta:
        model = Lead
        #fields = ('company_id', 'leads', 'contacts', 'activities', 'lists', 'statuses', 'contacts', 'opportunities', 'updated_date', 'source_first_name', 'source_last_name', 'source_email', 'source_company', 'source_created_date', 'source_status', 'source_stage', 'source_source', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Lead(**attrs)
    
