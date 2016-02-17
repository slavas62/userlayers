import json
from django.contrib.auth import get_user_model
from tastypie.test import ResourceTestCase
from userlayers.api.resources import TablesResource, FieldsResource

class TableMixin(object):
    uri = TablesResource().get_resource_uri()
    
    def create_user_and_login(self, username='user'):
        credentials = dict(username=username, password='password')
        get_user_model().objects.create_user(**credentials)
        self.api_client.client.login(**credentials)

    def create_table(self):
        payload = {"name": "foo", "fields": [{"name": "display_name", "type": "text"}, {"name": "value", "type": "integer"}, {"name": "is_ok", "type": "boolean"}]}
        resp = self.api_client.post(self.uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        return resp.get('Location')
    
    def get_object_uri(self):
        resp = self.api_client.get(self.create_table())
        data = self.deserialize(resp)
        objects_uri = data['objects_uri']
        payload = {'name': 'foo', 'value': 5, 'is_ok': True}
        resp = self.api_client.post(objects_uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        location = resp.get('Location')
        return location
    
    def setUp(self):
        super(TableMixin, self).setUp()
        self.create_user_and_login()

class TableApiTests(TableMixin, ResourceTestCase):
    
    def test_create_delete_table(self):
        location = self.create_table()
        self.assertValidJSONResponse(self.api_client.get(location))
        self.api_client.delete(location)
        self.assertHttpNotFound(self.api_client.get(location))

    def test_get_table_list(self):
        self.assertValidJSONResponse(self.api_client.get(self.uri))

class FieldApiTests(TableMixin, ResourceTestCase):
     
    fields_uri = FieldsResource().get_resource_uri()

    def add_field(self):
        table = self.create_table()
        payload = {'name': 'somefield', 'type': 'text', 'table': table}
        resp = self.api_client.post(self.fields_uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        location = resp.get('Location')
        return location
 
    def test_create_delete_field(self):
        location = self.add_field()
        resp = self.api_client.delete(location)
        self.assertHttpNotFound(self.api_client.get(location))

    def test_rename_field(self):
        location = self.add_field()
        newfieldname = 'newfieldname'
        payload = {'name': newfieldname}
        resp = self.api_client.patch(location, data=payload)
        self.assertIn(resp.status_code, [202, 204])
        resp = self.api_client.get(location)
        self.assertValidJSONResponse(resp)
        self.assertEqual(newfieldname, json.loads(resp.content).get('name'))

class TableDataTests(TableMixin, ResourceTestCase):
    
    def test_create_delete_entry(self):
        location = self.get_object_uri()
        self.api_client.delete(location)
        self.assertHttpNotFound(self.api_client.get(location))

    def test_shapefile_export(self):
        location = self.get_object_uri()
        resp = self.api_client.get(location, data={'format': 'shapefile'})
        self.assertHttpOK(resp)
        self.assertTrue('application/zip' in resp.get('Content-Type'))

class AuthorizationTests(TableMixin, ResourceTestCase):
    def test_table_access(self):
        location = self.create_table()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))
        
    def test_table_data_access(self):
        location = self.get_object_uri()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))
