from django import forms
from pos.models import POSUser


class PosUserForm(forms.ModelForm):
    class Meta:
        model = POSUser
        fields = "__all__"