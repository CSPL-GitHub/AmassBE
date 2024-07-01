from django import forms
from pos.models import PosUser


class PosUserForm(forms.ModelForm):
    class Meta:
        model = PosUser
        fields = "__all__"