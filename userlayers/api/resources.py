import os
import json
import mutant
import logging

from django.conf import settings
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse
from django.contrib.gis.geos import GEOSGeometry, WKBWriter
from django.contrib.gis.geos.error import GEOSException
from django.db import transaction
from tastypie.resources import Resource
from tastypie.contrib.gis.resources import ModelResource
from tastypie import fields, http
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from tastypie.exceptions import BadRequest, ImmediateHttpResponse
from mutant.models import ModelDefinition, FieldDefinition
from userlayers.signals import table_created, table_updated
from userlayers.models import UserToTable
from userlayers import DEFAULT_MD_GEOMETRY_FIELD_NAME, DEFAULT_MD_GEOMETRY_FIELD_TYPE
from vectortools.fsutils import TempDir
from vectortools.geojson import convert_to_geojson_data
from vectortools.reader import VectorReaderError
from .validators import FieldValidation
from .serializers import GeoJsonSerializer
from .authorization import FullAccessForLoginedUsers, get_table_auth, get_field_auth, get_table_data_auth
from .forms import TableFromFileForm, FieldForm, FIELD_TYPES, TableForm, GEOMETRY_FIELD_TYPES
from .naming import translit_and_slugify, get_db_table_name, normalize_field_name
from tastypie.validation import FormValidation

from dbtables.apps import DBTablesConfig as tables_app

get_db_table_name = getattr(settings, 'USERLAYERS_DB_TABLE_GENERATOR', get_db_table_name)

logger = logging.getLogger('userlayers.api.schema')

class FieldsResource(ModelResource):
    type = fields.ApiField()
    table = fields.ToOneField('userlayers.api.resources.TablesResource', 'model_def')
    
    class Meta:
        queryset = FieldDefinition.objects.all()
        authorization = get_field_auth()()
        validation = FieldValidation()
        fields = ['name']
    
    def hydrate(self, bundle):
        bundle = super(FieldsResource, self).hydrate(bundle)
        verbose_name = bundle.data['name']
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
        bundle.obj.verbose_name = verbose_name
        return bundle
        
    def dehydrate(self, bundle):
        cls = bundle.obj.content_type.model_class()
        f_type = dict((v,k) for k,v in FIELD_TYPES)[cls]
        bundle.data['type'] = f_type
        return bundle

