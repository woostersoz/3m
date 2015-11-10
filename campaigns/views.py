import datetime, json
from datetime import timedelta, date, datetime

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

from integrations.views import Marketo, Salesforce
from campaigns.serializers import CampaignSerializer
from campaigns.models import Campaign, EmailEvent
from superadmin.models import SuperIntegration
from company.models import CompanyIntegration
from campaigns.tasks import retrieveMktoCampaigns, retrieveSfdcCampaigns, retrieveHsptCampaigns
from campaigns.serializers import EmailEventSerializer
from mmm.views import exportToCsv, _get_code
# get leads 

#@api_view(['GET'])
class CampaignsViewSet(drfme_generics.ListCreateAPIView): #deprecated
    
    serializer_class = CampaignSerializer
    
    def get_queryset(self):
        #print 'in query'
        if 'code' in self.kwargs:
            queryset = None
        else:
            #print 'no code'
            queryset = Campaign.objects.all()
            
        return queryset
    
#     def list(self, request, account_username=None):
#         account = Account.objects.filter(username=account_username)
#         try:
#             if 0 < len(account):
#                 #serializedList = LeadSerializer(Lead.objects(), many=True)
#                 #return Response(serializedList.data)
#                 
#                 result = saveMktoCampaigns(request)
#                 return Response(result)
#             else:
#                 return Response("User " + account_username + " does not exist")
#         except Exception as e:
#             return Response(str(e))

@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def getAllCampaigns(request, id):
    try:
        company_id = request.user.company_id
        page_number = int(request.GET.get('page_number'))
        items_per_page = int(request.GET.get('per_page'))
        offset = (page_number - 1) * items_per_page
        total = Campaign.objects.filter(company_id=company_id).count()
        
        queryset = Campaign.objects.filter(company_id=company_id).skip(offset).limit(items_per_page)
        
        serializer = CampaignSerializer(queryset, many=True)   
        return JsonResponse({'count' : total, 'results': serializer.data})    
    except Exception as e:
        return JsonResponse({'Error' : str(e)})

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveCampaigns(request, id):
        code = request.GET.get('code')
        user_id = request.user.id
        company_id = request.user.company_id
        try:
            if code == 'mkto':
                result = retrieveMktoCampaigns.delay(user_id=user_id, company_id=company_id)
            elif code == 'sfdc': 
                result = retrieveSfdcCampaigns.delay(user_id=user_id, company_id=company_id)
            elif code == 'hspt': 
                result = retrieveHsptCampaigns.delay(user_id=user_id, company_id=company_id)
            else: 
                result =  'Nothing to report'
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def retrieveCampaignsDaily(request, id):
    code = request.GET.get('code')
    user_id = request.user.id
    #company_id = request.user.company_id
    company_id = id
    try:
#         if code == 'mkto':
#             #result = retrieveMktoContacts.delay(user_id=user_id, company_id=company_id)
#             pass
#         elif code == 'sfdc': 
#             result = retrieveSfdcCampaignsDaily.delay(user_id=user_id, company_id=company_id)
#         elif code == 'hspt': 
#             pass
#             #result = retrieveHsptContacts.delay(user_id=user_id, company_id=company_id)
#         else:
#             result =  'Nothing to report'
        result = None
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    
@api_view(['GET'])
#@renderer_classes((JSONRenderer,))    
def filterCampaignEmailEventsByType(request, id):
    user_id = request.user.id
    company_id = request.user.company_id
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    event_type = request.GET.get('event_type')
    campaign_guid = request.GET.get('campaign_guid')
    email_id = request.GET.get('email_id')
    query_type = request.GET.get('query_type')
    page_number = int(request.GET.get('page_number'))
    items_per_page = int(request.GET.get('per_page'))
    system_type = request.GET.get('system_type')
    chart_name = request.GET.get('chart_name')
    export_type = request.GET.get('export_type')
    offset = (page_number - 1) * items_per_page
    print ' in filter 22'
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
            print 'found code' + str(code)
                  
        if code is  None:
            raise ValueError("No integrations defined")  
        elif code == 'mkto':
            pass
        elif code == 'sfdc': 
            pass
            #result = filterLeadsSfdc(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, lead_type=lead_type, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code)
        elif code == 'hspt': 
            result = filterCampaignEmailEventsByTypeHspt(user_id=user_id, company_id=company_id, start_date=start_date, end_date=end_date, event_type=event_type, email_id=email_id, query_type=query_type, page_number=page_number, items_per_page=items_per_page, system_type=system_type, offset=offset, code=code, campaign_guid=campaign_guid, export_type=export_type)
            result['portal_id'] = client_secret
        else:
            result =  'Nothing to report'
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    

