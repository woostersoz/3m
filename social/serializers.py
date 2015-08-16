from django.contrib.auth import update_session_auth_hash

from rest_framework import serializers
from rest_framework_mongoengine.serializers import serializers as drfme_serial, DocumentSerializer

from social.models import CompanyTweetCategory, Tweet, TweetMasterList, PublishedTweet, FbAdInsight
from buffpy.models.profile import PATHS, Profile
from facebookads.objects import Insights

class CompanyTweetCategorySerializer(DocumentSerializer):       
   
    class Meta:
        model = CompanyTweetCategory
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return CompanyTweetCategory(**attrs)


class TweetSerializer(DocumentSerializer):       
   
    class Meta:
        model = Tweet
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Tweet(**attrs)
    
class TweetInMasterListSerializer(serializers.Serializer):
    tweet_id = drfme_serial.CharField
    version = drfme_serial.IntegerField
    text = drfme_serial.CharField
    
    class Meta:
        fields = ('tweet_id', 'text', 'version', )
    
    
class TweetMasterListSerializer(DocumentSerializer):       
    
    class Meta:
        model = TweetMasterList
        #fields = ('tweets', 'company',  'published', 'published_date', 'updated_date')
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return TweetMasterList(**attrs)
    
class BufferProfileSerializer(serializers.Serializer):
    class Meta:
        model = Profile
        
class PublishedTweetSerializer(DocumentSerializer):       
   
    class Meta:
        model = PublishedTweet
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return PublishedTweet(**attrs)
    
class FbInsightsSerializer(serializers.Serializer):       
   
    class Meta:
        model = Insights
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return Insights(**attrs)
    
class FbAdInsightSerializer(DocumentSerializer):       
    
    class Meta:
        model = FbAdInsight
        #fields = ('tweets', 'company',  'published', 'published_date', 'updated_date')
    
    def restore_object(self, attrs, instance=None):
        if instance is not None:
            for k, v in attrs.iteritems():
                setattr(instance, k, v)
            return instance
        return FbAdInsight(**attrs)   