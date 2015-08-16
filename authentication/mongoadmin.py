# mmm/mongoadmin.py

from mongonaut.sites import MongoAdmin

from authentication.models import CustomUser, Company

class UserAdmin(MongoAdmin):
    search_fields = ('first_name', 'last_name', 'email')
    list_fields = ('first_name', 'last_name', 'email')
    
    def has_edit_permission(self, request):
        return request.user.is_superadmin
    
    def has_add_permission(self, request):
        return request.user.is_superadmin

CustomUser.mongoadmin = UserAdmin()

class CompanyAdmin(MongoAdmin):
    search_fields = ('name')
    list_fields = ('name')
    
    def has_edit_permission(self, request):
        return request.user.is_superadmin
    
    def has_add_permission(self, request):
        return request.user.is_superadmin

Company.mongoadmin = UserAdmin()