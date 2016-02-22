from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

#serializes the Opportunity sub-document from within Account/Lead
class OpportunitySerializer(serializers.Serializer):       
    _id = drfme_serial.CharField()
    name = drfme_serial.CharField()
    close_date = drfme_serial.CharField()
    created_date = drfme_serial.CharField()
    amount = drfme_serial.DecimalField(max_digits=10, decimal_places=2)
    account_name = drfme_serial.CharField()
    account_id = drfme_serial.CharField()
    closed = drfme_serial.BooleanField()
    won = drfme_serial.BooleanField()
    owner_id = drfme_serial.CharField()
    owner_name = drfme_serial.CharField()
    stage = drfme_serial.CharField()
    multiple_occurences= drfme_serial.BooleanField()
    
    class Meta:
        fields = ('_id', 'name', 'close_date', 'created_date', 'amount', 'account_name', 'account_id', 'closed', 'won', 'owner_id', 'owner_name', 'stage', 'multiple_occurences' )