class TablesResource(ModelResource):
    fields = fields.ToManyField(FieldsResource, 'fielddefinitions', related_name='table', full=True)
    
    class Meta:
        queryset = ModelDefinition.objects.all()
        authorization = get_table_auth()()
        validation = FormValidation(form_class=TableForm)
        fields = ['name']
    
    def fill_obj(self, bundle):
        slug = translit_and_slugify(bundle.data['name'])
        bundle.obj.verbose_name = bundle.data['name']
        bundle.obj.app_label = tables_app.name
        if not bundle.obj.db_table:
            table_name = get_db_table_name(bundle.request.user, bundle.data['name'])[:63]
            bundle.obj.db_table = table_name
            bundle.obj.model = table_name
            bundle.obj.object_name = table_name
        
    def signal_payload(self, bundle):
        uri = self.get_resource_uri(bundle.obj)
        proxy_uri = TableProxyResource().uri_for_table(bundle.obj.pk)
        return dict(sender='api', user=bundle.request.user, md=bundle.obj, uri=uri, proxy_uri=proxy_uri)

    def emit_created_signal(self, bundle):
        table_created.send(**self.signal_payload(bundle))
    
    def emit_updated_signal(self, bundle):
        table_updated.send(**self.signal_payload(bundle))
 
    @transaction.atomic
    def save(self, bundle, *args, **kwargs):
        self.fill_obj(bundle)
        if bundle.obj.pk:
            #hack for renaming
            bundle.obj.model_class(force_create=True)
        return super(TablesResource, self).save(bundle, *args, **kwargs)
    
    def _create_auto_fields(self, bundle):
        Model = dict(GEOMETRY_FIELD_TYPES).get(bundle.data.get('geometry_type'), DEFAULT_MD_GEOMETRY_FIELD_TYPE)
        obj = Model(name=DEFAULT_MD_GEOMETRY_FIELD_NAME, model_def=bundle.obj, null=True, blank=True)
        bundle.data['fields'].append(Bundle(obj=obj))
        
    @transaction.atomic
    def obj_create(self, bundle, **kwargs):
        self._create_auto_fields(bundle)
        bundle = super(TablesResource, self).obj_create(bundle, **kwargs)
        self.emit_created_signal(bundle)
        logger.info('"%s" created table "%s"' % (bundle.request.user, bundle.obj.db_table))
        return bundle

    @transaction.atomic
    def obj_update(self, *args, **kwargs):
        bundle = super(TablesResource, self).obj_update(*args, **kwargs)
        self.emit_updated_signal(bundle)
        logger.info('"%s" updated table "%s"' % (bundle.request.user, bundle.obj.db_table))
        return bundle

    def obj_delete(self, bundle, **kwargs):
        super(TablesResource, self).obj_delete(bundle, **kwargs)
        logger.info('"%s" removed table "%s"' % (bundle.request.user, bundle.obj.db_table))

    def save_m2m(self, bundle):
        #This is only place for create UserToTable entry. Because we need to do it after save MD, but before save m2m (fields),
        #because fields authorization checks UserToTable entry
        UserToTable.objects.get_or_create(md=bundle.obj, user=bundle.request.user)
        
        for f in bundle.data['fields']:
            f.obj.model_def = bundle.obj
        return super(TablesResource, self).save_m2m(bundle)
    
    def dehydrate(self, bundle):
        bundle.data['objects_uri'] = TableProxyResource().uri_for_table(bundle.obj.pk)
        return bundle

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
            md = ModelDefinition.objects.get(pk=self.table_pk)
        except ModelDefinition.DoesNotExist:
            return http.HttpNotFound()
        
        proxy = self
        
        class R(ModelResource):
            logger = logging.getLogger('userlayers.api.data')
            
            class Meta:
                queryset = md.model_class().objects.all()
                authorization = get_table_data_auth(md)()
                serializer = GeoJsonSerializer()
                max_limit = None
        
            def dispatch(self, *args, **kwargs):
                response = super(R, self).dispatch(*args, **kwargs)
                ct = response.get('Content-Type')
                if ct and ct.startswith('application/zip'):
                    response['Content-Disposition'] = 'attachment; filename=%s.zip' % md.name
                return response
        
            def get_resource_uri(self, bundle_or_obj=None, **kwargs):
                url = proxy.get_resource_uri()
                if bundle_or_obj:
                    kw = self.resource_uri_kwargs(bundle_or_obj)
                    url += '%s%s' % (kw['pk'], trailing_slash())
                return url
        
            def serialize(self, request, data, format, options=None):
                options = options or {}
                options['geometry_field'] = DEFAULT_MD_GEOMETRY_FIELD_NAME
                return super(R, self).serialize(request, data, format, options)
            
            def obj_create(self, bundle, **kwargs):
                bundle = super(R, self).obj_create(bundle, **kwargs)
                self.logger.info('"%s" created table data, table "%s", object pk "%s"' % (bundle.request.user, md.db_table, bundle.obj.pk))
                return bundle
            
            def obj_update(self, bundle, **kwargs):
                bundle = super(R, self).obj_update(bundle, **kwargs)
                self.logger.info('"%s" updated table data, table "%s", object pk "%s"' % (bundle.request.user, md.db_table, bundle.obj.pk))
                return bundle
            
            def obj_delete(self, bundle, **kwargs):
                super(R, self).obj_delete(bundle, **kwargs)
                self.logger.info('"%s" deleted table data, table "%s", object pk "%s"' % (bundle.request.user, md.db_table, bundle.obj.pk))
        
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

    def get_geometry_type(self, geojson_data):
        type_map = {
            'Point': 'point',
            'MultiPoint': 'multi_point',
            'LineString': 'line_string',
            'MultiLineString': 'multi_line_string',
            'Polygon': 'polygon',
            'MultiPolygon': 'multi_polygon',
            'GeometryCollection': 'geometry_collection',
        }
        types = []
        for f in geojson_data['features']:
            t = f['geometry']['type']
            if t not in types:
                types.append(t)
        if len(types) == 1:
            geom_type = type_map.get(types[0])
        else:
            geom_type = 'geometry'
        
        return geom_type

    def create_table(self, request, name, geojson_data):
        tr = TablesResource()
        feature = geojson_data['features'][0]
        props = feature['properties']
        geom_type = self.get_geometry_type(geojson_data)
        fields = []
        for k, v in props.iteritems():
            if isinstance(v, (int, long)):
                ftype = 'integer'
            elif isinstance(v, (float)):
                ftype = 'float'
            else:
                ftype = 'text'
            fields.append({'name': k, 'type': ftype,})
        bundle = tr.build_bundle(request=request, data=dict(name=name, geometry_type=geom_type, fields=fields))
        return tr.obj_create(bundle)

    def fill_table(self, model_class, geojson_data):
        objects = []
        for f in geojson_data['features']:
            for k in f['properties'].keys():
                if normalize_field_name(k) != k:
                    f['properties'][normalize_field_name(k)] = f['properties'].pop(k)
            obj = model_class(**f['properties'])
            if f['geometry']:
                try:
                    obj.geometry = GEOSGeometry(json.dumps(f['geometry']))
                except GEOSException:
                    raise FileImportError(u'file contains wrong geometry')
                if obj.geometry.hasz:
                    #force 3D to 2D geometry convertation
                    obj.geometry = WKBWriter().write(obj.geometry)
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
            not_empty_layers = [l for l in geojson_data if len(l['features'])]
            if not not_empty_layers:
                raise FileImportError(u'file does not contain any features')
            geojson_data = not_empty_layers[0]
        except VectorReaderError:
            raise FileImportError(u'wrong file format')
        bundle = self.create_table(request, name, geojson_data)
        self.fill_table(bundle.obj.model_ct.model_class(), geojson_data)
        return bundle

    @transaction.atomic
    def post_list(self, request, **kwargs):
        form = TableFromFileForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ImmediateHttpResponse(response=self.error_response(request, form.errors))
        try:
            bundle = self.process_file(request, form.cleaned_data['name'], form.cleaned_data['file'])
        except FileImportError as e:
            raise ImmediateHttpResponse(response=self.error_response(request, {'file': [e.message]}))
        location = TablesResource().get_resource_uri(bundle)
        return http.HttpCreated(location=location)
