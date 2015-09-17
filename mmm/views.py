from __future__ import absolute_import
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
import pytz, string, unicodedata, nltk
from django.utils import timezone
from datetime import timedelta, date, datetime
from itertools import tee, izip, islice
from nltk import bigrams
from operator import itemgetter
from tempfile import NamedTemporaryFile
import csv
import time
import os

from rest_framework import status, views, permissions, viewsets
from subprocess import PIPE, STDOUT, Popen, call
from django.core.files import File
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from rest_framework.response import Response
from mmm.celery import app
from celery import task
from mongoengine.queryset.visitor import Q
from bson import ObjectId

from company.models import TempData, TempDataDelta
from nltk.parse.pchart import ProbabilisticBottomUpInitRule
from rest_framework.decorators import renderer_classes

from collab.signals import send_notification
from collab.models import Notification 
from mmm.models import ExportFile
from mmm.serializers import ExportFilesSerializer


class IndexView(TemplateView):
    template_name = 'index.html'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(IndexView, self).dispatch(*args, **kwargs)

class TimezoneMiddleware(object):
    def process_request(self, request):
        tzname = request.session.get('django_timezone')
        if tzname:
            #pass
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()
            
def _str_from_date(dateTime, format=None): # returns a timezone like string from a datetime object
    
    if format == 'short': # short format of date string found in Mkto created date
        return datetime.strftime(dateTime, '%Y-%m-%d')
    elif format == 'short_with_time':
        return datetime.strftime(dateTime, '%Y-%m-%d %H:%M:%S')
    else:
        return datetime.strftime(dateTime, '%Y-%m-%dT%H:%M:%SZ') # found in status record

def _date_from_str(dateString, format=None): # returns a datetime object from a timezone like string 
    
    if format == 'short': 
        return datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
    else:
        if dateString.find('+0000') != -1: #account for weird formats
            return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:%S.000+0000') 
        else:
            return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:%SZ') # found in status record
            
# called by Tasks to save temp data from source systems for initial runs        
def saveTempData(company_id=None, record_type=None, source_system=None, source_record=None, job_id=None):
    try:
        tempData = TempData(company_id=company_id, record_type=record_type, source_system=source_system, source_record=source_record, updated_date=datetime.utcnow(), job_id=job_id)
        tempData.save()   
    except Exception as e:
        print 'exception while saving: ' + str(e)

# called by Tasks to save temp data from source systems for delta runs        
def saveTempDataDelta(company_id=None, record_type=None, source_system=None, source_record=None, job_id=None):
    try:
        tempDataDelta = TempDataDelta(company_id=company_id, record_type=record_type, source_system=source_system, source_record=source_record, updated_date=datetime.utcnow(), job_id=job_id)
        tempDataDelta.save()   
    except Exception as e:
        print 'exception while saving: ' + str(e)
        
# called by Tasks to save temp data from source systems for initial runs        
def saveTempDataInBulk(company_id=None, record_type=None, source_system=None, source_record=None, job_id=None):
    try:
        tempData = TempData(company_id=company_id, record_type=record_type, source_system=source_system, source_record=source_record, updated_date=datetime.utcnow(), job_id=job_id)
        tempData.save()   
    except Exception as e:
        print 'exception while saving: ' + str(e)
# name parsing for matching algorithm
#@api_view(['GET'])
def parseName(name=None):
#     if name is not None:
#         print ' in parse with name ' + name.encode('utf-8')
    original_name = name
    if name is None:
        return None
    
    #replace punctuation with whitespace
    replace_punctuation = string.maketrans(string.punctuation, ' '*len(string.punctuation))
    name = name.encode('utf-8').translate(replace_punctuation)
    
    #convert name to lowercase after decoding it for UTF-8
    name = name.decode('UTF-8').lower()
    
    #replace multiple whitespaces with one
    name = " ".join(name.split())
    
    #remove special characters
    nkfd_form = unicodedata.normalize('NFKD', unicode(name))
    name = u"".join([c for c in nkfd_form if not unicodedata.combining(c)])
    
    #remove legal entity forms from the end of the name
    entities = ('inc', 'inc.', 'corp', 'corp.', 'llc', 'llc.', 'ltd', 'ltd.', 'limited')
    
    if name.endswith(entities):
        for entity in entities:
            if name.endswith(entity):
                name = name[:-len(entity)]
                break
            
    #print 'original name ' + original_name + ' was transformed to ' + name
    return name

