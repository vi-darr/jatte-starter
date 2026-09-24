from django import forms

from .models import ConvoSummary, ServiceRating


class ConvoSummaryForm(forms.ModelForm):
    class Meta:
        model = ConvoSummary
        fields = ['summary']
        widgets = {
            'summary': forms.Textarea(attrs={
                'rows': 10,
                'cols': 60,
                'placeholder': '• ',
                'class': 'w-full p-4 bg-gray-100 rounded-xl resize-y',
            }),
        }

class ServiceRatingForm(forms.ModelForm):
    class Meta:
        model = ServiceRating
        fields = ['overall_rating', 'responsiveness', 'helpfulness', 'comment']