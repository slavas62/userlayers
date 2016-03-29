from tastypie.validation import Validation
from django.core.exceptions import ValidationError

class FieldValidation(Validation):
    def is_valid(self, bundle, request=None):
        if not bundle.obj.pk and hasattr(bundle.obj, 'model_def') and bundle.obj.model_def.fielddefinitions.filter(name=bundle.obj.name):
            return {'name': u'field with name "%s" already exists' % bundle.obj.name}
        return {}


class TableValidation(Validation):
    def is_valid(self, bundle, request=None):
        obj = bundle.obj
        for k, v in bundle.data.items():
            try:
                obj._meta.get_field(k).to_python(v)
            except ValidationError as e:
                message = 'For field \'%s\': ' % k
                return {'error': message + e.message % e.params}
        return {}
