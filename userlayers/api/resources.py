import os
import json
import mutant

from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from tastypie.resources import Resource
from tastypie.contrib.gis.resources import ModelResource
from tastypie import fields, http
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from tastypie.exceptions import BadRequest, ImmediateHttpResponse
from mutant.models import ModelDefinition, FieldDefinition
from userlayers.signals import table_created
from userlayers.models import UserToTable
from vectortools.fsutils import TempDir
from vectortools.geojson import convert_to_geojson_data
from vectortools.reader import VectorReaderError
from .validators import TableValidation
from .serializers import GeoJsonSerializer
from .authorization import FullAccessForLoginedUsers, TableAuthorization, FieldAuthorization
from .forms import TableFromFileForm, FieldForm, FIELD_TYPES

class FieldsResource(ModelResource):
    type = fields.ApiField()
    
    class Meta:
        queryset = FieldDefinition.objects.all()
        authorization = FieldAuthorization()
        fields = ['name']
    
    def hydrate(self, bundle):
        bundle = super(FieldsResource, self).hydrate(bundle)
        form = FieldForm(bundle.data)
        if not form.is_valid():
            raise ImmediateHttpResponse(response=self.error_response(bundle.request, form.errors))
        bundle.data = form.cleaned_data
        model = dict(FIELD_TYPES)[bundle.data['type']]
        if not isinstance(bundle.obj, model):
            self._meta.object_class = model
            bundle.obj = model()
        bundle.obj.null = True
        bundle.obj.blank = True
        return bundle
        
    def dehydrate(self, bundle):
        cls = bundle.obj.content_type.model_class()
        if cls == mutant.contrib.geo.models.GeometryFieldDefinition:
            f_type = 'geometry'
        else:
            f_type = dict((v,k) for k,v in FIELD_TYPES)[cls]
        bundle.data['type'] = f_type
        return bundle

class TablesResource(ModelResource):
    fields = fields.ToManyField(FieldsResource, 'fielddefinitions', full=True)
    
    class Meta:
        queryset = ModelDefinition.objects.all()
        validation = TableValidation()
        authorization = TableAuthorization()
        fields = ['name']
        
    def hydrate(self, bundle):
        bundle.obj.app_label = 'dynamic'
        bundle.obj.model = bundle.data['name']
        bundle.obj.object_name = bundle.data['name']
        return super(TablesResource, self).hydrate(bundle)

    def emit_created_signal(self, bundle):
        uri = self.get_resource_uri(bundle.obj)
        proxy_uri = TableProxyResource().uri_for_table(bundle.obj.pk)
        table_created.send(sender='api', md=bundle.obj, uri=uri, proxy_uri=proxy_uri)

    @transaction.atomic
    def obj_create(self, bundle, **kwargs):
        bundle = super(TablesResource, self).obj_create(bundle, **kwargs)
        UserToTable(md=bundle.obj, user=bundle.request.user).save()
        self.emit_created_signal(bundle)
        return bundle

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
        authorization = FullAccessForLoginedUsers()
    
    def uri_for_table(self, table_pk):
        return reverse('api_dispatch_list', kwargs=dict(table_pk=table_pk, api_name=self._meta.api_name))
    
    def get_resource_uri(self, *args, **kwargs):
        return self.uri_for_table(self.table_pk)
    
    def dispatch(self, request_type, request, **kwargs):
        self.table_pk = kwargs.pop('table_pk')
        try:
            md = UserToTable.objects.get(md__pk=self.table_pk, user=request.user).md
        except UserToTable.DoesNotExist:
            return http.HttpNotFound()
        
        proxy = self
        
        class R(ModelResource):
            class Meta:
                queryset = md.model_class().objects.all()
                authorization = Authorization()
                serializer = GeoJsonSerializer()
        
            def get_resource_uri(self, bundle_or_obj=None, **kwargs):
                url = proxy.get_resource_uri()
                if bundle_or_obj:
                    kw = self.resource_uri_kwargs(bundle_or_obj)
                    url += '%s%s' % (kw['pk'], trailing_slash())
                return url
        
            def serialize(self, request, data, format, options=None):
                options = options or {}
                options['geojson'] = True
                return super(R, self).serialize(request, data, format, options)
        
        return R().dispatch(request_type, request, **kwargs)
    
    def base_urls(self):
        return [
            url(r"^(?P<resource_name>%s)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"^(?P<resource_name>%s)/schema%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_schema'), name="api_get_schema"),
            
            url(r"%s%s$" % (self.pattern, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"%s/(?P<%s>.*?)%s$" % (self.pattern, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

class FileImportError(Exception):
    pass

class FileImportResource(Resource):
    file = fields.FileField()
    
    class Meta:
        list_allowed_methods = ['post']
        detail_allowed_methods = []
        authorization = FullAccessForLoginedUsers()

    def create_table(self, request, name, geojson_data):
        if not len(geojson_data[0]['features']):
            raise FileImportError(u'file does not contain any features')
        tr = TablesResource()
        props = geojson_data[0]['features'][0]['properties']
        fields = []
        for k, v in props.iteritems():
            fields.append({'name': k, 'type': 'text',})
        bundle = tr.build_bundle(request=request, data=dict(name=name, fields=fields))
        return tr.obj_create(bundle)

    def fill_table(self, model_class, geojson_data):
        objects = []
        for f in geojson_data[0]['features']:
            obj = model_class(**f['properties'])
            obj.geometry = GEOSGeometry(json.dumps(f['geometry']))
            objects.append(obj)
        model_class.objects.bulk_create(objects)

    def process_file(self, request, name, uploaded_file):
        tmp_dir = TempDir()
        dst_file = open(os.path.join(tmp_dir.path, uploaded_file.name), 'w')
        for c in uploaded_file.chunks():
            dst_file.write(c)
        dst_file.close()
        try:
            geojson_data = convert_to_geojson_data(dst_file.name)
        except VectorReaderError:
            raise FileImportError(u'wrong file format')
        bundle = self.create_table(request, name, geojson_data)
        self.fill_table(bundle.obj.model_ct.model_class(), geojson_data)
        return bundle

    def post_list(self, request, **kwargs):
        form = TableFromFileForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ImmediateHttpResponse(response=self.error_response(request, form.errors))
        try:
            bundle = self.process_file(request, form.cleaned_data['name'], form.cleaned_data['file'])
        except FileImportError as e:
            raise ImmediateHttpResponse(response=self.error_response(request, {'file': [e.message]}))
        location = TablesResource().get_resource_uri(bundle)
        return self.create_response(response_class=http.HttpCreated, location=location)
        