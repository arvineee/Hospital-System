from django import forms
from .models import PatientHistory

class PatientHistoryForm(forms.ModelForm):
    class Meta:
        model = PatientHistory
        fields = [
            'signs', 'symptoms', 'temperature', 'blood_pressure', 'pulse',
            'respiratory_rate', 'spo2', 'hpi', 'diagnosis', 'notes', 'status'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'temperature': forms.NumberInput(attrs={'step': '0.1'}),
            'status': forms.Select(choices=PatientHistory.STATUS_CHOICES),
        }