#filter campaign email events for Campaign Email Performance chart  
def filterCampaignEmailEventsByTypeHspt(user_id, company_id, start_date, end_date, event_type, email_id, query_type, page_number, items_per_page, system_type, offset, code, campaign_guid, export_type):
    original_start_date = int(start_date) * 1000
    original_end_date = int(end_date) * 1000
    #print 'start ' + str(original_start_date) 
    #print 'end ' + str(original_end_date) 
#     if start_date is not None:
#         local_start_date_naive = datetime.fromtimestamp(float(start_date))
#         local_start_date = get_current_timezone().localize(local_start_date_naive, is_dst=None)
#     if end_date is not None:
#         local_end_date_naive = datetime.fromtimestamp(float(end_date))
#         local_end_date = get_current_timezone().localize(local_end_date_naive, is_dst=None)
#     utc_current_date = datetime.utcnow()
    #print 'filter start us ' + str(local_start_date) + ' and edn is ' + str(local_end_date)
    code = _get_code(company_id, system_type)
     
    try:
        
#         guid_field_qry = 'guid'
#         company_field_qry = 'company_id'
#         emails_field_qry = 'emails.id'
#         emails_qry = '$emails'
#         event_qry = '$emails.events.' + event_type 
#         event_date_qry = '$emails.events.' + event_type + '.created'
#         event_date_qry2 = 'emails.events.' + event_type + '.created' #without $
#         recipient_qry = '$emails.events.' + event_type + '.recipient'
#         id_qry = '$emails.events.' + event_type + '.id'
#         querydict = {company_field_qry: company_id, guid_field_qry: campaign_guid}
        #print 'qd is ' + str(querydict)
        #events_list = Campaign.objects(**querydict).aggregate({'$unwind': results_qry}, {'$project': {'_id':0, 'event_id': id_qry, 'date': event_date_qry, 'recipient': recipient_qry}}) #{'$match' : {event_date_qry2: {'$gte': original_start_date, '$lte': original_end_date }}},
        #events_list = Campaign.objects(**querydict).aggregate({'$unwind': emails_qry}, {'$match': {emails_field_qry: int(email_id)}}, {'$unwind': event_qry}, {'$project': {'_id':0, 'event_id': id_qry, 'date': event_date_qry, 'recipient': recipient_qry}}, {'$match' : {'date': {'$gte': original_start_date, '$lte': original_end_date }}})#,   
        events_list = EmailEvent.objects(Q(company_id=company_id) & Q(campaign_guid=campaign_guid) & Q(email_id=int(email_id)) & Q(event_type=event_type) & Q(created__gte=int(original_start_date)) & Q(created__lte=int(original_end_date)))            
        events_list = list(events_list)      
        #print 'final results ' + str(events_list)
        total = len(events_list)
        final_events_list = events_list[offset:int(items_per_page + offset)]
        #leads = Lead.objects(**querydict).skip(offset).limit(items_per_page)
        serializer = EmailEventSerializer(final_events_list, many=True)   
        
        results = {'count' : total, 'results': serializer.data}
        return results
    except Exception as e:
        return JsonResponse({'Error' : str(e)})
    