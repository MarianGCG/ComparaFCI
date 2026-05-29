from django import forms

class ImportarExcelForm(forms.Form):
    archivo = forms.FileField(label="Seleccionar archivo Excel")
