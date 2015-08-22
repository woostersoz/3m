from datetime import timedelta, datetime

from django.shortcuts import render
from django.views.generic.base import RedirectView
from django.http import HttpResponse, JsonResponse

from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from pythonmarketo.client import MarketoClient
from salesforce_oauth2 import SalesforceOAuth2
from simple_salesforce import api
from hapi.base import BaseClient
from hapi.nurturing import NurturingClient
from hapi.analytics import AnalyticsClient
from hapi.deals import DealsClient
from hapi.utils import get_auth_url, refresh_access_token
from hubspot.connection import OAuthKey, PortalConnection
from hubspot.contacts import Contact
from hubspot.contacts.lists import get_all_contacts, get_all_contacts_by_last_update
from hubspot.contacts.properties import get_all_properties
from hubspot.connection.exc import HubspotAuthenticationError
from buffpy import AuthService, API
from buffpy.managers.profiles import Profiles
from buffpy.managers.updates import Updates
#Google
import httplib2
import requests, json
from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import OAuth2Credentials
from oauth2client.file import Storage
#Facebook
from facebookads import FacebookSession
from facebookads import FacebookAdsApi
from facebookads.objects import (
    AdUser,
    AdCampaign,
    AdAccount,
    Insights,
    EdgeIterator
)
import facebook
from facepy import GraphAPI
#Twitter
from requests_oauthlib import OAuth1Session
import oauth2 as oauth
import urlparse, urllib

from integrations.models import UserOauth
from company.models import CompanyIntegration
from social.serializers import FbInsightsSerializer

import sys, inspect, json


# Create your views here.

