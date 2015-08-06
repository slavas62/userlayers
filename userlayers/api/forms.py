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
    table = forms.CharField(required=False)
    
    class Meta:
        model = FieldDefinition
        fields = ['name',]

    def clean_table(self):
        return self.cleaned_data['table'] or None 

class TableFromFileForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField()
