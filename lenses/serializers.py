from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer
 
from analytics.models import Snapshot, AnalyticsData, AnalyticsIds, PageTemplate, BinderTemplate, Binder

class SnapshotSerializer(DocumentSerializer): 
    
    class Meta:
        model = Snapshot
        fields = ('company', 'owner', 'updated_date', 'snapshot_html', 'chart_name', 'id' )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Snapshot(**attrs)
    
class AnalyticsDataSerializer(DocumentSerializer): 
    id = drfme_serial.CharField()      
    company_id = drfme_serial.IntegerField()
    chart_name = drfme_serial.CharField()
    system_type = drfme_serial.CharField()
    date = drfme_serial.CharField()
    date_range = drfme_serial.CharField()
    results = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = AnalyticsData
        fields = ('company_id', 'system_type', 'updated_date', 'results', 'chart_name', 'id', 'date', 'date_range', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return AnalyticsData(**attrs)
    
    
class AnalyticsIdsSerializer(DocumentSerializer): 
    id = drfme_serial.CharField()      
    company_id = drfme_serial.IntegerField()
    chart_name = drfme_serial.CharField()
    system_type = drfme_serial.CharField()
    date = drfme_serial.CharField()
    date_range = drfme_serial.CharField()
    results = drfme_serial.DictField()
    updated_date = drfme_serial.DateTimeField()
    
    class Meta:
        model = AnalyticsIds
        fields = ('company_id', 'system_type', 'updated_date', 'results', 'chart_name', 'id', 'date', 'date_range', )

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return AnalyticsIds(**attrs)

class PageTemplateSerializer(DocumentSerializer): 
    class Meta:
        model = PageTemplate
        
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return PageTemplate(**attrs)   
    
class BinderTemplateSerializer(DocumentSerializer): 
    class Meta:
        model = BinderTemplate
        
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return BinderTemplate(**attrs)   
    
class BinderSerializer(DocumentSerializer): 
    class Meta:
        model = Binder
        
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Binder(**attrs)   