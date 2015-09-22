import datetime, json, time
from datetime import timedelta, date, datetime
import pytz
import urllib
#import logging

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
from leads.serializers import LeadSerializer
from leads.models import Lead
from leads.tasks import retrieveMktoLeads, retrieveSfdcLeads, retrieveHsptLeads
from superadmin.models import SuperIntegration
from company.models import CompanyIntegration
from analytics.models import AnalyticsData, AnalyticsIds
from mmm.views import exportToCsv

# get leads 

def encodeKey(key): 
    return key.replace("\\", "\\\\").replace("\$", "\\u0024").replace(".", "\\u002e")


def decodeKey(key):
    return key.replace("\\u002e", ".").replace("\\u0024", "\$").replace("\\\\", "\\")


def _str_from_date(dateTime, format=None): # returns a datetime object from a timezone like string 
    
    if format == 'short': # short format of date string found in Mkto created date
        return datetime.strftime(dateTime, '%Y-%m-%d')
    elif format == 'short_with_time':
        return datetime.strftime(dateTime, '%Y-%m-%d %H:%M:%S')
    else:
        return datetime.strftime(dateTime, '%Y-%m-%dT%H:%M:%SZ') # found in status record
    
#@api_view(['GET'])
class LeadsViewSet(drfme_generics.ListCreateAPIView): #deprecated
    
    serializer_class = LeadSerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            print 'no code'
            company_id = self.request.user.company_id
            page_number = self.request.GET.get('page_number')
            items_per_page = 10
            offset = (page_number - 1) * items_per_page
            total = Lead.objects.filter(company_id=company_id).count()
            
            queryset = Lead.objects().filter(company_id=company_id).skip(offset).limit(items_per_page)
            
        return queryset
    
#     def list(self, request, account_username=None):
#         account = Account.objects.filter(username=account_username)
#         try:
#             if 0 < len(account):
#                 #serializedList = LeadSerializer(Lead.objects(), many=True)
#                 #return Response(serializedList.data)
#                 
#                 result = saveMktoLeads(request)
#                 return Response(result)
#             else:
#                 return Response("User " + account_username + " does not exist")
#         except Exception as e:
#             return Response(str(e))

