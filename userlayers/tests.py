import json
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from tastypie.test import ResourceTestCase
from userlayers.api.resources import TablesResource, FieldsResource
from django.contrib.gis.geos.geometry import GEOSGeometry

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

    def create_table(self, payload=TABLE_META):
        resp = self.api_client.post(self.uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        return resp.get('Location')

    def get_objects_uri(self, table_uri=None):
        table_uri = table_uri or self.create_table()
        resp = self.api_client.get(table_uri)
        data = self.deserialize(resp)
        return data['objects_uri']

    def get_objects_3d_uri(self):
        payload = TABLE_META.copy()
        payload['is_3d'] = True
        table_uri = self.create_table(payload)
        objects_uri = self.get_objects_uri(table_uri)
        return objects_uri

    def create_objects_in_table(self, values, objects_uri=None):
        """ values must look like
        values = {
            'geometry': ('{"type":"MultiPoint","coordinates":[[94.79003906249999,65.3668368922632]]}',),
            'text_field': ('foo', 'bar'),
            'integer_field': (1, 2),
            'float_field': (1, 1.1),
            'boolean_field': (1, 0)
        }
        """
        objects_uri = objects_uri or self.get_objects_uri()
        payload = {
            'objects': []
        }
        for k, v in values.items():
            payload['objects'] += map(lambda i: {k: i}, v)
        return self.api_client.put(objects_uri, data=payload)

    def get_object_uri(self):
        objects_uri = self.get_objects_uri()
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

    def test_create_objects_with_wrong_values(self):
        payload = {
            'geometry': ({"type": "MultiPoint", "coordinates": [94.79003906249999, 65.3668368922632]},),
            'integer_field': (1.1, 'some text'),
            'float_field': ('some text',)
        }
        resp = self.create_objects_in_table(payload)
        self.assertHttpBadRequest(resp)

    def test_create_objects(self):
        payload = {
            'geometry': ({"type": "MultiPoint", "coordinates": [[94.79003906249999, 65.3668368922632]]},),
            'text_field': (1, 1.1, True, False, '', 'some text', None),
            'integer_field': (1, '1', '', None),
            'float_field': (1, 1.1, True, False, '1.1', None),
            'boolean_field': (True, False, 1, 0, '', '123', None)
        }
        resp = self.create_objects_in_table(payload)
        self.assertHttpAccepted(resp)

    def test_attached_files(self):
        obj = self.get_object_uri()
        resp = self.api_client.get(obj)
        data = json.loads(resp.content)
        files_uri = data['properties'].get('files_uri')
        self.assertTrue(files_uri)
        
        f = SimpleUploadedFile('somefile.txt', 'some content')
        resp = self.api_client.client.post(files_uri, dict(file=f))
        self.assertHttpCreated(resp)
        
        file_uri = resp.get('Location')
        resp = self.api_client.get(file_uri)
        self.assertHttpOK(resp)
        
        resp = self.api_client.get(files_uri)
        data = json.loads(resp.content)
        files = data['objects']
        self.assertTrue(files)
        
        self.api_client.delete(file_uri)
        self.assertHttpNotFound(self.api_client.get(file_uri))

    def test_3d_geometry(self):
        objects_uri = self.get_objects_3d_uri()
        
        payload = {
            'geometry': (
                #3d
                {"type": "Point", "coordinates": [55.45, 37.37, 120]},
                {"type": "Polygon", "coordinates": [[[37.60, 55.75, 110], [37.62, 55.76, 120], [37.64, 55.74, 130], [37.60, 55.75, 110]]]},
                #2d
                {"type": "Point", "coordinates": [55.45, 37.37]},
                {"type": "Polygon", "coordinates": [[[37.60, 55.75], [37.62, 55.76], [37.64, 55.74], [37.60, 55.75]]]},
            )
        }
        resp = self.create_objects_in_table(payload, objects_uri)
        self.assertHttpAccepted(resp)
        
        resp = self.api_client.get(objects_uri)
        self.assertValidJSONResponse(resp)
        data = json.loads(resp.content)
        for feat in data['features']:
            geom = GEOSGeometry(json.dumps(feat['geometry']))
            self.assertTrue(geom.hasz)


class AuthorizationTests(TableMixin, ResourceTestCase):
    def test_table_access(self):
        location = self.create_table()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))

    def test_table_data_access(self):
        location = self.get_object_uri()
        self.create_user_and_login('user2')
        self.assertHttpUnauthorized(self.api_client.get(location))
