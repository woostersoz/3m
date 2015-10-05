from __future__ import division
import datetime, json
from datetime import timedelta, date, datetime
import pytz
import math
from random import randint, shuffle
from operator import itemgetter, attrgetter
from urllib import quote_plus

from collections import OrderedDict

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from django.core import serializers
#from django.contrib.auth.decorators import login_required

from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer

from rest_framework_mongoengine import generics as drfme_generics

from celery import task
from pickle import NONE
from mongoengine.django.shortcuts import get_document_or_404
from mongoengine.queryset.visitor import Q

from integrations.views import Marketo, Salesforce, Buffer
from social.models import Tweet, CompanyTweetCategory, TweetMasterList, PublishedTweet
from social.serializers import CompanyTweetCategorySerializer, TweetSerializer, TweetMasterListSerializer, BufferProfileSerializer, PublishedTweetSerializer
from authentication.models import Company
from company.models import CompanyIntegration
from superadmin.models import SuperIntegration
from analytics.models import AnalyticsData, AnalyticsIds
from mmm.views import _str_from_date

from bson import ObjectId


class TwitterCategories(viewsets.ModelViewSet):  
    
    serializer_class = CompanyTweetCategorySerializer
    
    def list(self, request, id=None): 
        try:
            company = Company.objects.filter(company_id=id).first()
            categories = CompanyTweetCategory.objects(company=company.id)
            serializedList = CompanyTweetCategorySerializer(categories, many=True)
            return Response(serializedList.data)
        except Exception as e:
            return Response(str(e))
        
        
class TwitterCategory(viewsets.ModelViewSet):  
    
    serializer_class = CompanyTweetCategorySerializer
    
    def delete(self, request, id=None, category_id=None): 
        try:
            company = Company.objects.filter(company_id=id).first()
            tweets = Tweet.objects(Q(company=company.id) & Q(category=category_id)).all()
            print 'twe are ' + str(list(tweets))
            if len(tweets) > 0:
                return HttpResponse("Category has dependent tweets", status=status.HTTP_400_BAD_REQUEST)
            deleted = CompanyTweetCategory.objects(Q(company=company.id) & Q(id=category_id)).delete()
            if deleted == 1:
                return HttpResponse("Category deleted", status=status.HTTP_200_OK)
            else:
                return HttpResponse("Category could not be deleted", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e))
        
    def update(self, request, id=None, category_id=None): 
        try:
            company = Company.objects.filter(company_id=id).first()
            category = CompanyTweetCategory.objects(Q(company=company.id) & Q(id=category_id)).first()
            if category is not None:
                data = json.loads(request.body)
                category.category_name = data.get('category_name', None)
                category.description = data.get('description', None)
                category.weight = data.get('weight', None)
                category.save()
                categories = CompanyTweetCategory.objects(company=company.id)
                serializedList = CompanyTweetCategorySerializer(categories, many=True)
                return Response(serializedList.data)
            else:
                return HttpResponse("Category could not be updated", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e))
        
    def create(self, request, id=None, category_id=None):
        try:
            company = Company.objects.filter(company_id=id).first()
            category = CompanyTweetCategory()
            if category is not None:
                data = json.loads(request.body)
                category.category_name = data.get('category_name', None)
                category.description = data.get('description', None)
                category.weight = data.get('weight', None)
                category.company = company
                category.save()
                categories = CompanyTweetCategory.objects(company=company.id)
                serializedList = CompanyTweetCategorySerializer(categories, many=True)
                return Response(serializedList.data)
            else:
                return HttpResponse("Category could not be created", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e))
        
class Tweets(viewsets.ModelViewSet):  
    
    serializer_class = TweetSerializer
    
    def list(self, request, id=None): 
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        try:
            company = Company.objects.filter(company_id=id).first()
            
            return JsonResponse(_get_tweets_for_company(company, offset, items_per_page))
        except Exception as e:
            return Response(str(e))
        
