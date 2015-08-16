# mmm/mongoadmin.py

from mongonaut.sites import MongoAdmin

from authentication.models import CustomUser, Company
from accounts.models import SuperAccount

class AccountAdmin(MongoAdmin):
    
    #list_fields = ('names')
    
    def has_edit_permission(self, request):
        return request.user.is_superadmin
    
    def has_add_permission(self, request):
        return request.user.is_superadmin

SuperAccount.mongoadmin = AccountAdmin()