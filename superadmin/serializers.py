from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import DocumentSerializer, EmbeddedDocumentSerializer

from superadmin.models import SuperIntegration, SuperAnalytics, SuperJobMonitor, SuperDashboards
from company.serializers import CompanyIntegrationSerializer
        
class SuperIntegrationSerializer(DocumentSerializer):
    
#     name = serializers.CharField()
#     vendor = serializers.CharField()
#     description = serializers.CharField()
#     code = serializers.CharField()
#     system_type = serializers.CharField()
#     company_info = serializers.DictField() #CompanyGenericIntegrationSerializer(read_only=True, required=False)
#     
    class Meta:
        model = SuperIntegration
#         fields = ('id', 'name', 'vendor', 'description', 'code', 'company_info', 'system_type', ) #'

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return SuperIntegration(**attrs)

        
    def get_validation_exclusions(self, *args, **kwargs):
        exclusions = super(SuperIntegrationSerializer, self).get_validation_exclusions()

        return exclusions + ['company_info']
        
        
class SuperAnalyticsSerializer(DocumentSerializer):
    
#     src = serializers.CharField()
#     url = serializers.CharField()
#     title = serializers.CharField()
#     name = serializers.CharField()
#     system_type = serializers.CharField()
#     object = serializers.CharField()
    
    class Meta:
        model = SuperAnalytics
#         fields = ('id', 'src', 'url', 'title', 'name', 'system_type', 'object', ) #'

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return SuperAnalytics(**attrs)
    
class SuperJobMonitorSerializer(DocumentSerializer):
  
    class Meta:
        model = SuperJobMonitor
        fields = ('id', 'company_id', 'started_date', 'ended_date', 'type', 'status', 'tasks', 'comments', ) #'

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return SuperJobMonitor(**attrs)

class SuperDashboardsSerializer(DocumentSerializer):
    
    class Meta:
        model = SuperDashboards

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return SuperDashboards(**attrs)