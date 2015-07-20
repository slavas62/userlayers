from django import forms

class TableFromFileForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField()
