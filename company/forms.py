from rest_framework_mongoengine import generics as drfme_generics
from django import forms
from mongodbforms import DocumentForm, CharField
from djangular.forms import NgModelFormMixin, NgFormValidationMixin
from djangular.styling.bootstrap3.forms import  Bootstrap3Form

from company.models import BaseCompanyIntegration

from cProfile import label
from djangular.styling.bootstrap3.forms import Bootstrap3ModelForm


# Create your forms here.

class BaseForm(Bootstrap3Form):

    scope_prefix = 'integration'
    form_name='integration_form'
    
    host = forms.URLField(label="Host", required=True)
    client_id = forms.CharField(label="Client ID", required=True)
    client_secret = forms.CharField(label="Client Secret", required=True)
    access_token = forms.CharField(label="reset", required=False, widget=forms.HiddenInput())
    redirect_uri = forms.URLField(label="Redirect URI", required=True)
    
class IntegrationBaseForm(NgModelFormMixin, NgFormValidationMixin, BaseForm):    
    class Meta:
        document = BaseCompanyIntegration

    #from djangular    
    def clean(self):
        return super(IntegrationBaseForm, self).clean()  
    