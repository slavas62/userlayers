import os
import json
import mutant
import logging

from django.contrib.gis.gdal import GDALException
from django.forms.models import modelform_factory
from django.conf import settings
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http.response import HttpResponse
from django.contrib.gis.geos import GEOSGeometry, WKBWriter
from django.contrib.gis.geos.error import GEOSException
from django.contrib.contenttypes.fields import GenericRelation
from django.db import transaction
from tastypie.resources import Resource
from tastypie.contrib.gis.resources import ModelResource
from tastypie import fields, http
from tastypie.bundle import Bundle
from tastypie.authorization import Authorization
from tastypie.authentication import SessionAuthentication
from tastypie.serializers import Serializer
from tastypie.utils import trailing_slash
from tastypie.exceptions import BadRequest, ImmediateHttpResponse
from mutant.models import ModelDefinition, FieldDefinition
from mutant.contrib.geo.models.field import GeometryFieldDefinition
from userlayers.signals import table_created, table_updated
from userlayers.models import UserToTable, AttachedFile
from userlayers.settings import DEFAULT_MD_GEOMETRY_FIELD_NAME, DEFAULT_MD_GEOMETRY_FIELD_TYPE
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
        queryset = FieldDefinition.objects.select_subclasses()
        authorization = get_field_auth()()
        authentication = SessionAuthentication()
        validation = FieldValidation()
        fields = ['name']
    
    def hydrate(self, bundle):
        bundle = super(FieldsResource, self).hydrate(bundle)
        verbose_name = bundle.data['name']
        form = FieldForm(bundle.data)
        if not form.is_valid():
            raise ImmediateHttpResponse(response=self.error_response(bundle.request, form.errors))
        bundle.data = form.cleaned_data
        if not bundle.obj.pk:
            model = dict(FIELD_TYPES)[bundle.data['type']]
            if not isinstance(bundle.obj, model):
                self._meta.object_class = model
                bundle.obj = model()
            bundle.obj.null = True
            bundle.obj.blank = True
        bundle.obj.verbose_name = verbose_name
        return bundle
        
    def dehydrate(self, bundle):
        obj = bundle.obj.type_cast()
        f_type = dict((v,k) for k,v in FIELD_TYPES)[type(obj)]
        bundle.data['type'] = f_type
        
        if isinstance(obj, GeometryFieldDefinition):
            bundle.data['is_3d'] = obj.dim == GeometryFieldDefinition.DIM_3D
        return bundle

