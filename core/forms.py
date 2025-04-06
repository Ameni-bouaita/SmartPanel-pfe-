from django import forms
from .models import Panelist, Announcer, Interest

class PanelistForm(forms.ModelForm):
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # ✅ Convertit en checklist
        required=True
    )

    class Meta:
        model = Panelist
        fields = ['full_name', 'email', 'interests']

class AnnouncerForm(forms.ModelForm):
    industry = forms.ModelChoiceField(
        queryset=Interest.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Announcer
        fields = ['company_name', 'email', 'industry']