def _get_code(company_id, system_type):
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
        else:
            return code
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
              
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAllLeads(request, id):
    try:
        #log = logging.getLogger(__name__)
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        collection = Lead._get_collection()
        total = collection.find({'company_id': int(company_id)}).hint('company_id_1').count()
        #print 'got count'
        total_with_company = 0 #collection.find({'company_id' : company_id, 'source_company' : {'$ne' : None}}).hint('source_sourcedata1_index').count()
        #print 'got count w company'
        #total = Lead.objects.filter(company_id=company_id).count()
        #total_with_company = Lead.objects.filter(Q(company_id=company_id) & Q(source_company__ne=None)).count()
        total_without_company = total - total_with_company
        queryset = Lead.objects(company_id=company_id).skip(offset).limit(items_per_page)
        
        #leads_cursor = collection.find({'company_id': int(company_id)}).hint('co_fname_lname').sort([('source_first_name', 1), ('source_last_name', 1)]) 
        #queryset = list(leads_cursor)
        #queryset = queryset[offset: offset + items_per_page]
        #total = collection.find({'company_id': int(company_id)}).hint('company_id_1').count()
            
        
        #queryset = Lead.objects().filter(company_id=company_id).order_by('-source_first_name', '-source_last_name').skip(offset).limit(items_per_page)
        #print 'got qset'
        stages = None #Lead.objects().filter(company_id=company_id).item_frequencies('source_stage')
        sources = None #Lead.objects().filter(company_id=company_id).item_frequencies('source_source')
        serializer = LeadSerializer(queryset, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data, 'total_with_company': total_with_company, 'total_without_company': total_without_company, 'stages':stages, 'sources':sources})    
    except Exception as e:
        print 'exception while getting all leads ' + str(e)
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeads(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    lead_type = request.GET.get('lead_type')
    series_type = request.GET.get('series_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    export_type = request.GET.get('export_type')
    offset = (page_number - 1) * items_per_page
    export_types = ['csv']
    
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
                    client_secret = existingIntegration['integrations'][code]['client_secret']
                    print 'cs is ' + client_secret
            #print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'mkto':
            result = filterLeadsMkto(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, chart_name=chart_name, export_type=export_type)
        elif code == 'sfdc': 
            pass
            #result = filterLeadsSfdc(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code)
        elif code == 'hspt': 
            result = filterLeadsHspt(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, chart_name=chart_name, export_type=export_type)
            result['portal_id'] = client_secret
        else:
            result =  'Nothing to report'
        
        #if not export to CSV or other format
        if export_type not in export_types:    
            return JsonResponse(result)
        else:
            exportToCsv.delay('lead', code, result, 'chart', chart_name, user_id, company_id)
            return JsonResponse({'Success' : 'File export started'})
    except Exception as e:
        print 'exception while retrieving leads ' + str(e)
        return JsonResponse({'Error' : str(e)})

#filter leads for Pipeline Duration chart
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsByDuration(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    lead_type = request.GET.get('lead_type')
    series_type = request.GET.get('series_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    export_type = request.GET.get('export_type')
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
        elif code == 'mkto':
            result = filterLeadsByDurationMkto(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, chart_name=chart_name, export_type=export_type)
        elif code == 'sfdc': 
            pass
            #result = filterLeadsSfdc(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code)
        elif code == 'hspt': 
            result = filterLeadsByDurationHspt(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, chart_name=chart_name, export_type=export_type)
        else:
            result =  'Nothing to report'
        return result
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsBySource(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    source_source = request.GET.get('source')
    
    # don't encode the key here since we are looking into the value in the lead record directly
    #source_source = encodeKey(urllib.unquote(source_source).decode('utf8'))
    
    lead_type = request.GET.get('lead_type')
    series_type = request.GET.get('series_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    export_type = request.GET.get('export_type')
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
        elif code == 'mkto':
            result = filterLeadsBySourceMkto(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, source=source_source, export_type=export_type)
        elif code == 'sfdc': 
            pass
            #result = filterLeadsSfdc(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code)
        elif code == 'hspt': 
            result = filterLeadsBySourceHspt(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, source=source_source, export_type=export_type)
        else:
            result =  'Nothing to report'
        return result
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsByRevenueSource(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    source_source = request.GET.get('source')
    
    source_source = encodeKey(urllib.unquote(source_source).decode('utf8'))
    #print 'source is ' + source_source
    
    lead_type = request.GET.get('lead_type')
    series_type = request.GET.get('series_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    export_type = request.GET.get('export_type')
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
        elif code == 'mkto':
            result = filterLeadsByRevenueSourceMkto(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, source=source_source, chart_name=chart_name, export_type=export_type)
        elif code == 'sfdc': 
            pass
            #result = filterLeadsSfdc(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code)
        elif code == 'hspt': 
            result = filterLeadsByRevenueSourceHspt(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, series_type=series_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, source=source_source, chart_name=chart_name, export_type=export_type)
        else:
            result =  'Nothing to report'
        return result
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

def filterLeadsMkto(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name, export_type):    
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
        leads = []
        
        company_field_qry = 'company_id'
        system_field_qry = 'leads__' + code + '__exists'
        start_date_created_field_qry = 'source_created_date__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        chart_name_qry = 'chart_name'
#         if lead_type is not None:
#             if query_type == "strict": # for the Contacts Distribution chart
#                 pass
# #               start_date_field_qry = 'source_created_date__gte'
# #               end_date_field_qry = 'source_created_date__lte'
# #               querydict = {system_field_qry: True, company_field_qry: company_id,  start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[lead_type]} #start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date,
#             else:
#                 lead_type_qry = 'results__ids__' + lead_type + '__exists'
#                 #querydict = {company_field_qry: company_id} #, lead_type_qry: True
        if query_type == "strict": #we are not done
            if series_type == 'Total':
                series_type = 'total'
            elif series_type == 'Inflow':
                series_type = 'inflows'
            elif series_type == 'Outflow':
                series_type = 'outflows'    
            
            system_type_qry = 'system_type'
            start_date_qry = 'date__gte'
            end_date_qry = 'date__lte'
            
            
            start_label = datetime.strftime(local_start_date_naive, '%Y-%m-%d')
            end_label = datetime.strftime(local_end_date_naive, '%Y-%m-%d')
            
            results_qry = '$results.' + lead_type + '.' + series_type
            print 'results q is ' + results_qry
            querydict = {company_field_qry: company_id, system_type_qry: system_type, start_date_qry: start_label, end_date_qry: end_label, chart_name_qry: chart_name}
            cursor = AnalyticsIds.objects(**querydict).aggregate( { '$unwind': results_qry }, { '$group': { '_id': None, 'list': { '$push': results_qry } } } )
            ids = None
            
            for entry in list(cursor):
                if 'list' in entry:
                    ids = entry['list']
                else:
                    return []
            
            if ids is None:
                return []
            
            leads = Lead.objects(company_id=company_id, mkto_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
            #print 'start5 is ' + str(time.time())
            #now do the calculations
            total = Lead.objects(company_id=company_id, mkto_id__in=ids).count() #len(leads)
            #print 'start6 is ' + str(time.time())
        
            serializer = LeadSerializer(leads, many=True)   
            return {'count' : total, 'results': serializer.data}   
    
        else: #not done. need to loop through leads to find which leads truly meet the criteria
            system_type_qry = 'system_type'
            date_qry = 'date'
            querydict = {company_field_qry: company_id, system_type_qry: system_type, date_qry: local_start_date, chart_name_qry: chart_name}
            print 'qd is ' + str(querydict)
            analyticsIds = AnalyticsIds.objects(**querydict).only('results').first()
            #print 'start3 is ' + str(time.time())
            if analyticsIds is None:
                return []
            print 'lead tupe is ' + lead_type
            ids = analyticsIds['results'].get(lead_type, None)
            print 'ids is ' + str(ids)
            leads = Lead.objects(company_id=company_id, mkto_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
            #print 'start5 is ' + str(time.time())
            #now do the calculations
            total = Lead.objects(company_id=company_id, mkto_id__in=ids).count() #len(leads)
            #print 'start6 is ' + str(time.time())
        
        serializer = LeadSerializer(leads, many=True)   
        return {'count' : total, 'results': serializer.data}   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

#filter leads for Pipeline Duration chart       
def filterLeadsByDurationMkto(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name, export_type):
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    
    start_key = local_start_date.strftime('%Y-%m-%d')
    end_key = local_end_date.strftime('%Y-%m-%d')
    
    e = local_end_date
    s = local_start_date - timedelta(days=1)
    delta = timedelta(days=1)
    
    company_field_qry = 'company_id'
    chart_name_qry = 'chart_name'
    date_query = 'date'
    ids = []  
    try: 
        while s < (e - delta):
                s += delta #increment the day counter
                start_key = s.strftime('%Y-%m-%d')
                
                querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: start_key} 
                
                existingData = AnalyticsIds.objects(**querydict).first()
                
                if existingData is None:
                    continue
                
                day_results = existingData['results'][lead_type]
                if day_results is None:
                    continue
                
                ids.extend(day_results)
        
        leads = Lead.objects(company_id=company_id, mkto_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
                #print 'start5 is ' + str(time.time())
                #now do the calculations
        total = Lead.objects(company_id=company_id, mkto_id__in=ids).count() #len(leads)
                #print 'start6 is ' + str(time.time())
            
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
    
#filter leads for Source Breakdown chart    
def filterLeadsBySourceMkto(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, source, export_type):
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    
    start_key = local_start_date.strftime('%Y-%m-%d')
    end_key = local_end_date.strftime('%Y-%m-%d')
    #utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    #code = _get_code(company_id, system_type)
     
    try:
        
        start_date_field_qry = 'source_created_date__gte'
        end_date_field_qry = 'source_created_date__lte'
        source_field_qry = 'leads__mkto__originalSourceType__exact'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__' + code + '__exists'
        print 'source ' + source
        querydict = {system_field_qry: True, company_field_qry: company_id, source_field_qry: source, start_date_field_qry : start_key, end_date_field_qry : end_key}
        total = Lead.objects(**querydict).count()
        leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})  
        
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
    
#filter leads for Revenue Source  chart
#@renderer_classes((JSONRenderer,))    
def filterLeadsByRevenueSourceMkto(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, source, chart_name, export_type):
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    
    start_key = local_start_date.strftime('%Y-%m-%d')
    end_key = local_end_date.strftime('%Y-%m-%d')
    
    e = local_end_date
    s = local_start_date - timedelta(days=1)
    delta = timedelta(days=1)
    #print 'names are ' + chart_name + ' ' + source
    company_field_qry = 'company_id'
    chart_name_qry = 'chart_name'
    date_query = 'date'
    ids = []  
    try: 
        while s < (e - delta):
                s += delta #increment the day counter
                start_key = s.strftime('%Y-%m-%d')
                
                querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: start_key} 
                
                existingData = AnalyticsIds.objects(**querydict).first()
                
                if existingData is None:
                    continue
                
                day_results = None
                if source in existingData['results']:
                    day_results = existingData['results'][source]['closed']
                if day_results is None:
                    continue
                
                ids.extend(day_results)
        
        leads = Lead.objects(company_id=company_id, mkto_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
                #print 'start5 is ' + str(time.time())
                #now do the calculations
        total = Lead.objects(company_id=company_id, mkto_id__in=ids).count() #len(leads)
                #print 'start6 is ' + str(time.time())
            
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
    
def filterLeadsHspt(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name, export_type):    
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
    export_types = ['csv']
    
    try:
        leads = []
        
        company_field_qry = 'company_id'
        system_field_qry = 'leads__' + code + '__exists'
        start_date_created_field_qry = 'source_created_date__gte'
        end_date_created_field_qry = 'source_created_date__lte'
        chart_name_qry = 'chart_name'
#         if lead_type is not None:
#             if query_type == "strict": # for the Contacts Distribution chart
#                 pass
# #               start_date_field_qry = 'source_created_date__gte'
# #               end_date_field_qry = 'source_created_date__lte'
# #               querydict = {system_field_qry: True, company_field_qry: company_id,  start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[lead_type]} #start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date,
#             else:
#                 lead_type_qry = 'results__ids__' + lead_type + '__exists'
#                 #querydict = {company_field_qry: company_id} #, lead_type_qry: True
        if query_type == "strict": #we are not done
            if series_type == 'Total':
                series_type = 'total'
            elif series_type == 'Inflow':
                series_type = 'inflows'
            elif series_type == 'Outflow':
                series_type = 'outflows'    
            
            system_type_qry = 'system_type'
            start_date_qry = 'date__gte'
            end_date_qry = 'date__lte'
            
            
            start_label = datetime.strftime(local_start_date_naive, '%Y-%m-%d')
            end_label = datetime.strftime(local_end_date_naive, '%Y-%m-%d')
            
            results_qry = '$results.' + lead_type + '.' + series_type
            print 'results q is ' + results_qry
            querydict = {company_field_qry: company_id, start_date_qry: start_label, end_date_qry: end_label, chart_name_qry: chart_name}
            cursor = AnalyticsIds.objects(**querydict).aggregate( { '$unwind': results_qry }, { '$group': { '_id': None, 'list': { '$push': results_qry } } } )
            ids = None
            
            for entry in list(cursor):
                if 'list' in entry:
                    ids = entry['list']
                else:
                    return []
            
            if ids is None:
                return []
            
            
            collection = Lead._get_collection()
            if export_type not in export_types:
                leads_cursor = collection.find({'hspt_id' : {'$in': ids}, 'company_id': int(company_id)}).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
                leads = list(leads_cursor)
                total = len(leads)
                serializer = LeadSerializer(leads, many=True)   
                return {'count' : total, 'results': serializer.data} 
            else:
                leads_cursor = collection.find({'hspt_id' : {'$in': ids}, 'company_id': int(company_id)})
                leads = list(leads_cursor)
                total = len(leads)
                result = [lead.to_mongo().to_dict() for lead in leads]  
                #print 'result is ' + str(result)
                return {'count' : total, 'results': result}
            #print 'start5 is ' + str(time.time())
            #now do the calculations
            #total = Lead.objects(hspt_id__in=ids).count() #len(leads)
            #print 'start6 is ' + str(time.time())
        
               
    
        else: #not done. need to loop through leads to find which leads truly meet the criteria
            system_type_qry = 'system_type'
            date_qry = 'date'
            querydict = {company_field_qry: company_id, date_qry: local_start_date, chart_name_qry: chart_name}
            print 'qd is ' + str(querydict)
            analyticsIds = AnalyticsIds.objects(**querydict).first()
            #print 'start3 is ' + str(time.time())
            if analyticsIds is None:
                return []
            #print 'lead type is ' + lead_type
            ids = analyticsIds['results'].get(lead_type, None)
            #print 'ids is ' + str(ids)
            if export_type not in export_types:
                leads = Lead.objects().filter(company_id=company_id, hspt_id__in=ids).order_by('source_first_name', 'source_last_name').skip(offset).limit(items_per_page).hint('co_hspt_id_fname_lname')
                total = Lead.objects().filter(company_id=company_id, hspt_id__in=ids).hint('co_hspt_id_fname_lname').count()
                serializer = LeadSerializer(leads, many=True)   
                return {'count' : total, 'results': serializer.data} 
            else:
                #leads = Lead.objects().filter(company_id=company_id, hspt_id__in=ids).order_by('hspt_id').hint('company_id_1_hspt_id_1')
                #leads = list(leads)
                #total = len(leads)
                #result = [lead.to_mongo().to_dict() for lead in leads]  
                #print 'result is ' + str(result)
                return {'results': ids} #return only the IDs here - let the export fxn take care of retrieving leads else takes too long
            #total = collection.find({'hspt_id' : {'$in': ids}, 'company_id': int(company_id)}).count()
            #leads = Lead.objects(hspt_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
            #print 'start5 is ' + str(time.time())
            #now do the calculations
            #total = Lead.objects(hspt_id__in=ids).count() #len(leads)
            #print 'start6 is ' + str(time.time())
        
          
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
def filterLeadsHspt_deprecated(user_id, company_id, start_date, end_date, lead_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name):    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        #local_start_date = _str_from_date(local_start_date_naive, "short")
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    
    start_key = local_start_date.strftime('%m-%d-%Y')
    end_key = local_end_date.strftime('%m-%d-%Y')
    date_range = start_key + ' - ' + end_key
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    #code = _get_code(company_id, system_type)
     
    try:
        leads = []
        
        if lead_type is not None:
            date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' }
            start_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__gte'
            end_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__lte'

            stage_field_map = { "Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer' }
            stage_field_qry = 'leads__hspt__properties__lifecyclestage'
        else:
            start_date_field_qry = 'leads__hspt__properties__createdate__gte'
            end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        
        company_field_qry = 'company_id'
        system_field_qry = 'leads__' + code + '__exists'
        start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
        
        if query_type == "strict": #we are done
            system_type_qry = 'system_type'
            date_range_qry = 'date_range'
            querydict = {company_field_qry: company_id, system_type_qry: system_type, date_range_qry: date_range} #start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date,
        else: #not done. need to loop through leads to find which leads truly meet the criteria
            system_type_qry = 'system_type'
            date_qry = 'date'
            querydict = {company_field_qry: company_id, system_type_qry: system_type, date_qry: start_key}
            #print 'start2 is ' + str(time.time())
        analyticsIds = AnalyticsIds.objects(**querydict).only('results').first()
        #print 'start3 is ' + str(time.time())
        if analyticsIds is None:
            return []
        
        ids = analyticsIds['results'].get(lead_type, None)
        #print 'start4 is ' + str(time.time())
        leads = Lead.objects(hspt_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
        #print 'start5 is ' + str(time.time())
        #now do the calculations
        total = Lead.objects(hspt_id__in=ids).count() #len(leads)
        #print 'start6 is ' + str(time.time())
        
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
    

def filterLeadsByDurationHspt(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, chart_name, export_type):
    
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    code = _get_code(company_id, system_type)  
    start_key = local_start_date.strftime('%m-%d-%Y')
    end_key = local_end_date.strftime('%m-%d-%Y')
    date_range = start_key + ' - ' + end_key  
    
    system_type_qry = 'system_type'
    date_range_qry = 'date_range'
    company_field_qry = 'company_id'
    querydict = {company_field_qry: company_id, system_type_qry: system_type, date_range_qry: date_range}

    try:
        analyticsIds = AnalyticsIds.objects(**querydict).only('results').first()
        #print 'start3 is ' + str(time.time())
        if analyticsIds is None:
            return []
        
        ids = analyticsIds['results'].get(lead_type, None)
        #print 'start4 is ' + str(time.time())
        leads = Lead.objects(hspt_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
        #print 'start5 is ' + str(time.time())
        #now do the calculations
        total = Lead.objects(hspt_id__in=ids).count() #len(leads)
        #print 'start6 is ' + str(time.time())
        
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
 
#filter leads for Pipeline Duration chart
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterLeadsByDurationDeprecated(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    lead_type = request.GET.get('lead_type')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    code = _get_code(company_id, system_type)
    
    try:
        
        leads = []
        new_leads = []
        lead_type_temp = ""
        
        if lead_type is not None:
            
            date_field_map = { "Subscribers" : 'hs_lifecyclestage_subscriber_date', "Leads" : 'hs_lifecyclestage_lead_date', "MQLs" : 'hs_lifecyclestage_marketingqualifiedlead_date', "SQLs" : 'hs_lifecyclestage_salesqualifiedlead_date', "Opportunities" : 'hs_lifecyclestage_opportunity_date', "Customers" : 'hs_lifecyclestage_customer_date' }
            company_field_qry = 'company_id'
            system_field_qry = 'leads__' + code + '__exists'
             # for the Contacts Distribution chart
            stage_field_map = { "Subscribers" : 'subscriber', "Leads" : 'lead', "MQLs" : 'marketingqualifiedlead', "SQLs" : 'salesqualifiedlead', "Opportunities" : 'opportunity', "Customers" : 'customer' }
            stage_field_qry = 'leads__hspt__properties__lifecyclestage'
            if lead_type != "All":
                start_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__gte'
                end_date_field_qry = 'leads__hspt__properties__' + date_field_map[lead_type] + '__lte'
                start_date_created_field_qry = 'leads__hspt__properties__createdate__gte'
                end_date_created_field_qry = 'leads__hspt__properties__createdate__lte'
                querydict = {system_field_qry:True, company_field_qry: company_id, start_date_created_field_qry: local_start_date, end_date_created_field_qry: local_end_date, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date, stage_field_qry : stage_field_map[lead_type]}
                total = Lead.objects(**querydict).count()
                leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
            else:
                lead_type_temp = "All"
                #start_date_field_qry = 'leads__hspt__properties__createdate__gte'
                #end_date_field_qry = 'leads__hspt__properties__createdate__lte'
                #querydict = {company_field_qry: company_id, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
                querydict = {system_field_qry: True, company_field_qry: company_id}
                leads_temp = Lead.objects(**querydict)#.skip(offset).limit(items_per_page)
                
                for lead_temp in leads_temp:
                    this_lead_stage_temp = lead_temp['leads']['hspt']['properties']['lifecyclestage']
                    for k, v in stage_field_map.items():
                        if v == this_lead_stage_temp:
                            this_lead_stage = k
                            #print 'this lead str is ' + str(this_lead_stage) + 'and id is ' + lead_temp['hspt_id']
                            break
                    started_this_stage_date = lead_temp['leads']['hspt']['properties'][date_field_map[this_lead_stage]]
                    #print 'dates ' + str(local_start_date_naive) + ' XX ' + str(started_this_stage_date) + ' XX ' + str(local_end_date_naive)
                    if local_start_date_naive <= started_this_stage_date and started_this_stage_date <= local_end_date_naive:
                        leads.append(lead_temp)
                #we have all the leads for All so now apply offset and items per page
                total = len(leads)
                #print 'total for All is ' + str(total)
                leads = leads[offset:offset + items_per_page]
            #print 'qmap is ' + str(querydict)
            #print 'qd2 is ' + str(querydict)
            #print 'in there ' + str(len(leads)) 
            for lead in leads: # iterate over each lead
                #print ' lead id is ' + lead['hspt_id']
                lead_props = lead['leads']['hspt']['properties']
                if  lead_type_temp == "All": # if it is all, find the lead stsage from lead record
                    this_lead_stage = lead_props['lifecyclestage']
                    for stage, stagename in stage_field_map.iteritems():
                        if stagename == this_lead_stage:
                            lead_type = stage 
                #print 'lead type is ' + lead_type
                #handle average days in current stage 
                if date_field_map[lead_type] not in lead['leads']['hspt']['properties']:
                    raise ValueError("This is not possible")
                
                started_this_stage_date = lead_props[date_field_map[lead_type]]
                days_in_this_stage = (utc_current_date - started_this_stage_date).total_seconds() #remove conversion to seconds if you want dates; use .days then - no ()
                lead['leads']['hspt']['properties']['days_in_this_stage'] = days_in_this_stage
                if (query_type != "strict"): #only get days in current stage so ignore the below
                #handle transition days
                    if lead_type == "Customers":
                        stage_date1 = lead_props.get('hs_lifecyclestage_opportunity_date')
                        stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date1 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date1).total_seconds() # change for number of days
                            lead['leads']['hspt']['properties']["last_stage"] = "Opportunity"
                        elif stage_date1 is  None:
                            if stage_date2 is not None:
                                lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date2).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "SQL"
                            else: 
                                if stage_date3 is not None:
                                    lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date3).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                                else:
                                    if stage_date4 is not None:
                                        lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date4).total_seconds()
                                        lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                                    else:
                                        if stage_date5 is not None:
                                            lead['leads']['hspt']['properties']["OC"] = (started_this_stage_date - stage_date5).total_seconds()
                                            lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                        
                        if last_stage == "Opportunity":                    
                            if stage_date2 is not None and stage_date1 is not None:
                                lead['leads']['hspt']['properties']["SO"] = (stage_date1 - stage_date2).total_seconds()
                                last_stage = "SQL"
                            elif stage_date2 is None: 
                                if stage_date3 is not None:
                                    lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date3).total_seconds()
                                    last_stage = "MQL"
                                else:
                                    if stage_date4 is not None:
                                        lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date4).total_seconds()
                                        last_stage = "Lead"
                                    else:
                                        if stage_date5 is not None:
                                            lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date5).total_seconds()
                                            last_stage = "Subscriber"
                        
                        if last_stage == "SQL":     
                            if stage_date3 is not None and stage_date2 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (stage_date2 - stage_date3).total_seconds()
                                last_stage = "MQL"
                            elif stage_date3 is None:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                    last_stage = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                             
                        if last_stage == "MQL":    
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                         
                        if last_stage == "Lead":                
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                        
                    elif lead_type == "Opportunities":
                        stage_date2 = lead_props.get('hs_lifecyclestage_salesqualifiedlead_date')
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date2 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date2).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "SQL"
                        elif stage_date2 is None: 
                            if stage_date3 is not None:
                                lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date3).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                            else:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date4).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["SO"] = (started_this_stage_date - stage_date5).total_seconds()
                                        lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                         
                        if last_stage == "SQL":   
                            if stage_date3 is not None and stage_date2 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (stage_date2 - stage_date3).total_seconds()
                                last_stage = "MQL"
                            elif stage_date3 is None:
                                if stage_date4 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                    last_stage = "Lead"
                                else:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                             
                        if last_stage == "MQL": 
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                        
                        if last_stage == "Lead":              
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                                
                    elif lead_type == "SQLs":
                        stage_date3 = lead_props.get('hs_lifecyclestage_marketingqualifiedlead_date')
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date3 is not None and started_this_stage_date is not None:
                            lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date3).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "MQL"
                        elif stage_date3 is None:
                            if stage_date4 is not None:
                                lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date4).total_seconds()
                                lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                            else:
                                if stage_date5 is not None:
                                    lead['leads']['hspt']['properties']["MS"] = (started_this_stage_date - stage_date5).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                         
                        if last_stage == "MQL": 
                            if stage_date4 is not None and stage_date3 is not None: 
                                lead['leads']['hspt']['properties']["LM"] = (stage_date3 - stage_date4).total_seconds()
                                last_stage = "Lead"
                            elif stage_date4 is None:
                                    if stage_date5 is not None:
                                        lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                        last_stage = "Subscriber"
                                      
                        if last_stage == "Lead":
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                            
                    elif lead_type == "MQLs":
                        stage_date4 = lead_props.get('hs_lifecyclestage_lead_date')
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        
                        if stage_date4 is not None and started_this_stage_date is not None: 
                            lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date4).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "Lead"
                        elif stage_date4 is None:
                                if stage_date5 is not None:
                                    lead['leads']['hspt']['properties']["LM"] = (started_this_stage_date - stage_date5).total_seconds()
                                    lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                        last_stage =   lead['leads']['hspt']['properties']["last_stage"]
                        
                        if last_stage == "Lead":          
                            if stage_date5 is not None and stage_date4 is not None: 
                                lead['leads']['hspt']['properties']["SL"] = (stage_date4 - stage_date5).total_seconds()
                                #lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                                
                    elif lead_type == "Leads":
                        stage_date5 = lead_props.get('hs_lifecyclestage_subscriber_date')
                        if stage_date5 is not None and started_this_stage_date is not None: 
                            lead['leads']['hspt']['properties']["SL"] = (started_this_stage_date - stage_date5).total_seconds()
                            lead['leads']['hspt']['properties']["last_stage"] = "Subscriber"
                            
                new_leads.append(lead)
            #print 'lead props are' + '\n'.join(str(p) for p in new_leads[0].leads["hspt"]["properties"])
            #print 'old lead props are' + '\n'.join(str(p) for p in lead)
            serializer = LeadSerializer(new_leads, many=True)   
            return JsonResponse({'count' : total, 'results': serializer.data})    
        else: #lead_type is None - not allowed here
            return JsonResponse({'Error' : 'Lead Type cannot be empty'})    
                
    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
