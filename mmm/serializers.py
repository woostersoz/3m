from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from mmm.models import ExportFile

class ExportFilesSerializer(DocumentSerializer):  
    class Meta:
        model = ExportFile
        #fields = ('company_id', 'leads', 'contacts', 'activities', 'lists', 'statuses', 'contacts', 'opportunities', 'updated_date', 'source_first_name', 'source_last_name', 'source_email', 'source_company', 'source_created_date', 'source_status', 'source_stage', 'source_source', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return ExportFile(**attrs)
    
