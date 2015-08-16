from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import DocumentSerializer, EmbeddedDocumentSerializer

from authentication.serializers import AccountSerializer
from integrations.models import UserOauth
        
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

        

        
