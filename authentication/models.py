from mongoengine.django.auth import User
from mongoengine import *
import datetime

class Company (Document):
    name = StringField(max_length=255)
    company_id = IntField(unique=True)
    weekly_email = BooleanField(default=False)
    meta = {'collection': 'company' }
    def __unicode__(self):
        return self.company_id
    
class CustomUser(User):

    #email_address = EmailField(unique=True)
#  
#     first_name = StringField(max_length=40)
#     last_name = StringField(max_length=40)
    #tagline = StringField(max_length=140)
    timezone = StringField(max_length=140)
 
    is_admin = BooleanField(default=False)
    is_superadmin = BooleanField(default=False)
 
    created_at = DateTimeField(default=datetime.datetime.utcnow())
    updated_at = DateTimeField(default=datetime.datetime.utcnow())
    company = IntField()
    image_url = StringField(max_length=2000)
    #objects = AccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    #meta = {'collection': 'user' } 

    def __unicode__(self):
        return self.username
 
    def get_full_name(self):
        return ' '.join([self.first_name, self.last_name])
 
    def get_short_name(self):
        return self.first_name
     
    #ADDED BY SATYA
#     def __unicode__(self):              # __unicode__ on Python 2
#         return self.email
 
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True
 
    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True
 
     
    #@property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
     
    def get_company(self):
        return self.company #.company_id 
     
    @property
    def company_id(self):
        return self.company #.company_id 
    
    @property
    def company_name(self):
        company = Company.objects(company_id = self.company).first()
        return company['name']
     
    def get_timezone(self):
        return self.timezone