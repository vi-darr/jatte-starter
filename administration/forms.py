from django import forms

from .models import Report


class ReportFilterForm(forms.Form):
    """Filters for the report list view."""
    period = forms.ChoiceField(
        choices=[('', 'All')] + list(Report.PERIOD_CHOICES),
        required=False,
    )


class GenerateReportForm(forms.ModelForm):
    """Form for manually generating a new report."""
    period_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded px-3 py-2 w-full'}),
    )
    period_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded px-3 py-2 w-full'}),
    )

    class Meta:
        model = Report
        fields = ['title', 'period', 'period_start', 'period_end', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'period': forms.Select(attrs={'class': 'border rounded px-3 py-2 w-full'}),
            'notes': forms.Textarea(attrs={'class': 'border rounded px-3 py-2 w-full', 'rows': 3}),
        }
