import re
from django import forms
from .models import Ticket
from masters.models import Area, Location, SpecificArea 

class QRComplaintForm(forms.ModelForm):
    area = forms.ModelChoiceField(queryset=Area.objects.all(), empty_label="Select building...", widget=forms.Select(attrs={'class': 'form-select custom-input'}))
    location = forms.ModelChoiceField(queryset=Location.objects.filter(qr_enabled=True), empty_label="Select floor...", widget=forms.Select(attrs={'class': 'form-select custom-input'}))
    specific_area = forms.ModelChoiceField(queryset=SpecificArea.objects.all(), empty_label="Select area...", widget=forms.Select(attrs={'class': 'form-select custom-input'}))

    class Meta:
        model = Ticket
        fields = ['area', 'location', 'specific_area', 'category', 'description', 'reporter_phone', 'priority', 'photo']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control custom-input', 'rows': 3, 'placeholder': 'Describe the problem...'}),
            'reporter_phone': forms.TextInput(attrs={'class': 'form-control custom-input', 'placeholder': '10-digit number...', 'maxlength': '10'}),
            'photo': forms.FileInput(attrs={'class': 'd-none', 'id': 'id_photo', 'accept': 'image/*'})
        }

    def __init__(self, *args, **kwargs):
        is_qr = kwargs.pop('is_qr', False)
        super().__init__(*args, **kwargs)
        if is_qr:
            for field in ['area', 'location', 'specific_area']:
                self.fields[field].disabled = True
                self.fields[field].widget.attrs['style'] = 'background-color: #e2e8f0 !important; cursor: not-allowed; color: #64748b;'