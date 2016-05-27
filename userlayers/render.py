import mapnik
from django.conf import settings
from .gistools import SphericalMercator

class Renderer(object):
    projection = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over'

    map_string_template = """
        <?xml version="1.0" encoding="utf-8"?>
        <Map srs="%(srs)s" background-color="#00000000">
          <Style name="Default Style">
            <Rule>
              <PolygonSymbolizer fill="rgb(242,239,249)"/>
              <LineSymbolizer stroke="rgb(128,128,128)" stroke-width="0.1"/>
            </Rule>
          </Style>
          <Layer name="PostGIS Layer" srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
            <StyleName>Default Style</StyleName>
            <Datasource>
              <Parameter name="dbname">%(dbname)s</Parameter>
              <Parameter name="host">%(host)s</Parameter>
              <Parameter name="password">%(password)s</Parameter>
              <Parameter name="table">&quot;%(dbtable)s&quot;</Parameter>
              <Parameter name="type">postgis</Parameter>
              <Parameter name="user">%(user)s</Parameter>
            </Datasource>
          </Layer>
        </Map>
    """

    def __init__(self, md):
        self.md = md

    def get_mapnik_config(self):
        db = settings.DATABASES['default']
        params = {
            'host': db.get('HOST'),
            'port': db.get('PORT'),
            'dbname': db.get('NAME'),
            'dbtable': self.md.db_table,
            'user': db.get('USER'),
            'password': db.get('PASSWORD'),
            
            'srs': self.projection,
        }
        
        map_string = (self.map_string_template % params).encode('utf-8')
        return map_string

    def render_tile(self, x, y, z):
        m = mapnik.Map(256, 256)
        mapnik.load_map_from_string(m, self.get_mapnik_config())
        im = mapnik.Image(m.width, m.height)
        proj = mapnik.Projection(self.projection)
        bbox = proj.forward(mapnik.Box2d(*SphericalMercator().xyz_to_envelope(int(x), int(y), int(z))))
        m.zoom_to_box(bbox)
        mapnik.render(m, im)
        return im.tostring('png')
