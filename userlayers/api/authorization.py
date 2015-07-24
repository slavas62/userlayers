from userlayers.models import UserToTable

class FullAccessForLoginedUsers(object):
    def base_check(self, object_list, bundle):
        return hasattr(bundle.request, 'user')
    
    def check_list(self, object_list, bundle):
        return object_list if self.base_check(object_list, bundle) else []
    
    def check_detail(self, object_list, bundle):
        return self.base_check(object_list, bundle)
    
    def read_list(self, object_list, bundle):
        return self.check_list(object_list, bundle)

    def read_detail(self, object_list, bundle):
        return self.check_detail(object_list, bundle)

    def create_list(self, object_list, bundle):
        return self.check_list(object_list, bundle)

    def create_detail(self, object_list, bundle):
        return self.check_detail(object_list, bundle)

    def update_list(self, object_list, bundle):
        return self.check_list(object_list, bundle)
    
    def update_detail(self, object_list, bundle):
        return self.check_detail(object_list, bundle)

    def delete_list(self, object_list, bundle):
        return self.check_list(object_list, bundle)

    def delete_detail(self, object_list, bundle):
        return self.check_detail(object_list, bundle)

class TableAuthorization(FullAccessForLoginedUsers):
    def filter_for_user(self, object_list, user):
        return object_list.filter(usertotable__in=UserToTable.objects.filter(user=user))
  
    def check_list(self, object_list, bundle):
        if not super(TableAuthorization, self).check_list(object_list, bundle):
            return []
        return self.filter_for_user(object_list, bundle.request.user)
  
    def check_detail(self, object_list, bundle):
        return bool(self.check_list(object_list, bundle))

class FieldAuthorization(TableAuthorization):
    def filter_for_user(self, object_list, user):
        return object_list.filter(model_def__usertotable__in=UserToTable.objects.filter(user=user))