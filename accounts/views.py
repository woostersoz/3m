import datetime, json
from datetime import timedelta, date, datetime
import pytz

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

from integrations.views import Marketo, Salesforce #, get_sfdc_test
from accounts.serializers import AccountCountSerializer, AccountSerializer
from accounts.models import Account
from leads.models import Lead
from mmm.views import matchingAlgo


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
        queryset =  Lead.objects(company_id=company_id).aggregate( { '$group': { '_id': '$source_company', 'count': { '$sum': 1 }, 'name' : { '$push': { '$concat': [ {'$ifNull': ['$source_first_name', 'Unknown']}, ' ', {'$ifNull':['$source_last_name', 'Unknown']}]} } } }, {'$sort': OrderedDict([('_id', 1), ('count', -1) ])} )
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
        
        company_field_qry = 'company_id'
        
        queryset =  Account.objects(company_id=company_id)
        qlist = list(queryset)
        total = len(qlist)
        result = qlist[offset:offset+items_per_page]
        for account in result:
            leadsTemp = []
            leads = account['leads']
            for lead in leads: # each 'lead' here is an object of type {lead_id_type: lead_id} e.g. {'sfdc_contact_id': 1234}
                for k, v in lead.iteritems():
                    lead_field_qry = k
                    querydict = {lead_field_qry: v, company_field_qry: company_id}
                    qset = Lead.objects(**querydict).only('source_first_name').only('source_last_name').only('id').first()
                    print 'qset ' + str(qset)
                    #qset_actual_lead_list_temp = [qset_lead.to_mongo().to_dict() for qset_lead in qset]
                    #for qset_actual_lead in qset_actual_lead_list_temp:
                    leadsTemp.append(qset)
            account['leads'] = leadsTemp
        #print 'qset is ' + str(qlist)
        serializer = AccountSerializer(result, many=True)   
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
