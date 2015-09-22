import requests, json
import datetime
from bson import json_util

from django.views.generic.edit import FormView
from django.http import HttpResponse, JsonResponse
from django.utils.encoding import force_text

from rest_framework.renderers import JSONRenderer
from rest_framework_mongoengine import generics as drfme_generics

from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from django.core.urlresolvers import reverse_lazy
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from django.shortcuts import render_to_response
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from celery import task

from superadmin.models import SuperIntegration
from superadmin.serializers import SuperIntegrationSerializer

from company.forms import IntegrationBaseForm
from company.models import CompanyIntegration, CompanyIntegrationDeleted, BaseCompanyIntegration, TempData
from company.serializers import CompanyIntegrationSerializer, CompanyIntegrationDeletedSerializer
from leads.models import Lead
from campaigns.models import Campaign
import pytz
from authentication.models import Company
from authentication.serializers import CompanySerializer
from company.tasks import companyDataExtract

# Create your views here.

class SystemsList(drfme_generics.ListCreateAPIView):
    
    serializer_class = SuperIntegrationSerializer
    
    def get_queryset(self):
        
        status = self.kwargs['status']
        company_id = self.request.user.get_company()
        print 'co id is ' + str(company_id)
        existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
        if existingIntegration is not None: #assume there's onlg one entry
            if status == 'new':
                queryset = SuperIntegration.objects(code__nin=existingIntegration.integrations.keys())
                for obj in queryset:
                    #company_info = CompanyGenericIntegrationSerializer()
                    obj.company_info = {}
            elif status == 'existing':
                queryset = SuperIntegration.objects(code__in=existingIntegration.integrations.keys())
                for obj in queryset:
                    #company_info = CompanyGenericIntegrationSerializer(existingIntegration.integrations[obj.code])
                    # print "code is " + str(existingIntegration.integrations[obj.code])
                    obj.company_info = existingIntegration.integrations[obj.code]
                    obj.company_info["code"] = obj.code
                    obj.company_info['record_id'] = json.dumps(existingIntegration.id, default=json_util.default)
            return queryset
        # if we are here, there are no records for the company 
        if status == 'new':
            print 'new sttatus'
            queryset_new = SuperIntegration.objects.all()    
        elif status == 'existing':
            queryset_new = None    
        return queryset_new
    
    

# handle initial empty form and posting/saving of form data    
class IntegrationFormView(FormView):
    template_name = 'integrations/new.html'
    form_class = IntegrationBaseForm
    #success_url = reverse_lazy('integrations-list', current_app='superadmin')
    #print "class xxxxx"
    
    
#     def get_form_class(self):
#         code = self.kwargs['code']
#         #print 'code is ' + code
#         formClasses = { "mkto" : MktoForm, "sfdc": SfdcForm, }
#         self.form_class = formClasses[code]
# #         if code == 'mkto':
# #             self.form_class = MktoForm
# #         else:
# #             if code == 'sfdc':
# #                 self.form_class = SfdcForm
#         return FormView.get_form_class(self)
    
#     def get(self, *args, **kwargs):
#         code = kwargs['code']
#         #super(IntegrationFormView, self).__init__(*args, **kwargs)
#         if code == 'mkto':
#             self.form_class = MktoForm
#         print 'in init' + str(code)
         
#     
#     def get(self, request, *args, **kwargs):
#         print "in get"
#         code = self.kwargs['code']
#         if code == 'mkto':
#             form_class = MktoForm
#         else:
#             if code == 'sfdc':
#                 form_class = SfdcForm
#         print 'form class is ' + str(form_class)
#         form = self.get_form(form_class)
#         context = self.get_context_data(**kwargs)
#         context['form'] = form
#         return self.render_to_response(context)
#     
#     def get_context_data(self, **kwargs):
#         print "in context"
#         print self.kwargs['code']
#         context = super(IntegrationFormView, self).get_context_data(**kwargs);
#         code = self.kwargs['code']
#         if code == 'mkto':
#             form_class = MktoForm
#         else:
#             if code == 'sfdc':
#                 form_class = SfdcForm
#         context['form_class'] = form_class
#         return context
    
