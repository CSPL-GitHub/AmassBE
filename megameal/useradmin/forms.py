from django import forms
from core.models import Platform, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = "__all__"

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = "__all__"

