from tastypie.validation import Validation
from mutant.models import ModelDefinition

class TableValidation(Validation):
    def is_valid(self, bundle, request=None):
        if ModelDefinition.objects.filter(name=bundle.data['name']):
            return {'name': u'table with name "%s" already exists' % bundle.data['name']}
        return {}        
