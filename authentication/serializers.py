from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer


from authentication.models import CustomUser, Company


class CustomUserSerializer(DocumentSerializer):
    password = drfme_serial.CharField(allow_blank=True, write_only=True)
    confirm_password = drfme_serial.CharField(allow_blank=True, write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'created_at', 'updated_at',
                  'first_name', 'last_name', 'password', 'confirm_password', 'company', 'timezone', 'is_admin', 'is_superadmin',  )
        #read_only_fields = ('created_at', 'updated_at',)

        def create(self, validated_data):
            return CustomUser.objects.create(**validated_data)
        
        def restore_object(self, attrs, instance=None):
            if instance is not None:
                for k, v in attrs.iteritems():
                    setattr(instance, k, v)
                return instance
            confirm_pw = attrs.get('confirm_password')
            del attrs['confirm_password']
            customUser = CustomUser(**attrs)
            customUser.confirm_password = confirm_pw
            #customUser.company = customUser.company.company_id # hack to return only the company ID instead of entire object
            return CustomUser(**attrs)

        def update(self, instance, validated_data):
            instance.username = validated_data.get('username', instance.username)
            #instance.tagline = validated_data.get('tagline', instance.tagline)
            instance.timezone = validated_data.get('timezone', instance.timezone)

            instance.save()

            password = validated_data.get('password', None)
            confirm_password = validated_data.get('confirm_password', None)

            if password and confirm_password and password == confirm_password:
                instance.set_password(password)
                instance.save()

            update_session_auth_hash(self.context.get('request'), instance)

            return instance
        
        
        
class CompanySerializer(DocumentSerializer):
    
    class Meta:
        
        model = Company
        
        def restore_object(self, attrs, instance=None):
            if instance is not None:
                for k, v in attrs.iteritems():
                    setattr(instance, k, v)
                return instance
            return Company(**attrs)