#     @csrf_exempt 
#     def dispatch(self, *args, **kwargs):
#         return super(MktoFormView, self).dispatch(*args, **kwargs)
# 
    def post(self, request, **kwargs):
        print 'posting'
        #if request.is_ajax():
        #print 'is ajax'
        return self.ajax(request)
        return super(IntegrationFormView, self).post(request, **kwargs)
 
    def ajax(self, request):
        print 'in ajax'
        code = self.kwargs['code']
        #print 'new code is ' + code
        self.form_class = self.get_form_class();
        #print 'class is ' + str(self.form_class)
        form = self.form_class(data=json.loads(request.body))
        if form.is_valid():
            company_id = request.user.get_company()
            existingIntegration = CompanyIntegration.objects(company_id = company_id ).first()
            if existingIntegration is not None:
                if code in existingIntegration.integrations: # record for this system found - update
                    existingDict = existingIntegration.integrations
                    existingDict[code] = form.cleaned_data
                    existingDict[code]['access_token'] = ''
                    CompanyIntegration.objects(company_id = company_id ).update(integrations=existingDict)
                    print "Updated data for " + code
                    return HttpResponse("Updated data for " + code, status=status.HTTP_200_OK)
                else:
                    #existingIntegration.integrations[code] = form.cleaned_data
                    existingDict = existingIntegration.integrations
                    existingDict[code] = form.cleaned_data
                    #existingDict[code] [code]['access_token'] = ''
                    CompanyIntegration.objects(company_id = company_id ).update(integrations=existingDict)
                    return HttpResponse('New integration added to existing data', status=status.HTTP_200_OK)
            companyIntegration = CompanyIntegration()
            companyIntegration.company_id = company_id
            companyIntegration.integrations[code] = form.cleaned_data
            try:
                #print 'saving'
                companyIntegration.save()
                return HttpResponse('New integration added', status=status.HTTP_200_OK)   
            except Exception as e:
                print str(e)
                return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST)
        else:
            response_data = {'errors': form.errors} #, 'success_url': force_text(self.success_url)
            return HttpResponse(json.dumps(response_data), content_type="application/json")
#

# Handle GET and DELETE for a single integration
class SingleIntegration(drfme_generics.RetrieveDestroyAPIView, FormView):
    
    serializer_class = CompanyIntegrationSerializer
    
    def get_queryset(self):
        pass
           
                
    def delete(self, *args, **kwargs):
        
        queryset = CompanyIntegration.objects(id=self.kwargs['id']).first()
        if queryset is not None and self.request.method == 'DELETE':
            try:
                integration_backup = CompanyIntegrationDeleted()
                integration_backup.company_id = queryset.company_id
                integration_backup.integrations[self.kwargs['code']] = queryset.integrations[self.kwargs['code']]
                integration_backup.save()                          
                queryset.integrations.pop(self.kwargs['code']) 
                queryset.save()
            except Exception as e:
                return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST)   
        
        return HttpResponse('Integration for ' +  self.kwargs['code'] + ' deleted', status=status.HTTP_200_OK) 
    
    def get(self, *args, **kwargs):
        template_name = 'integrations/new.html'
        form_class = IntegrationBaseForm

        
        instance = CompanyIntegration.objects(id=self.kwargs['id']).first()
        if instance is not None:
            queryset = instance.integrations[self.kwargs['code']];
            #print 'qset ' + queryset["host"]
            form = IntegrationBaseForm(queryset)
            return render_to_response('integrations/new.html', {'form':form})
        return HttpResponse("No editable record for " + self.kwargs['code'] + " found!", status=status.HTTP_400_BAD_REQUEST)
   
   
   
@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getCount(request, id):
        object = request.GET.get('object')
        try:
            if object == 'lead':
                result = {'count' : Lead.objects(company_id = id).count()}
            elif object == 'campaign': 
                result = {'count' : Campaign.objects(company_id = id).count()}
            else:
                result =  'Nothing to count'
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})   
        

@api_view(['GET'])
@renderer_classes((JSONRenderer,))    
def getTimezones(request, id):
        try:
            result = {'timezones' :pytz.common_timezones}
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({'Error' : str(e)})   
            

class CompaniesViewSet(viewsets.ModelViewSet):  
    
    serializer_class = CompanySerializer
    
    def list(self, request, id=None): 
        try:
            qryset = {'company_id__ne': 0}
            companies = Company.objects(**qryset).all()
            serializedList = CompanySerializer(companies, many=True)
            return Response(serializedList.data)
        except Exception as e:
            return Response(str(e))    
        
class CompanyIntegrationViewSet(viewsets.ModelViewSet):  
    
    serializer_class = CompanyIntegrationSerializer
    
    def list(self, request, id=None): 
        try:
            company = CompanyIntegration.objects(company_id=id).first()
            serializedList = CompanyIntegrationSerializer(company, many=False)
            return Response(serializedList.data)
        except Exception as e:
            return Response(str(e))    
        
class CompanyDataViewSet(viewsets.ModelViewSet):  
    
    serializer_class = CompanyIntegrationSerializer
    
    def list(self, request, id=None, run_type=None): #process initial data extract for a company
        if id==None or run_type== None:
            return HttpResponse('Company and Job Type need to be provided', status=status.HTTP_400_BAD_REQUEST) 
        try:
            sinceDateTime = request.GET.get('start_date')
            print 'start date is ' + sinceDateTime
            print 'run type is ' + run_type
            if sinceDateTime is None:
                return HttpResponse('Start date cannot be empty', status=status.HTTP_400_BAD_REQUEST) 
            companyDataExtract.delay(user_id=request.user.id, company_id=id, run_type='initial', sinceDateTime=sinceDateTime)
            return HttpResponse('Initial data extract for company ' +  id + ' scheduled', status=status.HTTP_200_OK) 
            
        except Exception as e:
            return HttpResponse(str(e), status=status.HTTP_400_BAD_REQUEST) 