#compare the length of 2 strings with the Jaccard similarity floor value to see if they should be compared    
def checkJaccardSimilarity(names):
    jaccSimilarity = 0.5
    s = names[0]
    t = names[1]
    print 'checking against name ' + t
    maxLength = float(len(s)) / jaccSimilarity
    if len(t) > maxLength:
        print 'max length reached ' + str(maxLength)
        return False
    return True

#compute the Jaccard similarity index
def computeJaccardIndex(names):
    s = set(names[0])
    t = set(names[1])
    
    n = len(s.intersection(t))
    return n / float(len(s) + len(t) - n)
    
# names matching for matching algorithm
#@api_view(['GET'])
def matchNames(names): #names is a list consisting of two names
    
    prob = 0
    names_bigrams = []
    for name in names:
        words_bigram = [name[i:i+2] for i in range(len(name)-1)]
        names_bigrams.append(words_bigram)
        print 'bigram is ' + str(words_bigram)
    #now that we have the 2 sets with bigrams, compute the Jaccard index
    prob = computeJaccardIndex(names_bigrams)
    print 'j index is ' + str(prob)
    return prob

def _get_entity_fieldname(entry=None, object_type=None): #gets the name of each account or company; needed because the structures of account and company are different
    if object_type == 'account':
        return getattr(entry, 'source_name')
    elif object_type == 'company':
        return entry['_id']
    else:
        return None
    
def _create_parsed_name(entry=None, object_type=None): #creates the parsed name of each account or company; needed because the structures of account and company are different
    if object_type == 'account':
        entry.parsed_name = parseName(_get_entity_fieldname(entry, object_type))
    elif object_type == 'company':
        entry['parsed_name'] = parseName(_get_entity_fieldname(entry, object_type))
    else:
        return None
    return entry

def _get_parsed_name(entry=None, object_type=None): #gets the parsed name of each account or company; needed because the structures of account and company are different
    if object_type == 'account':
        return entry.parsed_name 
    elif object_type == 'company':
        return entry['parsed_name'] 
    else:
        return None
    
    
def matchingAlgo(request, search_name=None,  entries=None, object_type=None): #entries is unsorted by length of name 
    try:
        results = [] 
        name1 = parseName(search_name)
        doJaccardian = True
        
        field_map = {'account': 'source_name', 'company': '_id'}
        
        #uncomment if length of name is to be used as cutoff
        #for entry in entries:
        #    _create_parsed_name(entry, object_type)
        
        #entries.sort(key=lambda x:len(_get_entity_fieldname(entry, object_type)), reverse=False)
       
        
        for entry in entries:
            #name2 = _get_parsed_name(entry, object_type) #uncomment if length of name is being used as a limit
            name2 = parseName(_get_entity_fieldname(entry, object_type))
            if name2 is None:
                continue
            # start by checking if the strings are identical or if the search term is contained within the account name
            if name1 == name2 or name1 in name2:
                print 'adding name 2 ' + name2
                results.append(entry)
            else: #elif doJaccardian: #go hunting for a Jaccardian match
                names = []
                names.append(name1)
                names.append(name2)
                #if checkJaccardSimilarity(names): #uncomment if length of name is being used as a limit
                if matchNames(names=names) > 0.5:
                    print 'adding jacardian name 2 ' + name2
                    results.append(entry)
                #else: #hit the Jaccardian Similarilty floor on string length #uncomment if length of name is being used as a limit
                #    doJaccardian = False
            
        return results
    except Exception as e:
        print 'exception was ' + str(e)
        return str(e)
    

def replace_dots(obj):
    #print 'object is ' + str(obj)
    if isinstance(obj, list):
        for i in range(len(obj)):
            for key in obj[i].keys():
                new_key = key.replace(".", "~")
                if new_key != key:
                    obj[i][new_key] = obj[i][key]
                    del obj[i][key]
    else:
        for key in obj.keys():
            new_key = key.replace(".", "~")
            if new_key != key:
                obj[new_key] = obj[key]
                del obj[key]
    return obj

