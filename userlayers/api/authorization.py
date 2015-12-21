from django.conf import settings
from django.utils.module_loading import import_by_path
from mutant.models.model import ModelDefinition
from userlayers.models import UserToTable

class FullAccessForLoginedUsers(object):
    def base_check(self, object_list, bundle):
        return hasattr(bundle.request, 'user') and not bundle.request.user.is_anonymous()
    
    def check_list_modify(self, object_list, bundle):
        return object_list if self.base_check(object_list, bundle) else []
    
    def check_list_view(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle)
    
    def check_detail_modify(self, object_list, bundle):
        return self.base_check(object_list, bundle)
    
    def check_detail_view(self, object_list, bundle):
        return self.check_detail_modify(object_list, bundle)
    
    def read_list(self, object_list, bundle):
        return self.check_list_view(object_list, bundle)

    def read_detail(self, object_list, bundle):
        return self.check_detail_view(object_list, bundle)

    def create_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle)

    def create_detail(self, object_list, bundle):
        return self.check_detail_modify(object_list, bundle)

    def update_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle)
    
    def update_detail(self, object_list, bundle):
        return self.check_detail_modify(object_list, bundle)

    def delete_list(self, object_list, bundle):
        return self.check_list_modify(object_list, bundle)

    def delete_detail(self, object_list, bundle):
        return self.check_detail_modify(object_list, bundle)

class TableAuthorization(FullAccessForLoginedUsers):
    def filter_for_user(self, object_list, user):
        if user.is_superuser:
            return object_list
        return object_list.filter(usertotable__in=UserToTable.objects.filter(user=user))
  
    def check_list_modify(self, object_list, bundle):
        if not super(TableAuthorization, self).check_list_modify(object_list, bundle):
            return []
        return self.filter_for_user(object_list, bundle.request.user)
  
    def check_detail_modify(self, object_list, bundle):
        return bundle.obj in self.check_list_modify(object_list, bundle)
    
    def create_detail(self, object_list, bundle):
        return self.base_check(object_list, bundle)

def get_table_auth():
    custom_table_auth = getattr(settings, 'USERLAYERS_TABLE_AUTHORIZATION', None)
 
    if custom_table_auth:
        return import_by_path(custom_table_auth)
    
    return TableAuthorization

def get_field_auth():
    class FieldAuthorization(get_table_auth()):
        def filter_for_user(self, object_list, user):
            md_list = super(FieldAuthorization, self).filter_for_user(ModelDefinition.objects.all(), user)
            return object_list.filter(model_def__in=md_list)
    return FieldAuthorization

def get_table_data_auth():
    class TableDataAuthorization(get_table_auth()):
        def filter_for_user(self, object_list, user):
            if not object_list:
                return object_list
            md = ModelDefinition.objects.filter(pk=type(object_list[0]).definition().pk)
            if super(TableDataAuthorization, self).filter_for_user(md, user):
                return object_list
            else:
                return []
    return TableDataAuthorization