def _get_tweets_for_company(company, offset, items_per_page):
    tweets = Tweet.objects(company=company.id).skip(offset).limit(items_per_page)
    serializedList = TweetSerializer(tweets, many=True)
    totalCount = Tweet.objects(company=company.id).count()
    firstDate = Tweet.objects(company=company.id).order_by('updated_date').first()
    firstDateCreated = firstDate['updated_date']
    lastDate = Tweet.objects(company=company.id).order_by('-updated_date').first()
    lastDateCreated = lastDate['updated_date']
    return {'results' : serializedList.data, 'totalCount': totalCount, 'firstDateCreated': firstDateCreated, 'lastDateCreated': lastDateCreated}
            
class SingleTweet(viewsets.ModelViewSet):  
    
    serializer_class = TweetSerializer
    
    def delete(self, request, id=None, tweet_id=None): 
        try:
            company = Company.objects.filter(company_id=id).first()
            deleted = Tweet.objects(Q(company=company.id) & Q(id=tweet_id)).delete()
            if deleted == 1:
                return HttpResponse("Tweet deleted", status=status.HTTP_200_OK)
            else:
                return HttpResponse("Tweet  could not be deleted", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e))
        
    def update(self, request, id=None, tweet_id=None): 
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        try:
            company = Company.objects.filter(company_id=id).first()
            tweet = Tweet.objects(Q(company=company.id) & Q(id=tweet_id)).first()
            if tweet is not None:
                data = json.loads(request.body)
                category = data.get('category', None)
                category_id = category['id']
                category = CompanyTweetCategory.objects(Q(company=company.id) & Q(id=category_id)).first()
                tweet.category = category
                tweet.text1 = data.get('text1', None)
                tweet.text2 = data.get('text2', None)
                tweet.text3 = data.get('text3', None)
                tweet.save()
                return JsonResponse(_get_tweets_for_company(company, offset, items_per_page))
            else:
                return HttpResponse("Tweet could not be updated", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e))
        
    def create(self, request, id=None, tweet_id=None):
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        try:
            company = Company.objects.filter(company_id=id).first()
            data = json.loads(request.body)
            category = data.get('category', None)
            category_id = category['id']
            category = CompanyTweetCategory.objects(Q(company=company.id) & Q(id=category_id)).first()
            tweet = Tweet()
            tweet.company = company
            tweet.category = category
            tweet.text1 = data.get('text1', None)
            tweet.text2 = data.get('text2', None)
            tweet.text3 = data.get('text3', None)
            tweet.save()
            return JsonResponse(_get_tweets_for_company(company, offset, items_per_page))
        except Exception as e:
            return Response(str(e))

class TwitterMasterLists(viewsets.ModelViewSet):  
    
    serializer_class = TweetMasterListSerializer
    
    def list(self, request, id=None): 
        try:
            company = Company.objects.filter(company_id=id).first()
            tw_mls = TweetMasterList.objects(company=company.id)
            serializedList = TweetMasterListSerializer(tw_mls, many=True)
            totalCount = TweetMasterList.objects(company=company.id).count()
            numPublished = TweetMasterList.objects(Q(company=company.id) & Q(published=True)).count()
            tw_mls_list = list(tw_mls)
            totalTwCount = 0
            for tw_ml in tw_mls_list:
                totalTwCount+= len(tw_ml.tweets)
            return JsonResponse({'results' : serializedList.data, 'totalCount': totalCount, 'numPublished': numPublished, 'totalTwCount' : totalTwCount})
        except Exception as e:
            return Response(str(e))
                
