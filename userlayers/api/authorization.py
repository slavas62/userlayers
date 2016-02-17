from django.conf import settings
from django.utils.module_loading import import_string
from mutant.models.model import ModelDefinition
from userlayers.models import UserToTable
from mutant.models.field import FieldDefinition

class FullAccessForLoginedUsers(object):
    def base_check(self, object_list, user):
        return not user.is_anonymous()
    
    def check_list_modify(self, object_list, user):
        return object_list if self.base_check(object_list, user) else []
    
    def check_list_view(self, object_list, user):
        return self.check_list_modify(object_list, user)
    
    def check_detail_modify(self, object_list, user):
        return object_list[0] in self.check_list_modify(object_list, user)
    
    def check_detail_view(self, object_list, user):
        return object_list[0] in self.check_list_view(object_list, user)
    
    def read_list(self, object_list, bundle):
        return self.check_list_view(object_list, bundle.request.user)

    def read_detail(self, object_list, bundle):
        return self.check_detail_view([bundle.obj], bundle.request.user)

    def create_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle.request.user)

    def create_detail(self, object_list, bundle):
        return self.check_detail_modify([bundle.obj], bundle.request.user)

    def update_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle.request.user)
    
    def update_detail(self, object_list, bundle):
        return self.check_detail_modify([bundle.obj], bundle.request.user)

    def delete_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle.request.user)

    def delete_detail(self, object_list, bundle):
        return self.check_detail_modify([bundle.obj], bundle.request.user)

class TableAuthorization(FullAccessForLoginedUsers):
    def filter_for_user(self, object_list, user):
        if user.is_superuser:
            return object_list
        return ModelDefinition.objects.filter(pk__in=object_list, usertotable__in=UserToTable.objects.filter(user=user))
  
    def check_list_modify(self, object_list, user):
        if not super(TableAuthorization, self).check_list_modify(object_list, user):
            return []
        return self.filter_for_user(object_list, user)
  
    def create_detail(self, object_list, bundle):
        return self.base_check(object_list, bundle.request.user)
    
    def check_data_view(self, md, user):
        return self.check_detail_view([md], user)
     
    def check_data_modify(self, md, user):
        return self.check_detail_modify([md], user)

def get_table_auth():
    custom_table_auth = getattr(settings, 'USERLAYERS_TABLE_AUTHORIZATION', None)
 
    if custom_table_auth:
        return import_string(custom_table_auth)
    
    return TableAuthorization

def get_field_auth():
    class FieldAuthorization(FullAccessForLoginedUsers):
        def check_table_access(self, operation, object_list, user):
            method = 'check_list_%s' % operation
            md_list = getattr(get_table_auth()(), method)(ModelDefinition.objects.all(), user)
            field_list = [o.pk for o in object_list] if type(object_list) is list else object_list
            return FieldDefinition.objects.select_subclasses().filter(pk__in=field_list, model_def__in=md_list)
        
        def check_list_modify(self, object_list, user):
            return self.check_table_access('modify', object_list, user)
         
        def check_list_view(self, object_list, user):
            return self.check_table_access('view', object_list, user)

        def create_detail(self, object_list, bundle):
            return get_table_auth()().check_detail_modify([bundle.obj.model_def], bundle.request.user)
        
    return FieldAuthorization

def get_table_data_auth(md):
    class TableDataAuthorization(FullAccessForLoginedUsers):
        def check_list_modify(self, object_list, user):
            if get_table_auth()().check_data_modify(md, user):
                return object_list
            else:
                return []
        
        def check_list_view(self, object_list, user):
            if get_table_auth()().check_data_view(md, user):
                return object_list
            else:
                return []
        
    return TableDataAuthorization
