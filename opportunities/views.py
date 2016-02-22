import datetime, json, time
from datetime import timedelta, date, datetime
from dateutil import tz
import pytz

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from mongoengine.queryset.visitor import Q
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
from django.utils.timezone import get_current_timezone

from integrations.views import Marketo, Salesforce #, get_sfdc_test

from opportunities.tasks import retrieveSfdcOpportunities
from accounts.models import Account
from accounts.serializers import AccountSerializer
from opportunities.serializers import OpportunitySerializer
from mmm.views import _str_from_date, _date_from_str
from company.models import CompanyIntegration 
from leads.models import Lead
# get leads 

#@api_view(['GET'])
class OpportunitiesViewSet(drfme_generics.ListCreateAPIView):
    
    #serializer_class = ActivitySerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            #print 'no code'
            #queryset = Activity.objects.all()
            pass
            
        return queryset

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveOpportunities(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        company_id = request.user.company_id
        try:
            if code == 'mkto':
                #result = retrieveMktoActivities.delay(user_id=user_id, company_id=company_id)
                pass
            elif code == 'sfdc': 
                result = retrieveSfdcOpportunities.delay(user_id=user_id, company_id=company_id)
            else:
                result =  'Nothing to report'
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveOpportunitiesDaily(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        #company_id = request.user.company_id
        company_id = id
        try:
#             if code == 'mkto':
#                 #result = retrieveMktoActivities.delay(user_id=user_id, company_id=company_id)
#                 pass
#             elif code == 'sfdc': 
#                 result = retrieveSfdcOpportunitiesDaily.delay(user_id=user_id, company_id=company_id)
#             else:
#                 result =  'Nothing to report'
            result = None
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getOpportunities(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        start_date = int(request.GET.get('start_date'))
        end_date = int(request.GET.get('end_date'))
        sub_view = request.GET.get('subview')
        filters = request.GET.get('filters')
        filters = json.loads(filters)
        superfilters = request.GET.get('superfilters')
        super_filters = json.loads(superfilters)
        #print 'super filters are ' + str(super_filters)
        date_field = None
        querydict_filters = {}
        #match_filters = {}
        company_field_qry = 'company_id'
        opp_field_qry = 'opportunities__sfdc__exists'
        subview_field_qry = ''
        original_date_field = ''
        
        projection = {'$project': {'_id': '$opportunities.sfdc.Id', 'created_date': '$opportunities.sfdc.CreatedDate', 'close_date': '$opportunities.sfdc.CloseDate', 'account_name': '$source_name', 'name': '$opportunities.sfdc.Name', 'amount': '$opportunities.sfdc.Amount', 'account_id': '$sfdc_id', 'closed': '$opportunities.sfdc.IsClosed', 'won': '$opportunities.sfdc.IsWon', 'owner_id': '$opportunities.sfdc.OwnerId', 'stage': '$opportunities.sfdc.StageName'  } }
        match = {'$match' : { }}
        
        if super_filters is not None:
            #print 'sf ' + str(super_filters)
            if 'date_types' in super_filters: # need to filter by a certain type of date
                date_field = super_filters['date_types']
                if start_date is not None:
                    utc_day_start_epoch =  datetime.fromtimestamp(float(start_date / 1000))
                    #utc_day_start_epoch = str('{0:f}'.format(utc_day_start_epoch).rstrip('0').rstrip('.'))
                    #print 'utc start epoch is ' + str(utc_day_start_epoch)
       
                    #local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
                #print 'start2 is ' + str(time.time())
                if end_date is not None:
                    utc_day_end_epoch = datetime.fromtimestamp(float(end_date / 1000))
                    #utc_day_end_epoch = str('{0:f}'.format(utc_day_end_epoch).rstrip('0').rstrip('.'))
                    print 'utc end epoch is ' + str(utc_day_end_epoch)
                utc_day_start_string = datetime.strftime(utc_day_start_epoch, '%Y-%m-%dT%H-%M-%S.000+0000')
                utc_day_end_string = datetime.strftime(utc_day_end_epoch, '%Y-%m-%dT%H-%M-%S.000+0000')
                #print 'utc start string is ' + str(utc_day_start_string)
                #print 'utc end string is ' + str(utc_day_end_string)
                #remove the date_types item 
                #super_filters.pop('date_types')
                
        if filters is not None:
            for key, value in filters.items():
                if value is not None and value != '':
                    querydict_filters['opportunities__sfdc__' + key] = value #creates an additional querydict that can be added to the main qd
                    match['$match']['opportunities.sfdc.' + key] = value
        
        
        
        
        if date_field is None: #if there's no date filter
            querydict = {opp_field_qry: True, company_field_qry: company_id}
            querydict.update(querydict_filters)
            opps = Account.objects(**querydict).aggregate({'$unwind': '$opportunities.sfdc'}, match, projection) #, {'$match': {'opportunities.sfdc.Id' : {'$ne': None}}} #
        
        else: #if date filter is used
            if date_field == 'opportunities.sfdc.CloseDate': #change to Last Modified Date because CloseDate in Opp may not be correctly updated by user
                date_field = 'opportunities.sfdc.LastModifiedDate'
            
            original_date_field = date_field
            date_field = date_field.replace('.', '__') # needed to change embedded field format for querydict
            date_field_start_qry = date_field + '__gte'
            date_field_end_qry = date_field + '__lte'
            match['$match'][original_date_field]  = {'$gte': utc_day_start_string, '$lte': utc_day_end_string}
        
            if original_date_field == 'opportunities.sfdc.LastModifiedDate': #if close add, add a filter for 'IsClosed'
                isclosed_field_qry = 'opportunities__sfdc__IsClosed'
                querydict = {company_field_qry: company_id, date_field_start_qry: utc_day_start_string, date_field_end_qry: utc_day_end_string, isclosed_field_qry: True}
                querydict.update(querydict_filters)
                match['$match']['opportunities.sfdc.IsClosed'] = True
                opps = Account.objects(**querydict).aggregate({'$unwind': '$opportunities.sfdc'},  match, projection) #, {'$match': {'opportunities.sfdc.Id' : {'$ne': None}}} #
        
            else:
                querydict = {company_field_qry: company_id, date_field_start_qry: utc_day_start_string, date_field_end_qry: utc_day_end_string}
                querydict.update(querydict_filters)
                opps = Account.objects(**querydict).aggregate({'$unwind': '$opportunities.sfdc'}, match, projection) #, {'$match': {'opportunities.sfdc.Id' : {'$ne': None}}} #
        
        #print 'qd is ' + str(querydict)
        #print 'start time was '  + str(time.time())
        #total =  Account.objects(**querydict).count()
        #print 'start time2 was '  + str(time.time())
        opps_list = list(opps)
        #see if there's a subview
        if sub_view == 'closedbeforecreated': #find Opps that have a Close Date before Created Date
            opps_list[:] = [opp for opp in opps_list if opp['close_date'] < _str_from_date(_date_from_str(opp['created_date']).replace(tzinfo=pytz.utc).astimezone(tz.tzlocal()), 'short')] #compare the short forms of both dates as strings after they Created Date is converted to local times
        elif sub_view == 'nocontact': #find Opps that don't have a contact
            opps2 = Lead.objects(**querydict).aggregate({'$unwind': '$opportunities.sfdc'}, match, projection)
            opps_list2 = list(opps2)
            #print 'opps 2 are ' + str(list(opps2))
            #opps_all = _make_hashable(opps_list)
            #opps_with_contacts = _make_hashable(list(opps2))
            #opps_list = [dict(x) for x in set(opps_all).difference(opps_with_contacts)]
            for opp2 in opps_list2:
                opps_list[:] = [opp for opp in opps_list if opp['_id'] != opp2['_id']]
                                  
        total = len(opps_list)
        opps_list = opps_list[offset:offset + items_per_page]
        #print 'start time3 was '  + str(time.time())
        
        for opp in opps_list:
            opp['multiple_occurences'] = False #needed due to analytical drilldown on Opps
            opp['created_date'] = _str_from_date(_date_from_str(opp['created_date']).replace(tzinfo=pytz.utc).astimezone(tz.tzlocal()), 'short') #convert date to local timezone
            #opp['owner_name'] = _map_sfdc_userid_name(company_id, opp['owner_id'])
        #print 'start time4 was '  + str(time.time())
        opps_list = _map_sfdc_userid_name(company_id, opps_list)
        serializer = OpportunitySerializer(opps_list, many=True)  
        #print 'start time6 was '  + str(time.time()) 
        type = 'opps'
        return JsonResponse({'count' : total, 'results': serializer.data, 'type': type, 'source_system': 'sfdc'})    
    except Exception as e:
        print 'exception while getting all accounts ' + str(e)
        return JsonResponse({'Error' : str(e)})
    
def _make_hashable(d):
    return (frozenset(x.iteritems() for x in d))

def _map_sfdc_userid_name(company_id, input_list):
    users = CompanyIntegration.objects(company_id=company_id).aggregate({'$unwind': '$integrations.sfdc.users.records'},  {'$project': {'_id':'$integrations.sfdc.users.records.Id', 'Fname':'$integrations.sfdc.users.records.FirstName', 'Lname':'$integrations.sfdc.users.records.LastName'}}) #{'$match': {'integrations.sfdc.users.records.Id':opp['owner_id']}}, 
    users = list(users)
    
    for item in input_list:
        for user in users:
            user_found = False
            if user['_id'] == item['owner_id']:
                item['owner_name'] = str(user['Fname']) + ' ' + str(user['Lname'])
                user_found = True
                break
        if not user_found:
            item['owner_name'] = 'Unknown'
            
    return input_list