from tastypie.serializers import Serializer
from django.core.serializers import json

class GeoJsonSerializer(Serializer):
    def to_geojson(self, data, options=None):
        """
        Given some Python data, produces GeoJSON output.
        """
        def _build_feature(obj):
            f = {
              "type": "Feature",
              "properties": {},
              "geometry": {}
            }
          
            def recurse(key, value):
                if key == 'id':
                    f[key] = value
                    return
                if key in ['coordinates', 'type']:
                    f['geometry'][key] = value
                if type(value)==type({}):
                    for k in value:
                        recurse(k, value[k])
                else:
                    f['properties'][key] = value
          
            for key, value in obj.iteritems():
                recurse(key, value)
            return f
    
        def _build_feature_collection(objs, meta):
            fc = {
                "type": "FeatureCollection",
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
    
    def to_json(self, data, options=None):
        """
        Override to enable GeoJSON generation when the geojson option is passed.
        """
        options = options or {}
        if options.get('geojson'):
            return self.to_geojson(data, options)
        else:
            return super(GeoJsonSerializer, self).to_json(data, options)