class ExportView(views.APIView):
    
    def get(self, request, type=None):
        #set the renderer class
        #renderer_classes = (PDFRenderer, )
        #get URL parameters
        object = request.GET.get('object', None)
        id = request.GET.get('id', None)
        company = request.GET.get('company', None)
        if object is None or id is None or company is None:
            return
        #get cookie
        cookies = request.COOKIES
        token = cookies['csrftoken']
        sessionid = cookies['sessionid']
        authenticatedAccount = cookies['authenticatedAccount']
        #set up variables
        file_name = '/tmp/test.pdf'
        phantomjs_script = '/var/www/webapps/3m/mmm/staticfiles/javascripts/common/services/generate_pdf.js' 
        url = ''
        if object == 'binder':
            url = 'http://app.claritix.io/pdf/binder/' + str(id)
            
 
        output = NamedTemporaryFile(delete=False)
        error = NamedTemporaryFile(delete=False)
        
        try:
            external_process = Popen(["phantomjs", phantomjs_script, url, token, sessionid, authenticatedAccount, file_name], stdout=output, stderr=error)
            external_process.communicate()
        except Exception as e:
            print 'exception was ' + str(e)
            return str(e)
        
        file_data = open(file_name, 'rb').read()
        response = HttpResponse(file_data, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=binder_pdf.pdf'
        return response

@app.task
def exportToCsv(object_type, system_code, data, chart_name, user_id, company_id):
    if object_type is None or system_code is None or data is None:
        return 
    try:
        if object_type == 'lead':
            result = exportLeadsToCsv(system_code, data, chart_name, user_id, company_id)
            print 'got result ' + str(result)
            file_name = result['file_name']
            content_type = result['content_type']
            export_file = open(file_name, 'rb')
            exportFile = ExportFile(company_id=company_id, owner_id=user_id, source=chart_name, type=content_type, file_name=os.path.basename(file_name))
            exportFile.file.put(export_file, content_type=content_type)
            exportFile.save()
            try:
                message = 'CSV file successfully exported'
                notification = Notification()
                #notification.company_id = company_id
                notification.owner = user_id
                notification.module = 'Exports'
                notification.type = 'Background task' 
                notification.method = os.path.basename(__file__)
                notification.message = message
                notification.success = True
                notification.read = False
                notification.save()
            except Exception as e:
                send_notification(dict(
                     type='error',
                     success=False,
                     message=str(e)
                    ))          
        else:
            return
    except Exception as e:
        print 'exception while trying to save CSV file: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e)))        

       
def exportLeadsToCsv(system_code, data, chart_name, user_id, company_id):
    if system_code == 'hspt':
        result = exportHsptLeadsToCsv(data, chart_name, user_id, company_id)
    else:
        return 
    return result
 
      
def exportHsptLeadsToCsv(data, chart_name, user_id, company_id):
    
    leads = data.get('results', None) #because this is being sent from the Lead drilldown view
    portal_id = data.get('portal_id', None)
    if leads is None or portal_id is None:
        return
    try:
        #open a temp file for writing
        end_date_string = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime())
        base_file_name = end_date_string + '_' + chart_name + '_leads' + '_cx.csv'
        file_name = '/tmp/' +  base_file_name
        csv_out = open(file_name, 'wb')
        fieldnames = ['Hubspot ID', 'First Name', 'Last Name', 'Email', 'City', 'Country', 'Current Stage', 'Source', 'Subscriber Date', 'Lead Date', 'MQL Date', 'SQL Date', 'Opportunity Date', 
                      'Customer Date', 'First Visit Date', 'Last Visit Date', 'First Form', 'First Form Date', 'Recent Form', 'Recent Form Date',  ]
        
        #create writer
        csv_writer = csv.DictWriter(csv_out, fieldnames=fieldnames, restval='', extrasaction='ignore')
        csv_writer.writeheader()
        
        for lead in leads:
            subscriber_date = lead_date = mql_date = sql_date = opp_date = customer_date = first_visit_date = last_visit_date = first_conversion_date = recent_conversion_date = ''
            
            hspt_id_url = "http://app.hubspot.com/contacts/" + str(portal_id) + "/contact/" +  str(lead['hspt_id']) 
            hspt_id = '=HYPERLINK("' + hspt_id_url + '", "' + str(lead['hspt_id']) + '")'
            if 'hspt_subscriber_date' in lead and lead['hspt_subscriber_date'] is not None:
                subscriber_date = datetime.strftime(lead['hspt_subscriber_date'], '%Y-%m-%d %H:%M:%S')
            if 'hspt_lead_date' in lead and lead['hspt_lead_date'] is not None:
                lead_date = datetime.strftime(lead['hspt_lead_date'], '%Y-%m-%d %H:%M:%S')
            if 'hspt_mql_date' in lead and lead['hspt_mql_date'] is not None:
                mql_date = datetime.strftime(lead['hspt_mql_date'], '%Y-%m-%d %H:%M:%S')
            if 'hspt_sql_date' in lead and lead['hspt_sql_date'] is not None:
                sql_date = datetime.strftime(lead['hspt_sql_date'], '%Y-%m-%d %H:%M:%S')
            if 'hspt_opp_date' in lead and lead['hspt_opp_date'] is not None:    
                opp_date = datetime.strftime(lead['hspt_opp_date'], '%Y-%m-%d %H:%M:%S')
            if 'hspt_customer_date' in lead and lead['hspt_customer_date'] is not None:    
                customer_date = datetime.strftime(lead['hspt_customer_date'], '%Y-%m-%d %H:%M:%S')
            if lead['leads']['hspt']['properties'].get('hs_analytics_first_visit_timestamp', '')  != '':
                first_visit_date = datetime.strftime(lead['leads']['hspt']['properties'].get('hs_analytics_first_visit_timestamp', ''), '%Y-%m-%d %H:%M:%S')
            if lead['leads']['hspt']['properties'].get('hs_analytics_last_visit_timestamp', '')  != '':
                last_visit_date = datetime.strftime(lead['leads']['hspt']['properties'].get('hs_analytics_last_visit_timestamp', ''), '%Y-%m-%d %H:%M:%S')
            if lead['leads']['hspt']['properties'].get('first_conversion_date', '')  != '':
                first_conversion_date = datetime.strftime(lead['leads']['hspt']['properties'].get('first_conversion_date', ''), '%Y-%m-%d %H:%M:%S')
            if lead['leads']['hspt']['properties'].get('recent_conversion_date', '')  != '':
                recent_conversion_date = datetime.strftime(lead['leads']['hspt']['properties'].get('recent_conversion_date', ''), '%Y-%m-%d %H:%M:%S')
            
            csv_writer.writerow({'Hubspot ID' : hspt_id, 'First Name': lead['source_first_name'].encode('utf-8'), 'Last Name': lead['source_last_name'].encode('utf-8'), 'Email': lead['source_email'].encode('utf-8'), 'Country': lead['leads']['hspt']['properties'].get('country', '').encode('utf-8'), 
                                 'City': lead['leads']['hspt']['properties'].get('city', '').encode('utf-8'), 'Current Stage': lead['source_stage'].encode('utf-8'),
                                 'Source': lead['source_source'], 'Subscriber Date': subscriber_date, 'Lead Date': lead_date,
                                 'MQL Date': mql_date, 'SQL Date': sql_date, 'Opportunity Date': opp_date,
                                 'Customer Date': customer_date, 'First Visit Date': first_visit_date, 
                                 'Last Visit Date': last_visit_date, 'First Form': lead['leads']['hspt']['properties'].get('first_conversion_event_name', '').encode('utf-8'),
                                 'First Form Date': first_conversion_date, 'Recent Form': lead['leads']['hspt']['properties'].get('recent_conversion_event_name', '').encode('utf-8'),
                                 'Recent Form Date': recent_conversion_date})
        
        csv_out.close()
        try:
            message = 'CSV file successfully exported'
            notification = Notification()
            #notification.company_id = company_id
            notification.owner = user_id
            notification.module = 'Exports'
            notification.type = 'Background task' 
            notification.method = os.path.basename(__file__)
            notification.message = message
            notification.success = True
            notification.read = False
            notification.save()
        except Exception as e:
            send_notification(dict(
                 type='error',
                 success=False,
                 message=str(e)
                ))          
        return {'file_name': file_name, 'content_type' : 'text/csv'}
    except Exception as e:
        print 'exception while trying to create CSV file: ' + str(e)
        send_notification(dict(type='error', success=False, message=str(e))) 
        
class ManageExports(viewsets.ModelViewSet):  
    
    serializer_class = ExportFilesSerializer
        
    def list(self, request):
        try:
            user_id = request.user.id  
            results = ExportFile.objects(owner_id=user_id).exclude("file")
            count = results.count()
            serializedList = ExportFilesSerializer(results, many=True)
            return JsonResponse({'results' : serializedList.data, 'count': count})
        except Exception as e:
                return Response(str(e))    
            
class SingleExport(viewsets.ModelViewSet):  
    
    serializer_class = ExportFilesSerializer
        
    def list(self, request, file_id):
        try:
            user_id = request.user.id  
            result = ExportFile.objects(Q(owner_id=user_id) & Q(id=ObjectId(file_id))).first()
            if result is None:
                return JsonResponse({'Error' : 'File not found to download'})
            export_file = result.file
            chunk_size = 8192
            response = StreamingHttpResponse(FileWrapper(export_file, chunk_size), content_type=result['type'])
            response['Content-Disposition'] = "attachment; filename=%s" % os.path.basename(result['file_name'])
            return response
        except Exception as e:
                return Response(str(e))    
            
    