class SingleTweetMasterList(viewsets.ModelViewSet):  
    
    def _round_down(self, num, divisor):
        return num - (num%divisor)
    
    def create(self, request, id=None, masterlist_id=None):
        try:
            company = Company.objects.filter(company_id=id).first()
            data = json.loads(request.body)
            tweets = data.get('tweets', None)
            buffer_profile_id = data.get('buffer_profile_id', None)
            tw_handle = data.get('tw_handle', None)
            tweetMasterList = TweetMasterList()
            tweetMasterList.company = company
            tweetMasterList.tweets = tweets
            tweetMasterList.buffer_profile_id = buffer_profile_id
            tweetMasterList.tw_handle = tw_handle
            tweetMasterList.save()
            serializedList = TweetMasterListSerializer(tweetMasterList, many=False)
            return Response(serializedList.data)
        except Exception as e:
            return Response(str(e))
    
    def list(self, request, id=None, masterlist_id=None):
        
        def _get_tweets(tweets_by_category, sorted_tweets_by_category):
            for category in sorted_tweets_by_category: # for each category in the list
                tweets = Tweet.objects(Q(company=company.id) & Q(category=category)) # get all the tweets
                tweets_list = list(tweets)
                tweets_by_category[category]['tweets'] = []
                remaining_tweets = tweets_by_category[category]['first_number']
                max_tweets = tweets_by_category[category]['max_number']
                for i in range(remaining_tweets):
                    if max_tweets == 0: # no more tweets left in this category so move to the next one
                        break
                    elif max_tweets == 1:
                        random_index = 0
                    else:
                        random_index = randint(0, max_tweets - 1)
                    random_text_index = randint(1,3) # to pick from one othe three options of the text
                    selected_tweet = tweets_list.pop(random_index)
                    #for j in range(1, 4):
                    fieldname = 'text' + str(random_text_index)
                        #if j != random_text_index:
                            #tweet[fieldname] = ''
                    tweet = {}
                    tweet['tweet_id'] = str(selected_tweet.id)
                    tweet['text'] = selected_tweet[fieldname]
                    tweet['version'] = random_text_index
                    tweet['category_id'] = str(category)
                    tweet['category_name'] = tweets_by_category[category]['name']
                    tweets_by_category[category]['tweets'].append(tweet)
                    remaining_tweets -= 1
                    max_tweets -= 1
            #print str(tweets_by_category)
            return tweets_by_category 
            
        try:
            select_by_category = False
            selected_category = request.GET.get('category', None)
            selected_count = request.GET.get('count', None) #how many tweets from selected category
            if selected_category is not None: #the request is to select tweets of a specific category
                select_by_category = True
             
            company = Company.objects.filter(company_id=id).first()
            categories = CompanyTweetCategory.objects(company=company.id)
            if select_by_category: 
                if selected_category == 'Undefined': #If category is "Undefined", it's the first call so pick a random category
                    random_index = randint(0, len(categories) - 1) #pick a random category
                    print 'rand us ' + str(random_index)
                    categories = CompanyTweetCategory.objects(company=company.id).limit(-1).skip(random_index)
                    print 'categ' + str(categories)
                else:
                    categories = CompanyTweetCategory.objects(Q(company=company.id) & Q(id=ObjectId(selected_category)))
                for category in list(categories):
                    print 'category is ' + str(category)
                    category.weight = 100
            tweets_by_category = {}
            total_weight = 0
            master_list_tweets = {}
            master_list_tweets_number = 20 # change to variable later

            for category in categories:
                total_weight += category.weight
                tweets_by_category[str(category.id)] = {}
                tweets_by_category[str(category.id)]['weight'] = category.weight / 100 #self._round_down(category.weight, 10) / 100 # round down the weight to the nearest 10
                tweets_by_category[str(category.id)]['name'] = category.category_name
                
            if total_weight != 100:
                return HttpResponse("Category weights need to total up to 100", status=status.HTTP_400_BAD_REQUEST) 
            
            possible_tweets = 0 #how many tweets can we get in the first pass thru?
            #first pass based on inputs provided 
            for category in tweets_by_category.keys(): #loop through each category and select the tweets
                if selected_count == 'Undefined' or selected_count is None:
                    tweets_by_category[category]['max_number'] = Tweet.objects(Q(company=company.id) & Q(category=category)).count()
                else:
                    tweets_by_category[category]['max_number'] = int(selected_count)
                print 'got tweets ' + str(tweets_by_category[category]['max_number'])
                tweets_by_category[category]['first_number'] = math.trunc( tweets_by_category[category]['weight'] * tweets_by_category[category]['max_number'] )
                possible_tweets += tweets_by_category[category]['first_number'] 
                print ' for category ' + str(category) + ' we have ' + str(tweets_by_category[category]['first_number'])
                #starting_point = random.randrange(0, )
            
            #first pass is completed - see if we have enough tweets else pick randomly
            print 'total tw ' + str(possible_tweets)
            sorted_tweets_by_category = sorted(tweets_by_category, key=lambda category: tweets_by_category[category]['weight'],  reverse=True)
            if possible_tweets >= master_list_tweets_number or select_by_category: # we have hit our target, so pick the tweets and off we go
                tweets_by_category = _get_tweets(tweets_by_category, sorted_tweets_by_category)
            else: #we have not yet hit the number so backfill
                for category in sorted_tweets_by_category:  
                    this_category_possible = tweets_by_category[category]['max_number'] - tweets_by_category[category]['first_number']
                    possible_tweets += this_category_possible
                    if possible_tweets >= master_list_tweets_number:
                        tweets_by_category[category]['first_number'] += this_category_possible - ( possible_tweets - master_list_tweets_number )# we may have gone above the max so bring back to max
                        print 'final 1 ' + str(tweets_by_category[category]['first_number'])
                        tweets_by_category = _get_tweets(tweets_by_category, sorted_tweets_by_category)
                        break # we are done
                    else:
                        tweets_by_category[category]['first_number'] = tweets_by_category[category]['max_number'] # we havent hit the max yet so just swap the numbers here 
                        print 'final 2 ' + str(tweets_by_category[category]['first_number'])
                if possible_tweets < master_list_tweets_number:
                    return HttpResponse("Insufficient number of tweets", status=status.HTTP_400_BAD_REQUEST)
            
            results = []
            for category in tweets_by_category.keys():
                for obj in tweets_by_category[category]['tweets']:
                    results.append(obj)
            #print ' results ' + str(results)
            
            return Response(results) 
        except Exception as e:
            return Response(str(e))
        
