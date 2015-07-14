import mutant

from django.conf.urls import url
from django.core.urlresolvers import reverse
from tastypie.resources import Resource
from tastypie.contrib.gis.resources import ModelResource
from tastypie import fields, http
from tastypie.bundle import Bundle
from tastypie.authorization import DjangoAuthorization, Authorization
from tastypie.utils import trailing_slash
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
        authorization = Authorization()
        fields = ['name']
    
    def hydrate(self, bundle):
        bundle = super(FieldsResource, self).hydrate(bundle)
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
        authorization = Authorization()
        fields = ['name']
        
    def hydrate(self, bundle):
        bundle.obj.app_label = 'dynamic'
        bundle.obj.model = bundle.data['name']
        bundle.obj.object_name = bundle.data['name']
        return super(TablesResource, self).hydrate(bundle)

    def save_m2m(self, bundle):
        for f in bundle.data['fields']:
            f.obj.model_def = bundle.obj
        
        # add geo field
        Model = mutant.contrib.geo.models.GeometryFieldDefinition
        obj = Model(name='geometry', model_def = bundle.obj, null=True, blank=True)
        bundle.data['fields'].append(Bundle(obj=obj))
        
        return super(TablesResource, self).save_m2m(bundle)

class TableProxyResource(Resource):
    pattern = r'^tablesdata/(?P<table_pk>\d+)/data'
    
    class Meta:
        resource_name = 'tablesdata'
    
    def uri_for_table(self, table_pk):
        return reverse('api_dispatch_list', kwargs=dict(table_pk=table_pk, api_name=self._meta.api_name))
    
    def get_resource_uri(self, *args, **kwargs):
        return self.uri_for_table(self.table_pk)
    
    def dispatch(self, request_type, request, **kwargs):
        self.table_pk = kwargs.pop('table_pk')
        try:
            md = ModelDefinition.objects.get(pk=self.table_pk)
        except ModelDefinition.DoesNotExist:
            return http.HttpNotFound()
        
        proxy = self
        
        class R(ModelResource):
            class Meta:
                queryset = md.model_class().objects.all()
                authorization = Authorization()
        
            def get_resource_uri(self, bundle_or_obj=None, **kwargs):
                url = proxy.get_resource_uri()
                if bundle_or_obj:
                    kw = self.resource_uri_kwargs(bundle_or_obj)
                    url += '%s%s' % (kw['pk'], trailing_slash())
                return url
        
        return R().dispatch(request_type, request, **kwargs)
    
    def base_urls(self):
        return [
            url(r"^(?P<resource_name>%s)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"^(?P<resource_name>%s)/schema%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_schema'), name="api_get_schema"),
            
            url(r"%s%s$" % (self.pattern, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"%s/(?P<%s>.*?)%s$" % (self.pattern, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]
