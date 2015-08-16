from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from integrations.models import UserOauth
from company.models import BaseCompanyIntegration, CompanyIntegration, CompanyIntegrationDeleted
        
class UserOauthSerializer(serializers.Serializer):
        
    #id = serializers.CharField()
    user_id = serializers.IntegerField()
    updated_date = serializers.DateTimeField()
    sfdc_access_token = serializers.CharField()
    
    class Meta:
        model = UserOauth
        fields = ('id', 'user_id', 'updated_date', 'sfdc_access_token', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return UserOauth(**attrs)

 
class BaseCompanyIntegrationSerializer(serializers.Serializer):       
    code = serializers.CharField()
    host = serializers.CharField()
    client_id = serializers.CharField()
    client_secret = serializers.CharField()
    access_token= serializers.CharField()
    redirect_uri = serializers.CharField()
    system_type = serializers.CharField()
    
    class Meta:
        model = BaseCompanyIntegration
        fields = ('code', 'host', 'client_id', 'client_secret', 'access_token', 'redirect_uri', 'system_type',)

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return BaseCompanyIntegration(**attrs)
    
class CompanyIntegrationSerializer(DocumentSerializer):       
    #company_code = drfme_serial.IntegerField()
    #integrations = drfme_serial.DictField()
    
    class Meta:
        model = CompanyIntegration

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return CompanyIntegration(**attrs)
    
class CompanyIntegrationDeletedSerializer(DocumentSerializer):       
    #company_code = drfme_serial.IntegerField()
    #integrations = drfme_serial.DictField()
    
    class Meta:
        model = CompanyIntegrationDeleted
        fields = ('company_code', 'integrations',)

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return CompanyIntegrationDeleted(**attrs)