@api_view(['POST'])  
def publishMl(request, id, masterlist_id):
    try:
        company = Company.objects.filter(company_id=id).first()
        ml = TweetMasterList.objects(Q(company=company.id) & Q(id=masterlist_id)).first()
        
        if ml is None:
            return HttpResponse("Could not find the Master List for publishing", status=status.HTTP_400_BAD_REQUEST)
        tweets = ml['tweets']
        shuffle(tweets)
        #buffer_profile_id = '558f150b7409ab382f11a39e' #change to parameter later
        
        existingIntegration = CompanyIntegration.objects(company_id = id ).first()
        if 'bufr' in existingIntegration['integrations']: # if Buffer is present and configured
            client_id = existingIntegration['integrations']['bufr']['client_id']
            client_secret = existingIntegration['integrations']['bufr']['client_secret']
            access_token = existingIntegration['integrations']['bufr']['access_token']
            buffer = Buffer()
            api = Buffer.get_api(buffer, client_id=client_id, client_secret=client_secret, access_token=access_token)
            #profile = Buffer.get_twitter_profile(buffer, api)
            profile = Buffer.get_twitter_profile_by_id(buffer, api, ml.buffer_profile_id)
            #print 'posting to profile ' + profile['id']
            for tweet in tweets:
                try:
                    post = quote_plus(tweet['text'])
                    Buffer.post_to_twitter(buffer, api, post, profile)
                except Exception as e:
                    continue
            TweetMasterList.objects(Q(company=company.id) & Q(id=masterlist_id)).update(published=True)
            TweetMasterList.objects(Q(company=company.id) & Q(id=masterlist_id)).update(published_date=datetime.utcnow())
            return HttpResponse("Tweets posted", status=status.HTTP_200_OK)
        else:
            return HttpResponse("No publishing integration found", status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])  