#filter leads for Source Breakdown chart  
def filterLeadsBySourceHspt(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, source, export_type):
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    code = _get_code(company_id, system_type)
     
    try:
        
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        source_field_qry = 'leads__hspt__properties__hs_analytics_source'
        company_field_qry = 'company_id'
        system_field_qry = 'leads__' + code + '__exists'
        
        querydict = {system_field_qry: True, company_field_qry: company_id, source_field_qry: source, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
        total = Lead.objects(**querydict).count()
        leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})  
        
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
#filter leads for Revenue Source  chart
#@renderer_classes((JSONRenderer,))    
def filterLeadsByRevenueSourceHspt(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, source, chart_name, export_type):
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    
    start_key = local_start_date.strftime('%Y-%m-%d')
    end_key = local_end_date.strftime('%Y-%m-%d')
    
    e = local_end_date
    s = local_start_date - timedelta(days=1)
    delta = timedelta(days=1)
    #print 'names are ' + chart_name + ' ' + source
    company_field_qry = 'company_id'
    chart_name_qry = 'chart_name'
    date_query = 'date'
    ids = []  
    try: 
        while s < (e - delta):
                s += delta #increment the day counter
                start_key = s.strftime('%Y-%m-%d')
                
                querydict = {chart_name_qry: chart_name, company_field_qry: company_id, date_query: start_key} 
                
                existingData = AnalyticsIds.objects(**querydict).first()
                
                if existingData is None:
                    continue
                
                day_results = None
                if source in existingData['results']:
                    day_results = existingData['results'][source]['closed']
                if day_results is None:
                    continue
                
                ids.extend(day_results)
        
        leads = Lead.objects(hspt_id__in=ids).skip(offset).limit(items_per_page).order_by('source_first_name', 'source_last_name') 
                #print 'start5 is ' + str(time.time())
                #now do the calculations
        total = Lead.objects(hspt_id__in=ids).count() #len(leads)
                #print 'start6 is ' + str(time.time())
            
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})   
    except Exception as e:
        return JsonResponse({'Error' : str(e)})  