class TablesResource(ModelResource):
    name = fields.ApiField('verbose_name')
    fields = fields.ToManyField(FieldsResource, 'fielddefinitions', related_name='table', full=True)
    
    class Meta:
        queryset = ModelDefinition.objects.all()
        authorization = get_table_auth()()
        authentication = SessionAuthentication()
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
        FieldModel = dict(GEOMETRY_FIELD_TYPES).get(bundle.data.get('geometry_type'), DEFAULT_MD_GEOMETRY_FIELD_TYPE)
        kwargs = {
            'name': DEFAULT_MD_GEOMETRY_FIELD_NAME,
            'model_def': bundle.obj,
            'null': True,
            'blank': True,
        }
        if bundle.data.get('is_3d'):
            kwargs['dim'] = FieldModel.DIM_3D
        obj = FieldModel(**kwargs)
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
        authentication = SessionAuthentication()

    def uri_for_table(self, table_pk):
        return reverse('api_dispatch_list', kwargs=dict(table_pk=table_pk, api_name=self._meta.api_name))
    
    def uri_for_file_list(self, table_pk, object_pk):
        return reverse('api_dispatch_files_list', kwargs=dict(table_pk=table_pk, api_name=self._meta.api_name, pk=object_pk))
    
    def uri_for_file_detail(self, table_pk, object_pk, file_pk):
        return reverse('api_dispatch_files_detail', kwargs=dict(table_pk=table_pk, api_name=self._meta.api_name, pk=object_pk, file_pk=file_pk))
    
    def get_objects_resource(self, table_pk):
        try:
            md = ModelDefinition.objects.get(pk=table_pk)
        except ModelDefinition.DoesNotExist:
            return http.HttpNotFound()
        
        Model = md.model_class()
        
        GeomModelField = Model._meta.get_field_by_name(DEFAULT_MD_GEOMETRY_FIELD_NAME)[0]
        
        gr = GenericRelation(AttachedFile)
        gr.contribute_to_class(Model, 'files')
        
        proxy = self
        
        class AttachedFilesInlineResource(ModelResource):
            class Meta:
                queryset = AttachedFile.objects.all()
                
            def get_resource_uri(self, bundle):
                kwargs = dict(table_pk=md.pk, object_pk=bundle.obj.object_id, file_pk=bundle.obj.pk)
                return proxy.uri_for_file_detail(**kwargs)
        
        class R(ModelResource):
            logger = logging.getLogger('userlayers.api.data')
            
            class Meta:
                queryset = Model.objects.all()
                authorization = get_table_data_auth(md)()
                serializer = GeoJsonSerializer()
                max_limit = None
                validation = FormValidation(form_class=modelform_factory(md.model_class(), exclude=('id',)))

            def dispatch(self, *args, **kwargs):
                response = super(R, self).dispatch(*args, **kwargs)
                ct = response.get('Content-Type')
                if ct and ct.startswith('application/zip'):
                    response['Content-Disposition'] = 'attachment; filename=%s.zip' % md.name
                return response
        
            def get_model_definition(self):
                return md
        
            def get_resource_uri(self, bundle_or_obj=None, **kwargs):
                url = proxy.uri_for_table(table_pk)
                if bundle_or_obj:
                    kw = self.resource_uri_kwargs(bundle_or_obj)
                    url += '%s%s' % (kw['pk'], trailing_slash())
                return url
        
            def error_response(self, request, errors, response_class=None):
                if isinstance(self._meta.serializer, GeoJsonSerializer):
                    self._meta.serializer = Serializer()
                return super(R, self).error_response(request, errors, response_class=None)
        
            def serialize(self, request, data, format, options=None):
                options = options or {}
                options['geometry_field'] = DEFAULT_MD_GEOMETRY_FIELD_NAME
                return super(R, self).serialize(request, data, format, options)

            def full_hydrate(self, bundle):
                bundle = super(R, self).full_hydrate(bundle)
                try:
                    bundle.data['geometry'] = bundle.obj.geometry
                except GDALException:
                    raise ImmediateHttpResponse(response=self.error_response(bundle.request, {'geometry': 'invalid geometry'}))
                if bundle.obj.geometry and GeomModelField.dim == 3 and not bundle.obj.geometry.hasz:
                    geom_3d = bundle.obj.geometry.ogr
                    geom_3d._set_coord_dim(3)
                    bundle.data['geometry'] = geom_3d.geos
                
                return bundle

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
                
            def dehydrate(self, bundle):
                bundle.data['files_uri'] = proxy.uri_for_file_list(table_pk, bundle.obj.pk)
                return bundle
                
        return R
    
    def dispatch(self, request_type, request, **kwargs):
        R = self.get_objects_resource(table_pk=kwargs.get('table_pk'))
        return R().dispatch(request_type, request, **kwargs)
    
    def dispatch_files_list(self, request, **kwargs):
        return self.dispatch_files('list', request, **kwargs)
    
    def dispatch_files_detail(self, request, **kwargs):
        return self.dispatch_files('detail', request, **kwargs)
    
    def dispatch_files(self, request_type, request, **kwargs):
        obj_res = self.get_objects_resource(table_pk=kwargs.get('table_pk'))()
        obj_bundle = obj_res.build_bundle(request=request)
        try:
            obj = obj_res.cached_obj_get(bundle=obj_bundle, **kwargs)
        except ObjectDoesNotExist:
            return http.HttpNotFound()
        except MultipleObjectsReturned:
            return http.HttpMultipleChoices("More than one resource is found at this URI.")
        
        proxy = self
        md = obj_res.get_model_definition()
        
        class R(ModelResource):
            
            class Meta:
                queryset = AttachedFile.objects.filter(content_type=md, object_id=obj.pk)
                fields = ['id', 'file']
                list_allowed_methods = ['get', 'post', 'delete']
                detail_allowed_methods = ['get', 'delete']
                authorization = Authorization()
                
            def get_resource_uri(self, bundle_or_obj=None, **kwargs):
                kwargs = dict(table_pk=md.pk, object_pk=obj.pk)
                
                if bundle_or_obj:
                    kwargs['file_pk'] = self.detail_uri_kwargs(bundle_or_obj).get('pk')
                    return proxy.uri_for_file_detail(**kwargs)
                else:
                    return proxy.uri_for_file_list(**kwargs)
                
            def authorized_create_detail(self, object_list, bundle):
                if obj_res.authorized_update_detail([obj], obj_bundle):
                    return object_list
                return []
            
            def authorized_delete_detail(self, object_list, bundle):
                return self.authorized_create_detail(object_list, bundle)
                
            def deserialize(self, request, data, format=None):
                return request.FILES
            
            def hydrate(self, bundle):
                bundle.obj.content_type = md
                bundle.obj.object_id = obj.pk
                return bundle
                
        return R().dispatch(request_type, request, **{'pk': kwargs.get('file_pk')})
    
    def base_urls(self):
        return [
            url(r"^(?P<resource_name>%s)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('dispatch_list'), name="api_dispatch_list"),
            url(r"^(?P<resource_name>%s)/schema%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_schema'), name="api_get_schema"),

            
            #attached files
            url(r"%s/(?P<%s>.*?)/files/(?P<file_pk>\d+)%s$" % (self.pattern, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('dispatch_files_detail'), name="api_dispatch_files_detail"),
            url(r"%s/(?P<%s>.*?)/files%s$" % (self.pattern, self._meta.detail_uri_name, trailing_slash()), self.wrap_view('dispatch_files_list'), name="api_dispatch_files_list"),
            
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
        authentication = SessionAuthentication()

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
        is_3d = False
        for f in geojson_data['features']:
            geom = GEOSGeometry(json.dumps(f['geometry']))
            t = geom.geom_type
            if t not in types:
                types.append(t)
            if not is_3d and geom.hasz:
                is_3d = True
        if len(types) == 1:
            geom_type = type_map.get(types[0])
        else:
            geom_type = 'geometry'
        
        return geom_type, is_3d

    def create_table(self, request, name, geojson_data):
        tr = TablesResource()
        feature = geojson_data['features'][0]
        props = feature['properties']
        geom_type, is_3d = self.get_geometry_type(geojson_data)
        fields = []
        for k, v in props.iteritems():
            if isinstance(v, (int, long)):
                ftype = 'integer'
            elif isinstance(v, (float)):
                ftype = 'float'
            else:
                ftype = 'text'
            fields.append({'name': k, 'type': ftype,})
        bundle = tr.build_bundle(request=request, data=dict(name=name, geometry_type=geom_type, is_3d=is_3d, fields=fields))
        return tr.obj_create(bundle)

    def fill_table(self, model_class, geojson_data):
        objects = []
        field_name_map = {}
        for f in geojson_data['features']:
            for k in f['properties'].keys():
                if k not in field_name_map:
                    field_name_map[k] = normalize_field_name(k)
                normalized_name = field_name_map[k]
                if normalized_name != k:
                    f['properties'][normalized_name] = f['properties'].pop(k)
            obj = model_class(**f['properties'])
            if f['geometry']:
                try:
                    obj.geometry = GEOSGeometry(json.dumps(f['geometry']))
                except GEOSException:
                    raise FileImportError(u'file contains wrong geometry')
            objects.append(obj)
        model_class.objects.bulk_create(objects)

    def process_file(self, request, name, uploaded_file):
        tmp_dir = TempDir()
        dst_file = open(os.path.join(tmp_dir.path, uploaded_file.name), 'w')
        for c in uploaded_file.chunks():
            dst_file.write(c)
        dst_file.close()
        try:
            geojson_data = convert_to_geojson_data(dst_file.name, unicode_errors='replace')
            not_empty_layers = [l for l in geojson_data if len(l['features'])]
            if not not_empty_layers:
                raise FileImportError(u'file does not contain any features')
            geojson_data = not_empty_layers[0]
            for l in not_empty_layers[1:]:
                geojson_data['features'].extend(l['features'])
        except VectorReaderError:
            raise FileImportError(u'wrong file format')
        bundle = self.create_table(request, name, geojson_data)
        self.fill_table(bundle.obj.model_ct.model_class(), geojson_data)
        return bundle

    @transaction.atomic
    def create_bundle(self, request):
        form = TableFromFileForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ImmediateHttpResponse(response=self.error_response(request, form.errors))
        try:
            bundle = self.process_file(request, form.cleaned_data['name'], form.cleaned_data['file'])
        except FileImportError as e:
            raise ImmediateHttpResponse(response=self.error_response(request, {'file': [e.message]}))
        return bundle

    def post_list(self, request, **kwargs):
        bundle = self.create_bundle(request)
        location = TablesResource().get_resource_uri(bundle)
        return http.HttpCreated(location=location)