@renderer_classes((JSONRenderer,))
def get_tw_handles_buffer(request, id):
    try:
        company = Company.objects.filter(company_id=id).first()
        
        existingIntegration = CompanyIntegration.objects(company_id = id ).first()
        if 'bufr' in existingIntegration['integrations']: # if Buffer is present and configured
            client_id = existingIntegration['integrations']['bufr']['client_id']
            client_secret = existingIntegration['integrations']['bufr']['client_secret']
            access_token = existingIntegration['integrations']['bufr']['access_token']
            buffer = Buffer()
            api = Buffer.get_api(buffer, client_id=client_id, client_secret=client_secret, access_token=access_token)
            profiles = Buffer.get_twitter_profiles(buffer, api)
            results = []
            for profile in profiles:
                new_profile = {}
                new_profile['id'] = profile['id']
                new_profile['service'] = profile['service']
                new_profile['service_id'] = profile['service_id']
                new_profile['service_username'] = profile['service_username']
                results.append(new_profile)
            #serializedList = BufferProfileSerializer(profiles, many=True)
            return JsonResponse({'results' :results})
        else:
            return JsonResponse({'error' : 'No integration found with Buffer'})
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def get_tw_category_size(request, id):
    category_id = request.GET.get('category_id', None)
    if category_id is None:
        return JsonResponse({'Error': 'No category provided'})
    company_id = request.user.company_id
    company = Company.objects.filter(company_id=company_id).first()
    category = ObjectId(category_id)
    print 'categ is '+ str(category_id) + ' and company is ' + str(company_id)
    tweetCount = Tweet.objects(Q(company=company.id) & Q(category=category)).count()
    print 'tw count is ' + str(tweetCount)
    return JsonResponse({'category_count': tweetCount})

    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterTwInteractions(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    interaction_type = request.GET.get('interaction_type')
    series_type = request.GET.get('series_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    offset = (page_number - 1) * items_per_page
    
    user_id = request.user.id
    company_id = request.user.company_id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    try:   
        code = None
        if existingIntegration is not None:
            for source in existingIntegration.integrations.keys():
                defined_system_type = SuperIntegration.objects(Q(code = source) & Q(system_type = system_type)).first()
                if defined_system_type is not None:
                    code = source
            #print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'bufr':
            result = filtertwInteractionsBufr(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, interaction_type=interaction_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, chart_name=chart_name)
        else:
            result =  'Nothing to report'
        return result
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
def filtertwInteractionsBufr(user_id, company_id, start_date, end_date, interaction_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name):    
    #print 'start is ' + str(time.time())
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = _str_from_date(local_start_date_naive, "short")
        #local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    #print 'start2 is ' + str(time.time())
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = _str_from_date(local_end_date_naive, "short")
    #print 'start3 is ' + str(time.time()) 
        #local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    #code = _get_code(company_id, system_type)
     
    try:
        interactions = []
        
        company_field_qry = 'company_id'
        chart_name_qry = 'chart_name'
       
        system_type_qry = 'system_type'
        date_qry = 'date'
        querydict = {company_field_qry: company_id, system_type_qry: system_type, date_qry: local_start_date, chart_name_qry: chart_name}
        print 'qd is ' + str(querydict)
        analyticsIds = AnalyticsIds.objects(**querydict).only('results').first()
        #print 'start3 is ' + str(time.time())
        if analyticsIds is None:
            return []
        print 'interaction tupe is ' + interaction_type
        ids = analyticsIds['results'].get(interaction_type, None)
        print 'ids is ' + str(ids)
        publishedTweets = PublishedTweet.objects(interaction_id__in=ids).skip(offset).limit(items_per_page).order_by('published_date') 
        #print 'start5 is ' + str(time.time())
        #now do the calculations
        total = PublishedTweet.objects(interaction_id__in=ids).count() #len(leads)
        #print 'start6 is ' + str(time.time())
        
        serializer = PublishedTweetSerializer(publishedTweets, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