#filter leads for Revenue Source  chart  
def filterLeadsByRevenueSourceHspt_deprecated(user_id, company_id, start_date, end_date, lead_type, series_type, query_type, page_number, items_per_page, system_type, offset, code, source, chart_name):
    
    offset = (page_number - 1) * items_per_page
    
    if start_date is not None:
        local_start_date_naive = datetime.fromtimestamp(float(start_date))
        local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
    if end_date is not None:
        local_end_date_naive = datetime.fromtimestamp(float(end_date))
        local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
    utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    code = _get_code(company_id, system_type)
     
    try:
        
        start_date_field_qry = 'leads__hspt__properties__createdate__gte'
        end_date_field_qry = 'leads__hspt__properties__createdate__lte'
        source_field_qry = 'leads__hspt__properties__hs_analytics_source'
        company_field_qry = 'company_id'
        revenue_field_qry = 'leads__hspt__properties__total_revenue__exists'
        system_field_qry = 'leads__' + code + '__exists'
        
        querydict = {system_field_qry:True, revenue_field_qry: True, company_field_qry: company_id, source_field_qry: source, start_date_field_qry : local_start_date, end_date_field_qry : local_end_date}
        total = Lead.objects(**querydict).count()
        leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        serializer = LeadSerializer(leads, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})  
        
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
                       
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveLeads(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    company_id = request.user.company_id
    try:
        if code == 'mkto':
            result = retrieveMktoLeads.delay(user_id=user_id, company_id=company_id)
        elif code == 'sfdc': 
            result = retrieveSfdcLeads.delay(user_id=user_id, company_id=company_id)
        elif code == 'hspt': 
            result = retrieveHsptLeads.delay(user_id=user_id, company_id=company_id)
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveLeadsDaily(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    #company_id = request.user.company_id
    company_id = id
    try:
#         if code == 'mkto':
#             result = retrieveMktoLeadsDaily.delay(user_id=user_id, company_id=company_id)
#         elif code == 'sfdc': 
#             result = retrieveSfdcLeadsDaily.delay(user_id=user_id, company_id=company_id)
#         elif code == 'hspt': 
#             result = retrieveHsptLeads.delay(user_id=user_id, company_id=company_id)
#         else:
#             result =  'Nothing to report'
        result = None
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
