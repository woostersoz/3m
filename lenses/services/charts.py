import datetime, json


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

from authentication.models import Account
from authentication.serializers import AccountSerializer

from celery import task
from pickle import NONE
from mongoengine.django.shortcuts import get_document_or_404

from integrations.views import Marketo, Salesforce #, get_sfdc_test
from activities.serializers import ActivitySerializer
from leads.models import Lead

from activities.tasks import retrieveMktoActivities, retrieveSfdcActivities

class FunnelChart(object):

    def computeMetrics(self, user_id = None, company_id = None):

        #company_id = self.request.user.company_id
        #start with total number of leads
        allLeads = Lead.objects(company_id = company_id).all()
        total_leads = len(allLeads)

        #move on to engaged leads
        campaignActivities = {1, 2, 3, 7, 8} # need to get these dynamically?
        engaged_leads = 0;

        for lead in allLeads:
            if 'mkto' in lead.activities:
                currentActivities = lead.activities['mkto']
                for i in range(len(currentActivities)):
                    if currentActivities[i]['activityTypeId'] in campaignActivities:
                        engaged_leads += 1
                        break

        results = {'total_leads' : total_leads, 'engaged_leads': engaged_leads}
        return results