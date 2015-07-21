import mutant

from django import forms

from mutant.models import ModelDefinition, FieldDefinition

FIELD_TYPES = (
    ('text', mutant.contrib.text.models.TextFieldDefinition),
    ('integer', mutant.contrib.numeric.models.BigIntegerFieldDefinition),
    ('boolean', mutant.contrib.boolean.models.NullBooleanFieldDefinition),
)

class FieldForm(forms.ModelForm):
    type = forms.ChoiceField(choices=FIELD_TYPES)
    
    class Meta:
        model = FieldDefinition
        fields = ['name',]


class TableFromFileForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField()
