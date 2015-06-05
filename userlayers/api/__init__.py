from tastypie.api import Api
from .resources import TablesResource, FieldsResource

v1_api = Api(api_name='v1')
v1_api.register(TablesResource())
v1_api.register(FieldsResource())
