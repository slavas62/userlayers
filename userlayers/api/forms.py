import mutant
from django import forms

FIELD_TYPES = (
    ('text', mutant.contrib.text.models.TextFieldDefinition),
    ('varchar', mutant.contrib.text.models.CharFieldDefinition),

    ('integer', mutant.contrib.numeric.models.BigIntegerFieldDefinition),
    ('small_integer', mutant.contrib.numeric.models.SmallIntegerFieldDefinition),

    ('null_boolean', mutant.contrib.boolean.models.NullBooleanFieldDefinition),
    ('boolean', mutant.contrib.boolean.models.BooleanFieldDefinition),

    ('file', mutant.contrib.file.models.FilePathFieldDefinition),

    ('foreign_key', mutant.contrib.related.models.ForeignKeyDefinition),
    ('one_to_one', mutant.contrib.related.models.OneToOneFieldDefinition),
    ('many_to_many', mutant.contrib.related.models.ManyToManyFieldDefinition),

    ('ip_generic', mutant.contrib.web.models.GenericIPAddressFieldDefinition),
    ('ip', mutant.contrib.web.models.IPAddressFieldDefinition),
    ('email', mutant.contrib.web.models.EmailFieldDefinition),
    ('url', mutant.contrib.web.models.URLFieldDefinition),

    ('geometry', mutant.contrib.geo.models.GeometryFieldDefinition),
    ('point', mutant.contrib.geo.models.PointFieldDefinition),
    ('multi_point', mutant.contrib.geo.models.MultiPointFieldDefinition),
    ('line_string', mutant.contrib.geo.models.LineStringFieldDefinition),
    ('multi_line_string', mutant.contrib.geo.models.MultiLineStringFieldDefinition),
    ('polygon', mutant.contrib.geo.models.PolygonFieldDefinition),
    ('multi_polygon', mutant.contrib.geo.models.MultiPolygonFieldDefinition),
    ('geometry_collection', mutant.contrib.geo.models.GeometryCollectionFieldDefinition),

    ('date', mutant.contrib.temporal.models.DateFieldDefinition),
    ('time', mutant.contrib.temporal.models.TimeFieldDefinition),
    ('datetime', mutant.contrib.temporal.models.DateTimeFieldDefinition),
)

class FieldForm(forms.ModelForm):
    type = forms.ChoiceField(choices=FIELD_TYPES)
    table = forms.CharField(required=False)
    
    class Meta:
        model = mutant.models.FieldDefinition
        fields = ['name']

    def clean_table(self):
        return self.cleaned_data['table'] or None 

class TableFromFileForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField()
