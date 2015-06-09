import mutant

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from mutant.models import ModelDefinition, FieldDefinition

FIELD_TYPES = (
    ('text', mutant.contrib.text.models.TextFieldDefinition),
    ('integer', mutant.contrib.numeric.models.BigIntegerFieldDefinition),
    ('boolean', mutant.contrib.boolean.models.NullBooleanFieldDefinition),
)

class FieldsResource(ModelResource):
    type = fields.ApiField()
    
    class Meta:
        queryset = FieldDefinition.objects.all()
        authorization = DjangoAuthorization()
        fields = ['name']
    
    def build_bundle(self, *args, **kwargs):
        bundle = super(FieldsResource, self).build_bundle(*args, **kwargs)
        model = dict(FIELD_TYPES)[bundle.data['type']]
        if not isinstance(bundle.obj, model):
            self._meta.object_class = model
            bundle.obj = model()
        return bundle
        
    def dehydrate(self, bundle):
        bundle.data['type'] = bundle.obj.content_type.name
        return bundle
    

class TablesResource(ModelResource):
    fields = fields.ToManyField(FieldsResource, 'fielddefinitions', full=True)
    
    class Meta:
        queryset = ModelDefinition.objects.all()
        authorization = DjangoAuthorization()
        fields = ['name']
        
    def hydrate(self, bundle):
        bundle.obj.app_label = 'dynamic'
        bundle.obj.model = bundle.data['name']
        bundle.obj.object_name = bundle.data['name']
        return super(TablesResource, self).hydrate(bundle)

    def save_m2m(self, bundle):
        for f in bundle.data['fields']:
            f.obj.model_def = bundle.obj
        return super(TablesResource, self).save_m2m(bundle)
