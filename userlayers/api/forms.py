from mutant.contrib.text.models import TextFieldDefinition, CharFieldDefinition
from mutant.contrib.numeric.models import BigIntegerFieldDefinition, SmallIntegerFieldDefinition
from mutant.contrib.boolean.models import NullBooleanFieldDefinition, BooleanFieldDefinition
from mutant.contrib.file.models import FilePathFieldDefinition
from mutant.contrib.related.models import ForeignKeyDefinition, OneToOneFieldDefinition, ManyToManyFieldDefinition
from mutant.contrib.web.models import GenericIPAddressFieldDefinition, IPAddressFieldDefinition, EmailFieldDefinition, \
    URLFieldDefinition
from mutant.contrib.geo.models import GeometryFieldDefinition, PointFieldDefinition, MultiPointFieldDefinition, \
    MultiPointFieldDefinition, LineStringFieldDefinition, MultiLineStringFieldDefinition, PolygonFieldDefinition, \
    MultiPolygonFieldDefinition, GeometryCollectionFieldDefinition
from mutant.contrib.temporal.models import DateFieldDefinition, TimeFieldDefinition, DateTimeFieldDefinition
from mutant.models import FieldDefinition
from django import forms

FIELD_TYPES = (
    ('text', TextFieldDefinition),
    ('varchar', CharFieldDefinition),

    ('integer', BigIntegerFieldDefinition),
    ('small_integer', SmallIntegerFieldDefinition),

    ('null_boolean', NullBooleanFieldDefinition),
    ('boolean', BooleanFieldDefinition),

    ('file', FilePathFieldDefinition),

    ('foreign_key', ForeignKeyDefinition),
    ('one_to_one', OneToOneFieldDefinition),
    ('many_to_many', ManyToManyFieldDefinition),

    ('ip_generic', GenericIPAddressFieldDefinition),
    ('ip', IPAddressFieldDefinition),
    ('email', EmailFieldDefinition),
    ('url', URLFieldDefinition),

    ('geometry', GeometryFieldDefinition),
    ('point', PointFieldDefinition),
    ('multi_point', MultiPointFieldDefinition),
    ('line_string', LineStringFieldDefinition),
    ('multi_line_string', MultiLineStringFieldDefinition),
    ('polygon', PolygonFieldDefinition),
    ('multi_polygon', MultiPolygonFieldDefinition),
    ('geometry_collection', GeometryCollectionFieldDefinition),

    ('date', DateFieldDefinition),
    ('time', TimeFieldDefinition),
    ('datetime', DateTimeFieldDefinition),
)

class FieldForm(forms.ModelForm):
    type = forms.ChoiceField(choices=FIELD_TYPES)
    table = forms.CharField(required=False)
    
    class Meta:
        model = FieldDefinition
        fields = ['name']

    def clean_table(self):
        return self.cleaned_data['table'] or None 

class TableFromFileForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField()
