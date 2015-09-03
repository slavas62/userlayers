from mutant.contrib.geo.models import GeometryFieldDefinition

AUTO_CREATE_MD_GEOMETRY_FIELD = 'geometry'

AUTO_CREATE_MD_FIELDS = {
    AUTO_CREATE_MD_GEOMETRY_FIELD: {'class': GeometryFieldDefinition, 'args': {'null': True, 'blank': True}}
}

