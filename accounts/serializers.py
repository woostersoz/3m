from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from accounts.models import SuperAccount, Account

class SuperAccountSerializer(DocumentSerializer):       
   
    names = drfme_serial.ListField(drfme_serial.CharField)
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = SuperAccount
        fields = ('id', 'updated_date', 'names')

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return SuperAccount(**attrs)

#used for counts of leads in accounts
class AccountCountSerializer(serializers.Serializer):       
    _id = drfme_serial.CharField()
    name = drfme_serial.ListField(drfme_serial.CharField)
    #status = drfme_serial.ListField(drfme_serial.CharField())
    count = drfme_serial.IntegerField()
    
    class Meta:
        fields = ('_id', 'count', 'name',  )


class AccountSerializer(DocumentSerializer):       
    
    class Meta:
        model = Account

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Account(**attrs)
