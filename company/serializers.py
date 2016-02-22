from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from company.models import BaseCompanyIntegration, CompanyIntegration, CompanyIntegrationDeleted, UserOauth
        
class UserOauthSerializer(serializers.Serializer):
        
    class Meta:
        model = UserOauth
        #fields = ('id', 'user_id', 'updated_date', 'sfdc_access_token', )

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

#     def restore_object(self, attrs, instance=None):
#         if instance is not None:
#             for k, v in attrs.iteritems():
#                 setattr(instance, k, v)
#             return instance
#         return CompanyIntegration(**attrs)

        def update(self, instance, validated_data):
            if instance is not None:
                for k, v in validated_data.iteritems():
                    setattr(instance, k, v)
            instance.save()
            return instance

        def create(self, validated_data):
            return CompanyIntegration.objects.create(**validated_data)
           


    
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

class LeadStatusMappingSerializer(serializers.Serializer):       
    stage = drfme_serial.DictField()
    
    class Meta:
        fields = ('stage' )