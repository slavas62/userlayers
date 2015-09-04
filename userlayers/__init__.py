from mutant.contrib.geo.models import GeometryFieldDefinition
from django.conf import settings

SETTINGS_DEFAULT_MD_GEOMETRY_FIELD_NAME = 'USERLAYERS_DEFAULT_MD_GEOMETRY_FIELD_NAME'
DEFAULT_MD_GEOMETRY_FIELD_NAME = getattr(settings, SETTINGS_DEFAULT_MD_GEOMETRY_FIELD_NAME, 'geometry')