class AuthorizeViewSet(viewsets.ViewSet, APIView):
    renderer_classes(JSONRenderer, )
    
    def list(self, request, id=None):
        #account = CustomUser.objects.filter(id=account_id)
        try:
            #if 0 < len(account):
                
            company_info = { 
            "code" : request.GET.get('code'),
            "host" : request.GET.get('host'),
            "client_id" : request.GET.get('client_id'),
            "client_secret" : request.GET.get('client_secret'),
            "redirect_uri" : request.GET.get('redirect_uri'),
            "company_id" : request.user.get_company(),
            "user_id" : request.user.id,
            "request": request
             }
         
            method_map = { "mkto" : self.setup_mkto, "sfdc": self.setup_sfdc, "hspt": self.setup_hspt, "bufr": self.setup_bufr, "goog": self.setup_goog, "fbok": self.setup_fbok, "twtr": self.setup_twtr }
            result = method_map[company_info['code']](**company_info)
            #print "resultxx is " + str(result)
            return Response(result)

            #else:
                #return Response({'error': "User " + account[0].username + " does not exist"})
        except Exception as e:
            return Response({'error': str(e)})
        
    def setup_mkto(self, **kwargs):
        try:
            error = False
            mkto = Marketo(self.request)
            client = mkto.create_client(kwargs['host'], kwargs['client_id'], kwargs['client_secret'])
            client.authenticate()
            print 'mkto client authenticated'
            if self.saveAccessToken(client.token, kwargs['code'], kwargs['company_id'], None, None, None, None): #and\
                #if self.saveUserOauth(client.token, kwargs['code'], kwargs['user_id']): 
                self.request.session['mkto_access_token'] = client.token
                return "Success: Marketo instance validated with token " + client.token
                #else:
                    #error = True
            else: 
                error = True
            
            if error:   
                return "Error: Marketo instance not validated"
        except Exception as e:
                return Response(str(e))
        
    
    def setup_sfdc(self, **kwargs):
        try:
            sfdc = Salesforce()
            client = sfdc.create_client(kwargs['host'], kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'])
            auth_url = sfdc.get_auth_url(client, state=kwargs['user_id'])
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
            
    def setup_hspt(self, **kwargs):
        try:
            hspt = Hubspot(self.request)
            #client = hspt.create_client(kwargs['host'], kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'])
           
            auth_url = hspt.get_auth_url(kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'], kwargs['user_id'])
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
            
    def setup_bufr(self, **kwargs):
        try:
            bufr = Buffer()
            client = bufr.create_client(kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'])
            auth_url = bufr.get_auth_url(client)
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
            
    def setup_goog(self, **kwargs):
        try:
            goog = Google(kwargs['company_id'])
            goog.create_client(kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'], None, None)
            auth_url = goog.get_auth_url()
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
            
    def setup_fbok(self, **kwargs):
        try:
            fbok = Facebook(kwargs['host'], kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'])
            auth_url = fbok.get_auth_url()
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
            
    def setup_twtr(self, **kwargs):
        try:
            print 'line 1'
            twtr = Twitter(kwargs['host'], kwargs['client_id'], kwargs['client_secret'], kwargs['redirect_uri'])
            print 'line 2'
            auth_url, oauth_token_secret = twtr.get_auth_url()
            kwargs['request'].session['oauth_token_secret'] = oauth_token_secret
            return {'auth_url': auth_url}
        except Exception as e:
                return Response(str(e))
    
    def saveUserOauth(self, access_token, code, user_id):
            #self.request.session[code + '_access_token'] = access_token
            tokenField = code + "_access_token"
            
            existingOauth = UserOauth.objects(user_id = user_id).first()
            if existingOauth is not None:
                existingOauth[tokenField] = access_token
                existingOauth.save()
                return True
            
            userOauth = UserOauth(user_id=user_id)
            UserOauth[tokenField] = access_token
            userOauth.save()
     
    def saveAccessToken(self, access_token, code, company_id, refresh_token, instance_url, token_expiry, token_uri):
        try:
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None:
                existingIntegration.integrations[code]["access_token"] = access_token
                if refresh_token is not None:
                    existingIntegration.integrations[code]["refresh_token"] = refresh_token
                if instance_url is not None:
                    existingIntegration.integrations[code]["host"] = instance_url
                if token_expiry is not None:
                    existingIntegration.integrations[code]["token_expiry"] = token_expiry
                if token_uri is not None:
                    existingIntegration.integrations[code]["token_uri"] = token_uri
                
                existingIntegration.save()
                #print 'at saved with ' + str(access_token)
            else:
                raise Exception("Huh? No existing integration found")
            #self.request.session[code + '_access_token'] = access_token    
            return True
        except Exception as e:
            print 'exception is ' + str(e)
            return False
    
    
    
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def get_sfdc_token(request):
    #print 'starting get sfdc'
    try:
        user_id = request.GET.get('state')
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        sfdcIntegration = existingIntegration.integrations['sfdc']
    
        sfdc = Salesforce()
        client = sfdc.create_client(sfdcIntegration['host'], sfdcIntegration['client_id'], sfdcIntegration['client_secret'], sfdcIntegration['redirect_uri'])
        #print request.GET.get('code')
        response = client.get_token(request.GET.get('code'))
        if response is not None:
            access_token = response['access_token']
            refresh_token = response['refresh_token']
            instance_url = response['instance_url']
            #request.session['sfdc_access_token'] = access_token
            authorizeViewSet = AuthorizeViewSet()
            authorizeViewSet.saveAccessToken(access_token, 'sfdc', company_id, refresh_token, instance_url, None, None)
            #authorizeViewSet.saveUserOauth(access_token, 'sfdc', user_id)
            request.session['sfdc_access_token'] = access_token
            access_token_json = {'sfdc_access_token': 'Success: Salesforce instance validated with token' + access_token}
            #return Response(access_token_json)    
        else:
            access_token_json = {'sfdc_access_token' : 'Error: Could not retrieve'}
        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def get_hspt_token(request):
    #print 'starting get hspt'
    try:
        user_id = request.GET.get('state')
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        hsptIntegration = existingIntegration.integrations['hspt']
    
        access_token = request.GET.get('code')
        refresh_token = request.GET.get('refresh_token')
        #request.session['sfdc_access_token'] = access_token
        authorizeViewSet = AuthorizeViewSet()
        authorizeViewSet.saveAccessToken(access_token, 'hspt', company_id, refresh_token, None, None, None)
        #authorizeViewSet.saveUserOauth(access_token, 'hspt', user_id)
        request.session['hspt_access_token'] = access_token
        access_token_json = {'hspt_access_token': 'Success: Hubspot instance validated with token' + access_token}
        #return Response(access_token_json)    

        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def get_bufr_token(request):
    #print 'starting get sfdc'
    try:
        user_id = request.GET.get('state')
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        bufrIntegration = existingIntegration.integrations['bufr']
    
        bufr = Buffer()
        client = bufr.create_client(bufrIntegration['client_id'], bufrIntegration['client_secret'], bufrIntegration['redirect_uri'])
        #print request.GET.get('code')
        access_token = client.get_access_token(request.GET.get('code'))
        if access_token is not None:
#             access_token = response['access_token']
#             refresh_token = response['refresh_token']
#             instance_url = response['instance_url']
            #request.session['sfdc_access_token'] = access_token
            authorizeViewSet = AuthorizeViewSet()
            authorizeViewSet.saveAccessToken(access_token, 'bufr', company_id, None, None, None, None)
            #authorizeViewSet.saveUserOauth(access_token, 'sfdc', user_id)
            request.session['bufr_access_token'] = access_token
            access_token_json = {'bufr_access_token': 'Success: Buffer instance validated with token' + access_token}
            #return Response(access_token_json)    
        else:
            access_token_json = {'bufr_access_token' : 'Error: Could not retrieve'}
        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        

@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def get_goog_token(request):
    try:
        user_id = request.GET.get('state')
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        googIntegration = existingIntegration.integrations['goog']
    
        goog = Google(company_id)
        goog.create_client(googIntegration['client_id'], googIntegration['client_secret'], googIntegration['redirect_uri'], None, None)
        credentials = goog.flow.step2_exchange(request.GET.get('code'))
        access_token = credentials.access_token
        if credentials.refresh_token:
            refresh_token = credentials.refresh_token
        else:
            refresh_token = None
        print 'refresh token is ' + str(refresh_token)
        token_expiry = credentials.token_expiry
        token_uri = credentials.token_uri
        
        if access_token is not None:
            authorizeViewSet = AuthorizeViewSet()
            authorizeViewSet.saveAccessToken(access_token, 'goog', company_id, refresh_token, None, token_expiry, token_uri)
            #authorizeViewSet.saveUserOauth(access_token, 'sfdc', user_id)
            request.session['goog_access_token'] = access_token
            access_token_json = {'goog_access_token': 'Success: Google instance validated with token' + access_token}
            #return Response(access_token_json)    
            #save Google account and profile information
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            googIntegration = existingIntegration.integrations['goog']
            googIntegration['accounts'] = []
            service = goog.create_service()
            accounts_list = goog.get_accounts(service)
            print 'got back goog accounts ' + str(len(accounts_list.get('items')))
            for account in accounts_list.get('items'): #for each GA account
                try:
                    account_id = account.get('id')
                    account_name = account.get('name')
                    profiles = goog.get_profiles(service, account_id) #find all profiles
                    for profile in profiles.get('items', []): # for each GA profile
                        profile_id = profile.get('id')
                        profile_name = profile.get('name')
                        account_object = {'account_id' : account_id, 'account_name': account_name, 'profile_id': profile_id, 'profile_name': profile_name}
                        googIntegration['accounts'].append(account_object)
                except:
                    raise Exception('Could not retrieve Google profile data')
            #existingIntegration.integrations['goog'] = googIntegration
            existingIntegration.save()
        else:
            access_token_json = {'goog_access_token' : 'Error: Could not retrieve'}
        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        
def get_fbok_token(request):
    try:
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        fbokIntegration = existingIntegration.integrations['fbok']
    
        fbok = Facebook(fbokIntegration['host'], fbokIntegration['client_id'], fbokIntegration['client_secret'], fbokIntegration['redirect_uri'])
        #print request.GET.get('code')
        response = fbok.get_token(request.GET.get('code'))
        if response is not None:
            access_token = response['access_token']
            #request.session['sfdc_access_token'] = access_token
            authorizeViewSet = AuthorizeViewSet()
            authorizeViewSet.saveAccessToken(access_token, 'fbok', company_id, None, None, None, None)
            request.session['fbok_access_token'] = access_token
            access_token_json = {'fbok_access_token': 'Success: Facebook instance validated with token' + access_token}
            #save FB ad accounts
            
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first() #need to do this again since access token has been saved in between
            fbokIntegration = existingIntegration.integrations['fbok']
            fbokIntegration['accounts'] = []
            
            try:
                api = fbok.create_api(company_id)
                me = AdUser(fbid='me', api=api)
                my_accounts = list(me.get_ad_accounts())
                for my_account in my_accounts:
                    entries_list = json.loads(json.dumps(my_account, default=lambda o: o.__dict__))
                    print 'my ad account: ' + str(entries_list)  
                    account_object = {'account_id' : entries_list['_data']['account_id'], 'id': entries_list['_data']['id']}
                    fbokIntegration['accounts'].append(account_object)
            except:
                    raise Exception('Could not retrieve Facebook account  data')
            existingIntegration.save() 
        else:
            access_token_json = {'fbok_access_token' : 'Error: Could not retrieve'}
        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        
def get_twtr_token(request):
    try:
        company_id = request.GET.get('company')  
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        twtrIntegration = existingIntegration.integrations['twtr']
        if twtrIntegration is None: 
            raise Exception('No Twitter integration found')
        twtr = Twitter(twtrIntegration['host'], twtrIntegration['client_id'], twtrIntegration['client_secret'], twtrIntegration['redirect_uri'])
        #print request.GET.get('code')
        response = twtr.get_token(request.GET.get('code'), request.session['oauth_token_secret'], request.GET.get('state'))
        if response is not None:
            access_token = response['oauth_token']
            #request.session['sfdc_access_token'] = access_token
            authorizeViewSet = AuthorizeViewSet()
            authorizeViewSet.saveAccessToken(access_token, 'twtr', company_id, None, None, None, None)
            request.session['twtr_access_token'] = access_token
            access_token_json = {'twtr_access_token': 'Success: Twitter instance validated with token' + access_token}
            #return Response(access_token_json)    
        else:
            access_token_json = {'twtr_access_token' : 'Error: Could not retrieve'}
        return JsonResponse(access_token_json)  
    except Exception as e:
            return JsonResponse({'error': str(e)})
        
# get metadataof objects 
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def get_metadata(request, id):
    
    code = request.GET.get('code')
    object = request.GET.get('object')
    
    if code == 'mkto' and (object != 'lead' and object != 'activity'):
        result = "Sorry, Marketo only provides metadata for Leads and Activities"
        return JsonResponse(result, safe=False)
    
    #company_id = request.user.company_id  
    company_id = id
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    
    if existingIntegration is not None:
        integration = existingIntegration.integrations[code]
        if integration is not None:    
            if code == 'sfdc':
                path = 'sobjects/' + object + '/describe/'
                params = {}
                sfdc = Salesforce()
                client = sfdc.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                #print 'path is ' + str(path)
                metaobject = client.restful(path, params)
                if object == 'lead': # if lead, get lead statuses as well
                    params = {'q': 'SELECT IsConverted, IsDefault, MasterLabel, SortOrder from LeadStatus' }
                    path = 'query/'
                    metadata_status = client.restful(path, params)
                    if metadata_status is not None and metadata_status['done'] == True:
                        if 'records' in metadata_status:
                            metaobject['statuses'] = metadata_status['records']
            elif code == 'mkto':
                mkto = Marketo(company_id)
                if (object == 'activity'):
                    metaobject = mkto.get_activity_types()
                else:
                    metaobject = mkto.describe(object + 's') #because Mkto needs 'leads' and 'campaigns'
            elif code == 'hspt':
                hspt = Hubspot(company_id)
                if (object == 'lead'):
                    metaobject_temp = hspt.get_metadata_lead()
                    metaobject = []
                    if metaobject_temp is not None:
                        for property in metaobject_temp:
                            property = vars(property)['_field_values']
                            property.pop('options', None)
                            #print property
                            metaobject.append(property)
                else:
                    result = "Nothing to report"
                    return JsonResponse(result, safe=False)
            else:
                result = "Nothing to report"
                return JsonResponse(result, safe=False)
        else:
            result = 'Error: No ' + code + ' integration found'
            return JsonResponse(result, safe=False)
    
    existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
    integration = existingIntegration.integrations[code]
    existingDict = existingIntegration.integrations
    if 'metadata' in integration:
        existing_metadata = integration['metadata']
        existing_metadata[object] = metaobject
        integration['metadata'] = existing_metadata
    else:
        integration['metadata'] = {}
        integration['metadata'][object] = metaobject
    existingDict[code] = integration
    #print existingDict[code]
    CompanyIntegration.objects(company_id = company_id ).update(integrations=existingDict)
    
    result = {'describe_' + code + '_' + object  : metaobject}       
    return JsonResponse(result, safe=False)
    
class Marketo:
    
    def __init__(self, company_id):
        self.company_id = company_id
        
    def create_client(self, host, client_id, client_secret):
#        mc = MarketoClient(host='541-KMH-410.mktorest.com', client_id='673bf62a-dc5a-4be9-9588-39691d885df4', client_secret='Xx0oo9w530bfZA47hf7z9eWte4Ik9Inb')
        mc = MarketoClient(host=host, client_id=client_id, client_secret=client_secret)
        # !! Mkto client code changed to remove leading slash for host. Add it back after Django 1.8
        return mc
    
    def get_creds(self):
    
        company_id = self.company_id
        #print 'company is ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        mktoIntegration = existingIntegration.integrations['mkto']
        if mktoIntegration is not None:
            self.host = mktoIntegration['host']
            self.client_id = mktoIntegration['client_id']
            self.client_secret = mktoIntegration['client_secret']
            #print 'host is ' + str(self.client_id) + " //// " +  str(self.client_secret)
        else:
            raise Exception("No integration details for Marketo")
    
    def get_leads(self):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)

            fieldList = None
            names = []
            company_id = self.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['mkto']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for i in range(len(metadata)):
                            names.append(metadata[i]['rest']['name'])
                        
            #fieldList = ', ' .join(names)
            if names:
                return mc.execute(method = 'get_leads', filtr = 'email', values = 'satyarg@yahoo.com', fields=names)
            else:
                raise Exception("Could not retrieve field list for Marketo")

        except Exception as e:
            raise Exception("Could not retrieve leads from Marketo: " + str(e))
        
    def get_leads_by_changes(self, leadIds): #used for cron jobs
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)

            fieldList = None
            names = []
            company_id = self.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['mkto']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for i in range(len(metadata)):
                            names.append(metadata[i]['rest']['name'])
                        
            #fieldList = ', ' .join(names)
            if names:
                return mc.execute(method = 'get_leads', filtr = 'id', values = leadIds, fields=names)
            else:
                raise Exception("Could not retrieve field list for Marketo")

        except Exception as e:
            raise Exception("Could not retrieve leads from Marketo: " + str(e))

    def get_leads_by_listId(self, listId = None):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)

            fieldList = None
            names = []
            company_id = self.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['mkto']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for i in range(len(metadata)):
                            names.append(metadata[i]['rest']['name'])
                        
            #fieldList = ', ' .join(names)
            if names:
                return mc.execute(method = 'get_leads_by_listId', listId = listId, batchSize = None, fields=names)
            else:
                raise Exception("Could not retrieve field list for Marketo")

        except Exception as e:
            raise Exception("Could not retrieve leads by list from Marketo: " + str(e))
        
    def get_campaigns(self):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            return mc.execute(method = 'get_campaigns')
        except Exception as e:
            raise Exception("Could not retrieve campaigns from Marketo: " + str(e))
    
    def get_activity_types(self):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            return mc.execute(method = 'get_activity_types')
        except Exception as e:
            raise Exception("Could not retrieve activity types from Marketo: " + str(e))
            
    def get_lead_activity(self, activityTypeIds, sinceDatetime=datetime.now() - timedelta(days=30)):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            #sinceDatetime=datetime.now() - timedelta(days=365)
            #print 'first date is ' + str(sinceDatetime)
            return mc.execute(method = 'get_lead_activity', activityTypeIds = activityTypeIds, sinceDatetime = sinceDatetime, batchSize = None, listId = None)
        except Exception as e:
            raise Exception("Could not retrieve activities from Marketo: " + str(e))
        
    def get_lead_changes(self, fields, sinceDatetime=datetime.now() - timedelta(days=365)):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            #sinceDatetime=datetime.now() - timedelta(days=365)
            #print 'first date is ' + str(sinceDatetime)
            return mc.execute(method = 'get_lead_changes', fields = fields, sinceDatetime = sinceDatetime, batchSize = None, listId = None)
        except Exception as e:
            raise Exception("Could not retrieve lead changes from Marketo: " + str(e))
    
    def get_lists(self, id = None , name=None, programName=None, workspaceName=None, batchSize = None):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            return mc.execute(method = 'get_lists', id = id, name = name, programName = programName, workspaceName = workspaceName, batchSize = None)
        except Exception as e:
            raise Exception("Could not retrieve lists from Marketo: " + str(e))
    
    
    def describe(self, objName):
        try:
            self.get_creds()
            mc = self.create_client(self.host, self.client_id, self.client_secret)
            return mc.execute(method = 'describe', objName = objName)
        except Exception as e:
            raise Exception("Could not retrieve metadata from Marketo: " + str(e))
        
        
class Salesforce:
    
    def create_client(self, auth_site, client_id, client_secret, redirect_uri, **kwargs):
        sfdc = SalesforceOAuth2(auth_site, client_id, client_secret, redirect_uri, **kwargs)
        return sfdc
    
    def get_auth_url(self, sfdc, state):
        auth_url = sfdc.authorize_url(state=state) #state refers to the user_id that is being sent
        return auth_url
    
    def refresh_token(self, company_id):
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        if existingIntegration is not None: 
            integration = existingIntegration.integrations['sfdc']
            client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], refresh_token=integration['refresh_token'])
            response = client.refresh_token(integration['refresh_token'])
            if response is not None:
                access_token = response.get('access_token')
                refresh_token = response.get('refresh_token')
                instance_url = response.get('instance_url')
                #request.session['sfdc_access_token'] = access_token
                authorizeViewSet = AuthorizeViewSet()
                authorizeViewSet.saveAccessToken(access_token, 'sfdc', company_id, refresh_token, instance_url, None, None)
           
                
        
    def get_leads(self, user_id, company_id):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                #params = {'q': 'SELECT ' + fieldList + ' from Lead' }
                #path = 'query/'
                #client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                #return client.restful(path, params)
                
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Lead'
                #print 'dping query' + str(query)
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve leads from Salesforce: " + str(e))
     
    def get_leads_delta(self, user_id, company_id, sinceDateTime): #used by cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                #params = {'q': 'SELECT ' + fieldList + ' from Lead' }
                #path = 'query/'
                #client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                #return client.restful(path, params)
                
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Lead where CreatedDate > ' + sinceDateTime
                #print 'dping query' + str(query)
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve leads from Salesforce: " + str(e))
        
    def get_accounts(self, user_id, company_id):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'contact' in integration['metadata']:
                        metadata = integration['metadata']['account'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                #params = {'q': 'SELECT ' + fieldList + ' from Lead' }
                #path = 'query/'
                #client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                #return client.restful(path, params)
                
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Account'
                #print 'dping query' + str(query)
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve accounts from Salesforce: " + str(e))
           
    def get_accounts_delta(self, user_id, company_id, sinceDateTime): #used by cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'contact' in integration['metadata']:
                        metadata = integration['metadata']['account'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Account where CreatedDate > ' + sinceDateTime
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve accounts from Salesforce: " + str(e))
        
    def get_contacts(self, user_id, company_id):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'contact' in integration['metadata']:
                        metadata = integration['metadata']['contact'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                #params = {'q': 'SELECT ' + fieldList + ' from Lead' }
                #path = 'query/'
                #client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                #return client.restful(path, params)
                
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Contact'
                #print 'dping query' + str(query)
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve contacts from Salesforce: " + str(e))
           
    def get_contacts_delta(self, user_id, company_id, sinceDateTime): #used by cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'contact' in integration['metadata']:
                        metadata = integration['metadata']['contact'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT ' + fieldList + ' from Contact where CreatedDate > ' + sinceDateTime
                print 'dping query' 
                print sinceDateTime
                return client.query_all(query)
        except Exception as e:
            raise Exception("Could not retrieve contacts from Salesforce: " + str(e))
        
    def get_contacts_for_opportunities(self, user_id, company_id): # because SFDC does not send Contact ID within an Opp
        try:    
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                query = 'SELECT Id, FirstName, LastName, Email, CreatedDate, LeadSource, (SELECT Id,OpportunityId,Opportunity.StageName, Opportunity.Amount, ContactId FROM OpportunityContactRoles) FROM Contact'
                #print 'dping query' + str(query)
                return client.query_all(query)
            else:
                raise ValueError('No integration found for Salesforce')
        except Exception as e:
            raise Exception("Could not retrieve contacts for opportunities from Salesforce: " + str(e))
           
    def get_campaigns(self, user_id, company_id):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'campaign' in integration['metadata']:
                        metadata = integration['metadata']['campaign'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                query = 'SELECT ' + fieldList + ' from Campaign' 
                #path = 'query/'
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve campaigns from Salesforce: " + str(e))
        
    def get_campaigns_delta(self, user_id, company_id, sinceDateTime): # for cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'campaign' in integration['metadata']:
                        metadata = integration['metadata']['campaign'] 
                        for obj in metadata['fields']:
                            names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                query = 'SELECT ' + fieldList + ' from Campaign  where CreatedDate > ' + sinceDateTime 
                #path = 'query/'
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve campaigns from Salesforce: " + str(e))
    
    def get_opportunities(self, user_id, company_id):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'opportunity' in integration['metadata']:
                        metadata = integration['metadata']['opportunity'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                query = 'SELECT ' + fieldList + ' from Opportunity' 
                #path = 'query/'
                #print 'params is ' + str(params)
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve opportunities from Salesforce: " + str(e))
    
    def get_opportunities_delta(self, user_id, company_id, sinceDateTime): # for cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'opportunity' in integration['metadata']:
                        metadata = integration['metadata']['opportunity'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                query = 'SELECT ' + fieldList + ' from Opportunity where CreatedDate > ' + sinceDateTime
                #path = 'query/'
                #print 'params is ' + str(params)
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve opportunities from Salesforce: " + str(e))
    
    def get_opportunities_from_accounts(self, user_id, company_id, account_list):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'opportunity' in integration['metadata']:
                        metadata = integration['metadata']['opportunity'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                query = 'SELECT ' + fieldList + ' from Opportunity where AccountId in ' + account_list 
                #path = 'query/'
                #print 'params is ' + str(params)
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve opportunities from Salesforce: " + str(e))
    
    def get_opportunities_from_accounts_daily(self, user_id, company_id, account_list, sinceDateTime): # for cron job
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'opportunity' in integration['metadata']:
                        metadata = integration['metadata']['opportunity'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                #print fieldList
                #path = 'SELECT Id, IsDeleted, MasterRecordId, LastName, FirstName, Salutation, Name, Title, Company from Lead'
                params = {'q': 'SELECT ' + fieldList + ' from Opportunity where AccountId in ' + account_list + ' AND CreatedDate > ' + sinceDateTime}
                path = 'query/'
                #print 'params is ' + str(params)
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.restful(path, params)
            
        except Exception as e:
            raise Exception("Could not retrieve opportunities from Salesforce: " + str(e))
    
    
    def get_activities_for_lead(self, user_id, company_id, lead_list, sinceDateTime):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'task' in integration['metadata']:
                        metadata = integration['metadata']['task'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                query = 'SELECT (SELECT ' + fieldList + ' from Tasks where CreatedDate > ' + sinceDateTime + ' )  from Lead where Id in ' + lead_list 
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve tasks for leads from Salesforce: " + str(e))
        
    
    def get_activities_for_contact(self, user_id, company_id, contact_list, sinceDateTime):
        try:
            fieldList = None
            names = []
            #company_id = request.user.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['sfdc']
                if 'metadata' in integration:
                    if 'task' in integration['metadata']:
                        metadata = integration['metadata']['task'] 
                        for obj in metadata['fields']:
                            if 'name' in obj:
                                names.append(obj['name'])
            fieldList = ', ' .join(names)
            if fieldList is not None:
                query = 'SELECT (SELECT ' + fieldList + ' from Tasks where CreatedDate > ' + sinceDateTime + ' ) from Contact where Id in ' + contact_list
                client = self.create_client(integration['host'], integration['client_id'], integration['client_secret'], integration['redirect_uri'], auth_token=integration['access_token'])
                return client.query_all(query)
            
        except Exception as e:
            raise Exception("Could not retrieve tasks for contacts from Salesforce: " + str(e))
    #Park the below code for now - use it later when trying to get the auth token, not during authorization
#     def retrieve_auth_token(self): 
#             if request.session.get('sfdc_access_token', False):
#         access_token = request.session.get('sfdc_access_token')
#     else:
#         userOauthInstance = UserOauth.objects(user_id=user_id).first()
#         if userOauthInstance is not None:
#             print "got user"
#             serializedList = UserOauthSerializer(userOauthInstance, many=False)
#             access_token = serializedList.data
#             return Response(serializedList.data)
    
    
class Hubspot:
    
    def __init__(self, company_id):
        self.company_id = company_id
    
    def create_client(self, hub_id, client_id, redirect_uri, **kwargs):
        hspt = BaseClient(hub_id, client_id, redirect_uri, **kwargs)
        return hspt
    
    def get_auth_url(self, client_id, portalId, redirect_uri, state):
        try:
            auth_url = get_auth_url(client_id, portalId, redirect_uri, state=state)
            #print 'url is ' + auth_url
            return auth_url
        except Exception as e:
            raise Exception("Could not retrieve auth url from Hubspot: " + str(e))
        
    def get_creds(self):
    
        company_id = self.company_id
        #print 'company is ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        hsptIntegration = existingIntegration.integrations['hspt']
        if hsptIntegration is not None:
            self.host = hsptIntegration['host']
            self.client_id = hsptIntegration['client_id']
            self.client_secret = hsptIntegration['client_secret']
            self.access_token = hsptIntegration['access_token']
            self.refresh_token = hsptIntegration['refresh_token']
            if self.access_token is None:
                raise Exception("No access token for Hubspot")
            #print 'host is ' + str(self.access_token) 
        else:
            raise Exception("No integration details for Hubspot")
        
    def get_all_contacts(self):
        try:
            self.get_creds()
            authentication_key = OAuthKey(self.access_token)
            
            fieldList = None
            names = ''
            company_id = self.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['hspt']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for i in range(len(metadata)):
                            names = names + '"' + metadata[i]['name'] + '", '
                        #names = ",".join(metadata['name'])
            
            #print 'names are ' + names
            if names:
                names = 'firstname', 'lastname', 'company', 'twitterhandle', 'days_to_close', 'first_conversion_date', 'hs_analytics_source', 'hs_analytics_first_url', 'hs_analytics_source_data_1', 'hs_analytics_source_data_2', 'hs_email_first_click_date', 'hs_analytics_first_visit_timestamp', 'hs_analytics_last_visit_timestamp', 'hs_analytics_last_url', 'hs_analytics_first_referrer', 'hs_analytics_last_referrer', 'lifecyclestage', 'hs_lifecysclestage_lead_date', 'hs_email_open', 'hs_email_click', 'recent_conversion_event_name', 'recent_conversion_date', 'num_conversion_events', 'num_unique_conversion_events', 'hs_lifecyclestage_lead_date', 'hs_lifecyclestage_marketingqualifiedlead_date', 'hs_lifecyclestage_opportunity_date', 'hs_lifecyclestage_customer_date', 'hs_lifecyclestage_subscriber_date', 'hs_lifecyclestage_salesqualifiedlead_date', 'hs_lifecyclestage_evangelist_date', 'hs_lifecyclestage_other_date', 'salesforceleadid','salesforcecontactid', 'salesforceaccountid', 'salesforceopportunitystage', 'leadsource', 'total_revenue', 'first_deal_created_date', 'num_associated_deals', 'recent_deal_amount', 'recent_deal_close_date', 'hs_analytics_first_timestamp', 'hs_analytics_last_timestamp', 
                
                #names = 'firstname', 'lastname', 'company', 'twitterhandle', 'days_to_close', 'first_conversion_date', 'hs_analytics_source', 'hs_analytics_first_url', 'hs_analytics_source_data_1', 'hs_analytics_source_data_2', 'hs_email_first_click_date', 'hs_analytics_first_visit_timestamp', 'hs_analytics_last_url', 'hs_analytics_first_referrer', 'hs_analytics_last_referrer', 'lifecyclestage', 'hs_lifecysclestage_lead_date', 'hs_email_open', 'hs_email_click', 'recent_conversion_event_name', 'recent_conversion_date', 'num_conversion_events', 'num_unique_conversion_events', 'hs_lifecyclestage_lead_date', 'hs_lifecyclestage_marketingqualifiedlead_date', 'hs_lifecyclestage_opportunity_date', 'hs_lifecyclestage_customer_date', 'hs_lifecyclestage_subscriber_date', 'hs_lifecyclestage_salesqualifiedlead_date', 'hs_lifecyclestage_evangelist_date', 'hs_lifecyclestage_other_date', 'salesforceleadid','salesforcecontactid', 'salesforceaccountid', 'salesforceopportunitystage', 'leadsource', 'total_revenue', 'first_deal_created_date', 'num_associated_deals', 'recent_deal_amount', 'recent_deal_close_date', 'hs_analytics_first_timestamp',  
                contactList = []
                with PortalConnection(authentication_key, "3m") as connection:
                    return get_all_contacts(connection, property_names=names)
#                     for contact in contacts: #
#                         #'firstname', 'lastname', 'twitterhandle', 'days_to_close', 'first_conversion_date', 'hs_analytics_source', 'hs_analytics_first_url', 'hs_analytics_source_data_1', 'hs_email_first_click_date', 'hs_analytics_first_visit_timestamp', 'hs_analytics_last_url', 'hs_analytics_first_referrer', 'lifecyclestage', 'hs_lifecysclestage_lead_date', 'hs_email_open', 'hs_email_click',
#                         #'hs_analytics_num_page_views', print contact
#                         contactList.append(contact)
#                         if len(contactList) == 100:
#                             saveHsptLeads(user_id=user_id, company_id=company_id, leadList=contactList, job_id=job_id, run_type=run_type)
#                             contactList = []
#                 
#                 return contactList
            else:
                raise Exception("Could not retrieve field list for Hubspot")
            
        except Exception as e:
            print 'Hubspot exception: ' + str(e)
            raise Exception("Could not retrieve contacts from Hubspot: " + str(e))
        
    def get_recent_contacts(self, sinceDateTime): # use this in stead of get_all_contacts to allow for both Initial and Delta runs. Initial run will have sinceDateTime as None
        try:
            self.get_creds()
            authentication_key = OAuthKey(self.access_token)
            
            fieldList = None
            names = ''
            company_id = self.company_id  
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['hspt']
                if 'metadata' in integration:
                    if 'lead' in integration['metadata']:
                        metadata = integration['metadata']['lead'] 
                        for i in range(len(metadata)):
                            names = names + '"' + metadata[i]['name'] + '", '
                            #names = names + ' ' + metadata[i]['name'] + ', '
                            #names = names[:-1]
            
            #print names
            if names:
                names = 'firstname', 'lastname', 'company', 'twitterhandle', 'days_to_close', 'first_conversion_date', 'hs_analytics_source', 'hs_analytics_first_url', 'hs_analytics_source_data_1', 'hs_analytics_source_data_2', 'hs_email_first_click_date', 'hs_analytics_first_visit_timestamp', 'hs_analytics_last_visit_timestamp', 'hs_analytics_last_url', 'hs_analytics_first_referrer', 'hs_analytics_last_referrer', 'lifecyclestage', 'hs_lifecysclestage_lead_date', 'hs_email_open', 'hs_email_click', 'recent_conversion_event_name', 'recent_conversion_date', 'num_conversion_events', 'num_unique_conversion_events', 'hs_lifecyclestage_lead_date', 'hs_lifecyclestage_marketingqualifiedlead_date', 'hs_lifecyclestage_opportunity_date', 'hs_lifecyclestage_customer_date', 'hs_lifecyclestage_subscriber_date', 'hs_lifecyclestage_salesqualifiedlead_date', 'hs_lifecyclestage_evangelist_date', 'hs_lifecyclestage_other_date', 'salesforceleadid','salesforcecontactid', 'salesforceaccountid', 'salesforceopportunitystage', 'leadsource', 'total_revenue', 'first_deal_created_date', 'num_associated_deals', 'recent_deal_amount', 'recent_deal_close_date', 'hs_analytics_first_timestamp', 'hs_analytics_last_timestamp', 
                contactList = []
                with PortalConnection(authentication_key, "3m") as connection:
                    for contact in get_all_contacts_by_last_update(connection, property_names=names, cutoff_datetime=sinceDateTime):
                        #'firstname', 'lastname', 'twitterhandle', 'days_to_close', 'first_conversion_date', 'hs_analytics_source', 'hs_analytics_first_url', 'hs_analytics_source_data_1', 'hs_email_first_click_date', 'hs_analytics_first_visit_timestamp', 'hs_analytics_last_url', 'hs_analytics_first_referrer', 'lifecyclestage', 'hs_lifecysclestage_lead_date', 'hs_email_open', 'hs_email_click',
                        #'hs_analytics_num_page_views', print contact
                        contactList.append(contact)
                return contactList
            else:
                raise Exception("Could not retrieve field list for Hubspot")
            
        except Exception as e:
            raise Exception("Could not retrieve contacts from Hubspot: " + str(e))
        
    def get_traffic(self):
        try:
            self.get_creds()
            params = {}
            params['access_token'] = self.access_token
            #print 'at is ' + self.access_token
#             hspt = NurturingClient(access_token = self.access_token)
#             return hspt.get_campaigns(params = params)
            hspt = AnalyticsClient(access_token = self.access_token)
            return hspt.get_sources(params = params)
            
        except Exception as e:
            raise Exception("Could not retrieve sources analytics from Hubspot: " + str(e))
        
    def get_detailed_traffic(self, channel=None, fromTimestamp=None, toTimestamp=None):
        try:
            if channel is None or fromTimestamp is None or toTimestamp is None:
                return
            
            self.get_creds()
            params = {}
            params['access_token'] = self.access_token
            params['start'] = fromTimestamp
            params['end'] = toTimestamp
            #print 'at is ' + self.access_token
#             hspt = NurturingClient(access_token = self.access_token)
#             return hspt.get_campaigns(params = params)
            hspt = AnalyticsClient(access_token = self.access_token)
            if channel == 'social':
                return hspt.get_social_breakdown(params = params)
            else:
                return None
            
        except Exception as e:
            raise Exception("Could not retrieve drilldown sources analytics from Hubspot: " + str(e))
    
    def get_campaigns(self):
        try:
            self.get_creds()
            params = {}
            params['access_token'] = self.access_token
            print 'at is ' + self.access_token
            hspt = NurturingClient(access_token = self.access_token)
            return hspt.get_all_campaigns(params = params)
            
        except Exception as e:
            raise Exception("Could not retrieve campaigns from Hubspot: " + str(e))
    
    def get_deals(self):
        try:
            self.get_creds()
            params = {}
            params['access_token'] = self.access_token
            #print 'at is ' + self.access_token
#             hspt = NurturingClient(access_token = self.access_token)
#             return hspt.get_campaigns(params = params)
            hspt = DealsClient(access_token = self.access_token)
            return hspt.get_recent_deals_created(params = params)
            
        except Exception as e:
            raise Exception("Could not retrieve deals from Hubspot: " + str(e))
        
        
    def get_metadata_lead(self):
        try:
            self.get_creds()
            #print 'getting at ' +  str(self.access_token)
            authentication_key = OAuthKey(self.access_token)
            propertyList = []
            connection = PortalConnection(authentication_key, "3m")
            #print str(connection.api_calls[0])
            with connection:
                #print 'getting props'
                for propertyx in get_all_properties(connection):
                    propertyList.append(propertyx)
            
            return propertyList
        except Exception as e:
            #print 'type of exception is ' + str(type(e))
            if isinstance(e, HubspotAuthenticationError):
                #print 'authentication error with access' + str(self.access_token)
                #connection._session.close()# close the existing connection else all sorts of issues
                return self.refresh_auth_token()
            else:
                raise Exception("Could not retrieve contacts metadata from Hubspot: " + str(e))  
        
    def refresh_auth_token(self): #arg1 is a placeholder if the caller has a parameter when being called 
        try:
            result = json.loads(refresh_access_token(self.refresh_token, self.client_id)) 
            #print 'ac' + str((result))
            access_token = result.get('access_token')
            refresh_token = result.get('refresh_token')
            #print 'setting at ' +  str(access_token)
            authorizeViewSet = AuthorizeViewSet()
            #print 'company is ' + str(self.company_id)
            authorizeViewSet.saveAccessToken(access_token, 'hspt', self.company_id, refresh_token, None, None, None)
            method_map = { "get_all_contacts" : self.get_all_contacts, "get_campaigns": self.get_campaigns, "get_metadata_lead": self.get_metadata_lead,}
            return method_map[inspect.stack()[1][3]]()   
            #authorizeViewSet.saveUserOauth(access_token, 'hspt', user_id)
            #self.request.session['hspt_access_token'] = access_token
            #print 'called from ' + inspect.stack()[1][3] + ' wtih arg ' + str(arg1)
            #getattr(sys.modules[__name__], inspect.stack()[1][3])(self, arg1)
        except Exception as e:
            raise Exception("Could not refresh access token from Hubspot: " + str(e))  
        
class Buffer:
    
    def create_client(self, client_id, client_secret, redirect_uri, **kwargs):
        service = AuthService(client_id, client_secret, redirect_uri)
        return service
    
    def get_auth_url(self, client):
        try:
            auth_url = client.authorize_url
            return auth_url
        except Exception as e:
            raise Exception("Could not retrieve auth url from Buffer: " + str(e))
    
    def get_api(self, client_id, client_secret, access_token):
        return API(client_id=client_id, client_secret=client_secret, access_token=access_token)
    
    def get_twitter_profile(self, api):
        return Profiles(api=api).filter(service='twitter')[0]
    
    def get_twitter_profile_by_id(self, api, id):
        return Profiles(api=api).filter(id=id)[0]
    
    def get_twitter_profiles(self, api):
        return Profiles(api=api).filter(service='twitter')
         
    def post_to_twitter(self, api, post, profile):
        profile.updates.new(post)
        
    def get_twitter_updates(self, profile):
        return profile.updates.sent
        
class Google:
    
    def __init__(self, company_id):
        self.company_id = company_id
        
    def create_client(self, client_id, client_secret, redirect_uri, token_uri, token_expiry, **kwargs):
        self.flow = OAuth2WebServerFlow(client_id,
                             client_secret,
                             'https://www.googleapis.com/auth/analytics',
                             redirect_uri=redirect_uri)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_uri = token_uri
        self.token_expiry = token_expiry
        
    
    def get_auth_url(self):
        try:
            return self.flow.step1_get_authorize_url()
        except Exception as e:
            raise Exception("Could not retrieve auth url from Google: " + str(e))
        
    def create_service(self): 
        existingIntegration = CompanyIntegration.objects(company_id = self.company_id ).first()
        googIntegration = existingIntegration.integrations['goog']
        if googIntegration is None:
            return None
        self.refresh_token = googIntegration.get('refresh_token', None)
        if self.refresh_token is None:
            raise ValueError('No refresh token for Google')
            return None
        self.client_id = googIntegration.get('client_id', None)
        self.client_secret = googIntegration.get('client_secret', None)
        self.redirect_uri = googIntegration.get('redirect_uri', None)
        self.token_uri = googIntegration.get('token_uri', None)
        self.token_expiry = googIntegration.get('token_expiry', None)
        self.access_token = googIntegration.get('access_token', None)
        
        credentials = OAuth2Credentials(self.access_token, self.client_id, self.client_secret, self.refresh_token, self.token_expiry, self.token_uri, None) #, None, None, None
        service = None
        if credentials is not None:
            http = httplib2.Http()
            http = credentials.authorize(http)
            service = build('analytics', 'v3', http=http)
                
        return service
    
    def get_accounts(self, service):
        return service.management().accounts().list().execute()
    
    def get_profiles(self, service, account_id):
        return service.management().profiles().list(accountId=account_id, webPropertyId='~all').execute()
    
    def get_metrics(self, service, ids, start_date, end_date, metrics, dimensions, sort):
        print 'ids are ' + ids
        print 'metrics are ' + str(metrics)
        print 'dimensions are ' + str(dimensions)
        print 'sort are ' + str(sort)
        api_query = service.data().ga().get(
                                            ids = ids, #'ga:104801618'
                                            start_date = start_date, #'2015-06-01'
                                            end_date = end_date, #'2015-07-31'
                                            metrics = metrics, #'ga:pageviews, ga:timeOnPage',
                                            dimensions = dimensions, #'ga:date, ga:hour, ga:minute, ga:month, ga:pageTitle, ga:pagePath, ga:source',
                                            sort = sort, #'ga:date, ga:source, ga:timeOnPage',
                                            )
        try:
            results = api_query.execute()
            return results
        except Exception as e:
            print 'exception is ' + str(e)
            raise Exception("Could not retrieve data from Google: " + str(e))
        
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def goog_test(request):
    user_id = request.GET.get('state')
    company_id = request.GET.get('company')  
    metrics = 'ga:pageviews, ga:timeOnPage'
    dimensions = 'ga:date, ga:hour, ga:minute, ga:month, ga:pageTitle, ga:pagePath, ga:source'
    sort = 'ga:date, ga:source, ga:timeOnPage'
    ids = 'ga:104801618'
    start_date = '2015-06-01'
    end_date = '2015-07-31'
    goog = Google(company_id) #googIntegration['client_id'], googIntegration['client_secret'], googIntegration['redirect_uri'], googIntegration['token_uri'], googIntegration['token_expiry']
    service = goog.create_service()
    return JsonResponse({'results': goog.get_metrics(service, ids, start_date, end_date, metrics, dimensions, sort)})

class Facebook:
     
    def __init__(self, host, client_id, client_secret, redirect_uri, **kwargs):
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
    def get_auth_url(self):
        try:
            return self.host + '?' + 'client_id=' + self.client_id + '&redirect_uri=' + self.redirect_uri + '&scope=ads_read,manage_pages,read_insights'
        except Exception as e:
            raise Exception("Could not retrieve auth url from Facebook: " + str(e))
        
    def get_token(self, code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code,
            #'scope': 'manage_pages,ads_read'
        }
        url = 'https://graph.facebook.com/v2.4/oauth/access_token'
        s = requests.Session()
        response = s.get(url, params=data)
        response_json = response.json()
        
        if 'access_token' in response_json:
            self.access_token = response_json['access_token']
        return response_json
    
    def create_session(self, company_id):
        try:
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None: 
                integration = existingIntegration.integrations['fbok']
                if integration['access_token'] is not None:
                    session = FacebookSession(
                               self.client_id,
                               self.client_secret,
                               integration['access_token']
                            )
                else:
                    raise Exception("Facebook access token not found ")
                return session
            raise Exception("Facebook integration not found ")
        except Exception as e:
            raise Exception("Could not create Facebook session: " + str(e))
        
    def create_api(self, company_id):
        try:
            api = FacebookAdsApi(self.create_session(company_id))
            #FacebookAdsApi.init(self.client_id, self.client_secret, access_token)
            return api
        except Exception as e:
            raise Exception("Could not create Facebook API: " + str(e))
        
    #@api_view(['GET'])
    #@renderer_classes((JSONRenderer,))        
    def get_adaccount_stats(self, company_id, run_type):
        
        api = self.create_api(company_id)
        FacebookAdsApi.set_default_api(api)
        ### Setup user and read the object from the server
        me = AdUser(fbid='me', api=api)
    
        ### Get first account connected to the user
        my_account = me.get_ad_account()
    
        ### Read connections (in this case, the accounts connected to me)
    
        # Pro tip: Use list(me.get_ad_accounts()) to make a list out of
        # all the elements out of the iterator
    
        my_accounts = list(me.get_ad_accounts())
        
        if run_type == 'initial':
            preset = Insights.Preset.last_3_months
        else:
            preset = Insights.Preset.last_7_days
            
        params = {'date_preset': preset, 'time_increment': 1}
    
        accounts = []
        for account in my_accounts:
                account_object = {}
                account_object['id'] = account[AdAccount.Field.id]
                #account_object['name'] = account[AdAccount.Field.name]
                account_object['insights'] = []
                #insights = [insight for insight in EdgeIterator(campaign.get_insights(params=params), Insights)]
                insights = list(account.get_insights(params=params))
                #print 'got insights ' + str(insights)
                for insight in insights:
                    entries_list = json.loads(json.dumps(insight, default=lambda o: o.__dict__))
                    entries_list = {'data' : entries_list['_data']}
                    print 'entries list is ' + str(entries_list)
                    account_object['insights'].append(entries_list)
                accounts.append(account_object)
            
        return accounts

    #@api_view(['GET'])
    #@renderer_classes((JSONRenderer,))        
    def get_campaign_stats(self, company_id, run_type):
        
        api = self.create_api(company_id)
        FacebookAdsApi.set_default_api(api)
        ### Setup user and read the object from the server
        me = AdUser(fbid='me', api=api)
    
        ### Get first account connected to the user
        my_account = me.get_ad_account()
    
        ### Read connections (in this case, the accounts connected to me)
    
        # Pro tip: Use list(me.get_ad_accounts()) to make a list out of
        # all the elements out of the iterator
    
        my_accounts = list(me.get_ad_accounts())
        
        if run_type == 'initial':
            preset = Insights.Preset.last_3_months
        else:
            preset = Insights.Preset.last_7_days
            
        params = {'date_preset': preset, 'time_increment': 1}
    
        campaigns = []
        for my_account in my_accounts:
            for campaign in my_account.get_ad_campaigns(fields=[AdCampaign.Field.name]):
                campaign_object = {}
                campaign_object['id'] = campaign[AdCampaign.Field.id]
                campaign_object['name'] = campaign[AdCampaign.Field.name]
                campaign_object['account_id'] = my_account[AdAccount.Field.account_id]
                campaign_object['insights'] = []
                #insights = [insight for insight in EdgeIterator(campaign.get_insights(params=params), Insights)]
                insights = list(campaign.get_insights(params=params))
                #print 'got insights ' + str(insights)
                for insight in insights:
                    entries_list = json.loads(json.dumps(insight, default=lambda o: o.__dict__))
                    entries_list = {'data' : entries_list['_data']}
                    print 'entries list is ' + str(entries_list)
                    campaign_object['insights'].append(entries_list) 
                print 'saving acmpaign with id ' + str(campaign[AdCampaign.Field.id])
                campaigns.append(campaign_object)
            
        return campaigns
    #         for stat in campaign.get_insights(params=params):
    #             print(campaign[campaign.Field.name])
    #             for statfield in stat:
    #                 print("\t%s:\t\t%s" % (statfield, stat[statfield]))

class FacebookPage:
    
    def __init__(self, access_token):
        self.access_token = access_token
        
    def create_graph(self):   
        return facebook.GraphAPI(access_token=self.access_token) #, version='2.4'
        
    def get_user(self):
        graph = self.create_graph()
        graph.get_object(id='me')
            
    def get_pages(self):
        #graph = self.create_graph()
        #graph.get_object(id='me/accounts')
        data = {
            'access_token': self.access_token
        }
        url = 'https://graph.facebook.com/v2.4/me/accounts'
        s = requests.Session()
        response = s.get(url, params=data)
        response_json = response.json()
        return response_json
    
    def get_page_insights(self, page_id, page_token, sinceTimestamp, untilTimestamp):
        data = {
            'access_token': page_token,
            'since': sinceTimestamp,
            'until': untilTimestamp,
            'period' : 'day'
                }
        url = 'https://graph.facebook.com/v2.4/' + page_id + '/insights'
        s = requests.Session()
        response = s.get(url, params=data)
        response_json = response.json()
        return response_json
    
    def get_posts(self, page_id, page_token):
#         data = {
#             'access_token': page_token
#         }
#         url = 'https://graph.facebook.com/' + str(page_id) + '/posts'
#         s = requests.Session()
#         response = s.get(url, params=data)
#         response_json = response.json()
#         return response_json

          graph = GraphAPI(page_token)
          posts = graph.get(page_id + '/posts')
          print '# posts ' + str(len(posts))
          #print 'posts retrieved are ' + str(posts)
          return posts
    
    def get_post_insights(self, post_id, page_token):
        data = {
            'access_token': page_token
                }
        url = 'https://graph.facebook.com/v2.4/' + post_id + '/insights'
        s = requests.Session()
        response = s.get(url, params=data)
        response_json = response.json()
        return response_json
      
class Twitter:
     
    def __init__(self, host, client_id, client_secret, redirect_uri, **kwargs):
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.request_token_url = 'https://api.twitter.com/oauth/request_token'
        self.access_token_url = 'https://api.twitter.com/oauth/access_token'
        
    def get_auth_url(self):
        try:
            consumer = oauth.Consumer(self.client_id, self.client_secret)    
            client = oauth.Client(consumer)
            resp, content = client.request(self.request_token_url, "POST", body=urllib.urlencode({'oauth_callback':self.redirect_uri}))
            if resp['status'] != '200':
                raise Exception('Invalid response %s.' % resp['status'])
            request_token = dict(urlparse.parse_qsl(content))
            print 'rt is ' + str(request_token)
            print 'token is ' + str(oauth.Token.from_string(content))
            
            return '%s?%s&oauth_callback=%s' % (self.host, oauth.Token.from_string(content), self.redirect_uri), request_token['oauth_token_secret'] #request_token['oauth_token']
        except Exception as e:
            print 'exception is ' + str(e)
            raise Exception("Could not retrieve auth url from Twitter: " + str(e))
        
    def get_token(self, oauth_token, oauth_token_secret, oauth_verifier):
        try:
            print 'verifier is ' + str(oauth_verifier)
            consumer = oauth.Consumer(self.client_id, self.client_secret)   
            token = oauth.Token(oauth_token, oauth_token_secret) 
            client = oauth.Client(consumer, token)
            print 'created client ' + str(client)
            resp, content = client.request(self.access_token_url, "POST", body=urllib.urlencode({'oauth_callback':self.redirect_uri, 'oauth_verifier': oauth_verifier}))
            if resp['status'] != '200':
                raise Exception('Invalid response %s.' % resp['status'])
            access_token = dict(urlparse.parse_qsl(content))
            return access_token
        except Exception as e:
            print 'exception is ' + str(e)
            raise Exception("Could not retrieve access token from Twitter: " + str(e))