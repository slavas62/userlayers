from tastypie.serializers import Serializer
from django.core.serializers import json
from shapeutils.convert import geojson_to_zipshape

class GeoJsonSerializer(Serializer):
    formats = ['geojson', 'shapefile']
     
    content_types = {
        'geojson': 'application/json',
        'shapefile': 'application/zip',
    }
    
    def from_geojson(self, *args, **kwargs):
        return self.from_json(*args, **kwargs)
    
    def to_geojson(self, data, options=None):
        """
        Given some Python data, produces GeoJSON output.
        """
        def _build_feature(obj):
            f = {
              "type": "Feature",
              "properties": {},
              "geometry": None,
            }
          
            def recurse(key, value):
                if key == 'id':
                    f[key] = value
                    return
                if type(value)==type({}):
                    if 'type' in value.keys():
                        if value['type'] == 'GeometryCollection' or 'coordinates' in value.keys():
                            if f['geometry']:
                                f['properties'][key] = value
                            else:
                                f['geometry'] = value
                            return
                    for k in value:
                        recurse(k, value[k])
                else:
                    f['properties'][key] = value
          
            geometry_field = options.get('geometry_field')
            if geometry_field and geometry_field in obj:
                f['geometry'] = obj.pop(geometry_field)
            for key, value in obj.iteritems():
                recurse(key, value)
            return f
    
        def _build_feature_collection(objs, meta):
            fc = {
                "type": "FeatureCollection",
                "crs": {
                    "type": "name",
                    "properties": {
                      "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                    }
                },
                "features": []
            }
            if(meta):
                fc["meta"] = meta
            for obj in objs:
                fc['features'].append(_build_feature(obj))
            return fc
    
        options = options or {}    
        data = self.to_simple(data, options)
        meta = data.get('meta')
        
        if 'objects' in data:
            data = _build_feature_collection(data['objects'], meta)
        else:
            data = _build_feature(data)
        return json.json.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)   
    
    def to_shapefile(self, data, options=None):
        return geojson_to_zipshape(self.to_geojson(data, options))
