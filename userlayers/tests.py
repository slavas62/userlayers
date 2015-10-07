from django.contrib.auth import get_user_model
from tastypie.test import ResourceTestCase
from userlayers.api.resources import TablesResource

class TableApiTests(ResourceTestCase):
    
    uri = TablesResource().get_resource_uri()
    
    def create_user_and_login(self):
        credentials = dict(username='admin', password='admin')
        get_user_model().objects.create_user(**credentials)
        self.api_client.client.login(**credentials)

    def create_table(self):
        payload = {"name": "foo", "fields": [{"name": "display_name", "type": "text"}, {"name": "value", "type": "integer"}, {"name": "is_ok", "type": "boolean"}]}
        resp = self.api_client.post(self.uri, data=payload)
        self.assertHttpCreated(resp)
        self.assertTrue(resp.has_header('Location'))
        return resp.get('Location')
    
    def setUp(self):
        super(TableApiTests, self).setUp()
        self.create_user_and_login()
    
    def test_create_delete_table(self):
        location = self.create_table()
        self.assertValidJSONResponse(self.api_client.get(location))
        self.api_client.delete(location)
        self.assertHttpNotFound(self.api_client.get(location))

    def test_get_table_list(self):
        self.assertValidJSONResponse(self.api_client.get(self.uri))
