import json
from django.contrib.auth import get_user_model
from tastypie.test import ResourceTestCase
from userlayers.api.resources import TablesResource, FieldsResource

TABLE_META = {
    'name': 'foo',
    'fields': [
        {
            'name': 'text_field',
            'type': 'text'
        },
        {
            'name': 'integer_field',
            'type': 'integer'
        },
        {
            'name': 'float_field',
            'type': 'float'
        },
        {
            'name': 'boolean_field',
            'type': 'boolean'
        }
    ]
}


class TableMixin(object):
    uri = TablesResource().get_resource_uri()
    
    def create_user_and_login(self, username='user'):
        credentials = dict(username=username, password='password')
        get_user_model().objects.create_user(**credentials)
        self.api_client.client.login(**credentials)

    def create_table(self):
        payload = TABLE_META
        resp = self.api_client.post(self.uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        return resp.get('Location')

    def create_objects_in_table(self, table_uri, values=None):
        """ values must look like
        values = {
            'text_field': ('foo', 'bar'),
            'integer_field': (1, 2),
            'float_field': (1, 1.1),
            'boolean_field': (1, 0)
        }
        """
        payload = {
            'objects': []
        }
        if not values:
            return self.api_client.put(table_uri, data=payload)
        for k, v in values.items():
            for val in v:
                payload['objects'].append(
                    {k: val}
                )
        return self.api_client.put(table_uri, data=payload)

    def get_object_uri(self):
        resp = self.api_client.get(self.create_table())
        data = self.deserialize(resp)
        objects_uri = data['objects_uri']
        payload = {
            'text_field': 'foo',
            'integer_field': 1,
            'float_field': 1.1,
            'boolean_field': True
        }
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
        
    def test_table_rename(self):
        table = self.create_table()
        newtablename = 'newtablename'
        payload = {'name': newtablename}
        resp = self.api_client.patch(table, data=payload)
        self.assertIn(resp.status_code, [202, 204])
        resp = self.api_client.get(table)
        self.assertEqual(newtablename, json.loads(resp.content).get('name'))
    
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
        resp_data = json.loads(resp.content)
        self.assertEqual(newfieldname, resp_data.get('name'))
        resp = self.api_client.get(resp_data['table'])
        self.assertValidJSONResponse(resp)
        
        #ensure that field really renamed within DB. If not then server will generate exception.
        objects_uri = json.loads(resp.content)['objects_uri']
        resp = self.api_client.get(objects_uri)
        self.assertValidJSONResponse(resp)
        

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

    def test_create_entry_with_wrong_values(self):
        resp = self.api_client.get(self.create_table())
        data = self.deserialize(resp)
        table_uri = data['objects_uri']
        payload = {
            'integer_field': ('1.1', 'some text'),
            'float_field': ('some text',)
        }
        resp = self.create_objects_in_table(table_uri, payload)
        self.assertHttpBadRequest(resp)

    def test_create_entry_with_right_values(self):
        resp = self.api_client.get(self.create_table())
        data = self.deserialize(resp)
        table_uri = data['objects_uri']
        payload = {
            'text_field': (1, 1.1, True, False, '', 'some text'),
            'integer_field': (1, 1.1, True, False, '1'),
            'float_field': (1, 1.1, True, False, '1.1'),
            'boolean_field': ('', 'some text', True, False, 123, 0, 1)
        }
        resp = self.create_objects_in_table(table_uri, payload)
        self.assertHttpAccepted(resp)

class AuthorizationTests(TableMixin, ResourceTestCase):
    def test_table_access(self):
        location = self.create_table()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))
        
    def test_table_data_access(self):
        location = self.get_object_uri()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))
