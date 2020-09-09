from tastypie.validation import Validation


class FieldValidation(Validation):
    def is_valid(self, bundle, request=None):
        if not bundle.obj.pk and hasattr(bundle.obj, 'model_def') and bundle.obj.model_def.fielddefinitions.filter(name=bundle.obj.name):
            return {'name': u'field with name "%s" already exists' % bundle.obj.name}
        return {}
