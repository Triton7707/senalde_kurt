from django import forms


class PredictionForm(forms.Form):
    GENDER_CHOICES = [
        ('', '— Select Gender —'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    SLEEP_CHOICES = [
        ('', '— Select Sleep Duration —'),
        ('Less than 5 hours', 'Less than 5 hours'),
        ('5-6 hours', '5–6 hours'),
        ('7-8 hours', '7–8 hours'),
        ('More than 8 hours', 'More than 8 hours'),
    ]

    age = forms.IntegerField(
        min_value=16,
        max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 21',
        }),
        label='Age',
        help_text='Your current age in years (16–60).'
    )

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Gender'
    )

    academic_pressure = forms.FloatField(
        min_value=0,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 3.5',
            'step': '0.1',
        }),
        label='Academic Pressure',
        help_text='Rate academic pressure from 0 (none) to 5 (extreme).'
    )

    sleep_duration = forms.ChoiceField(
        choices=SLEEP_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Sleep Duration'
    )

    cgpa = forms.FloatField(
        min_value=0.0,
        max_value=10.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 7.8',
            'step': '0.01',
        }),
        label='CGPA',
        help_text='Your cumulative GPA on a 10-point scale.'
    )

    study_satisfaction = forms.FloatField(
        min_value=0,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 3.0',
            'step': '0.1',
        }),
        label='Study Satisfaction',
        help_text='Rate your satisfaction with studies from 0 (very dissatisfied) to 5 (very satisfied).'
    )

    work_pressure = forms.FloatField(
        min_value=0,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2.5',
            'step': '0.1',
        }),
        label='Work Pressure',
        help_text='Rate work/job pressure from 0 (none) to 5 (extreme). Enter 0 if not working.'
    )
