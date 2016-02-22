import datetime, json, time
from datetime import timedelta, date, datetime
import pytz

from collections import OrderedDict
from operator import itemgetter, attrgetter, methodcaller

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

from integrations.views import Marketo, Salesforce #, get_sfdc_test
from accounts.serializers import AccountCountSerializer, AccountSerializer
from accounts.models import Account
from leads.models import Lead
from mmm.views import matchingAlgo, _str_from_date, _date_from_str


@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAccountsAndCounts(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        #total = Lead.objects.filter(company_id=company_id).count()
        
        #queryset = Lead.objects(company_id=company_id).item_frequencies('source_company') #.skip(offset).limit(items_per_page)
        queryset =  Lead.objects(company_id=company_id).aggregate( { '$group': { '_id': '$source_company', 'count': { '$sum': 1 }, 'name' : { '$push': { '$concat': [ {'$ifNull': ['$source_first_name', 'Unknown']}, ' ', {'$ifNull':['$source_last_name', 'Unknown']}]} } } }, {'$sort': ('count', -1) } )
        qlist = list(queryset)
        total = len(qlist)
        result = qlist[offset:offset+items_per_page]
        #print 'qset is ' + str(qlist)
        serializer = AccountCountSerializer(result, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAccounts(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        start_date = int(request.GET.get('start_date'))
        end_date = int(request.GET.get('end_date'))
        sub_view = request.GET.get('subview')
        superfilters = request.GET.get('superfilters')
        super_filters = json.loads(superfilters)
        #print 'super filters are ' + str(super_filters)
        date_field = None
        if super_filters is not None:
            if 'date_types' in super_filters: # need to filter by a certain type of date
                date_field = super_filters['date_types']
                if start_date is not None:
                    utc_day_start_epoch =  datetime.fromtimestamp(float(start_date / 1000))
                    #utc_day_start_epoch = str('{0:f}'.format(utc_day_start_epoch).rstrip('0').rstrip('.'))
                    print 'utc start epoch is ' + str(utc_day_start_epoch)
       
                    #local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
                #print 'start2 is ' + str(time.time())
                if end_date is not None:
                    utc_day_end_epoch = datetime.fromtimestamp(float(end_date / 1000))
                    #utc_day_end_epoch = str('{0:f}'.format(utc_day_end_epoch).rstrip('0').rstrip('.'))
                    print 'utc end epoch is ' + str(utc_day_end_epoch)
                utc_day_start_string = datetime.strftime(utc_day_start_epoch, '%Y-%m-%dT%H-%M-%S.000+0000')
                utc_day_end_string = datetime.strftime(utc_day_end_epoch, '%Y-%m-%dT%H-%M-%S.000+0000')
                print 'utc start string is ' + str(utc_day_start_string)
                print 'utc end string is ' + str(utc_day_end_string)
                
        result = []
        company_field_qry = 'company_id'
        #print 'start time was '  + str(time.time())
        collection = Account._get_collection()
        if date_field is None:
            total = collection.find({'company_id': int(company_id)}).count() #.hint('company_id_1')
        else:
            total = collection.find({'company_id': int(company_id), date_field: {'$gte':utc_day_start_string, '$lte':utc_day_end_string}}).count() #.hint('company_id_1')
        
        if date_field is None:
            queryset = Account.objects(company_id=company_id).skip(offset).limit(items_per_page)
        else:
            date_field_start_qry = date_field + '__gte'
            date_field_end_qry = date_field + '__lte'
            company_field_qry = 'company_id'
            querydict = {company_field_qry: company_id, date_field_start_qry: utc_day_start_string, date_field_end_qry: utc_day_end_string}
            queryset = Account.objects(**querydict).skip(offset).limit(items_per_page)
        
        #qlist = list(queryset)
        #print 'start time3 was '  + str(time.time())
        #total = len(qlist)
        #result = qlist[offset:offset+items_per_page]
        #print 'start time4 was '  + str(time.time())
        for account in queryset:
            leadsTemp = []
            leads = account['leads']
            for lead in leads: # each 'lead' here is an object of type {lead_id_type: lead_id} e.g. {'sfdc_contact_id': 1234}
                for k, v in lead.iteritems():
                    lead_field_qry = k
                    querydict = {lead_field_qry: v, company_field_qry: company_id}
                    qset = Lead.objects(**querydict).only('source_first_name').only('source_last_name').only('id').first()
                    #print 'qset ' + str(qset)
                    #qset_actual_lead_list_temp = [qset_lead.to_mongo().to_dict() for qset_lead in qset]
                    #for qset_actual_lead in qset_actual_lead_list_temp:
                    leadsTemp.append(qset)
            account['leads'] = leadsTemp
            result.append(account)
        
        #result.sort(key=lambda account:len(account.leads))
        #print 'qset is ' + str(qlist)
        #print 'start time5 was '  + str(time.time())
        serializer = AccountSerializer(result, many=True)  
        #print 'start time6 was '  + str(time.time()) 
        type = 'accounts'
        return JsonResponse({'count' : total, 'results': serializer.data, 'type': type})    
    except Exception as e:
        print 'exception while getting all accounts ' + str(e)
        return JsonResponse({'Error' : str(e)})

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def matchAccountName(request, id, accountSearchName):
    try:
        if accountSearchName is None:
            return JsonResponse({'count' : 0, 'results': None})  
        
        company_id = request.user.company_id
        
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        
        accounts =  Account.objects(company_id=company_id)
        accounts_list = list(accounts)
        #accounts_list.sort(key=lambda x:len(x.source_name), reverse=False)
        
        results_temp = matchingAlgo(request, search_name=accountSearchName, entries=accounts_list, object_type='account')
        results = results_temp[offset:offset+items_per_page]
        serializer = AccountSerializer(results, many=True)   
        return JsonResponse({'count' : len(results_temp), 'results': serializer.data}) 
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
            
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def matchCompanyName(request, id, companySearchName):    
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        
        queryset =  Lead.objects(company_id=company_id).aggregate( { '$group': { '_id': '$source_company', 'count': { '$sum': 1 }, 'name' : { '$push': { '$concat': [{'$ifNull': ['$source_first_name', 'Unknown']}, ' ', {'$ifNull':['$source_last_name', 'Unknown']}]} } } }, {'$sort': OrderedDict([('_id', 1), ('count', -1) ])} )
        qlist = list(queryset)
        
        results_temp = matchingAlgo(request, search_name=companySearchName, entries=qlist, object_type='company')
        results = results_temp[offset:offset+items_per_page]
        serializer = AccountCountSerializer(results, many=True)   
        return JsonResponse({'count' : len(results_temp), 'results': serializer.data}) 
        
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
