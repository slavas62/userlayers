from tastypie.api import Api
from .resources import TablesResource, FieldsResource, TableProxyResource, FileImportResource

v1_api = Api(api_name='v1')
v1_api.register(TablesResource())
v1_api.register(FieldsResource())
v1_api.register(TableProxyResource())
v1_api.register(FileImportResource())
