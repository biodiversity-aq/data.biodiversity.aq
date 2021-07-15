from data_manager.models import BasisOfRecord, DataType, Person, Dataset, Publisher
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.postgres.forms import FloatRangeField
from django_filters.widgets import RangeWidget
from psycopg2.extras import NumericRange


class DatasetFilterForm(forms.Form):
    """
    Filter form for refined search on dataset listview page (search result)
    Queryset for multiple choice field will be override in views because they are dependent on the search parameter

    """
    # Faceted search form
    q = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'placeholder': ' search'}))

    # Queryset for data_type, keyword, project_contact will be override in views before form validation
    data_type = forms.ModelMultipleChoiceField(label='Data types', queryset=DataType.objects.all(), required=False,
                                               widget=forms.CheckboxSelectMultiple())
    publisher = forms.ModelMultipleChoiceField(label='Publisher', queryset=Publisher.objects.all(), required=False,
                                               widget=forms.CheckboxSelectMultiple())
    keyword = forms.MultipleChoiceField(label='Keywords', required=False, widget=forms.SelectMultiple())
    project_contact = forms.ModelMultipleChoiceField(label='Project contacts', required=False,
                                                     queryset=Person.objects.all(),
                                                     widget=forms.CheckboxSelectMultiple())
    # Text input
    project = forms.CharField(label='Project', required=False,
                              widget=forms.TextInput(attrs={'placeholder': ' search project title'}))

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')  # remove ':' after label tag
        super(DatasetFilterForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DatasetFilterForm, self).clean()
        return cleaned_data


class OccurrenceFilterForm(forms.Form):
    """
    Filter form for refined search on occurrence listview page (search result)
    """
    taxon = forms.CharField(max_length=100, widget=forms.HiddenInput(), required=False)
    # Faceted search form
    q = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'placeholder': ' search'}))
    dataset = forms.ModelChoiceField(queryset=Dataset.objects.all().order_by('title'), required=False)
    basis_of_record = forms.ModelMultipleChoiceField(label='Basis of record', required=False,
                                                     queryset=BasisOfRecord.objects.all(),
                                                     widget=forms.CheckboxSelectMultiple())
    decimal_latitude = FloatRangeField(widget=RangeWidget({'type': 'number', 'step': 'any'}), required=False,
                                       initial=NumericRange(-90.0, 90.0, '[)'))
    decimal_longitude = FloatRangeField(widget=RangeWidget({'type': 'number', 'step': 'any'}), required=False,
                                        initial=NumericRange(-180.0, 180.0, '[)'))

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super(OccurrenceFilterForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(OccurrenceFilterForm, self).clean()
        if not cleaned_data['decimal_latitude']:
            cleaned_data['decimal_latitude'] = self.fields['decimal_latitude'].initial
        if not cleaned_data['decimal_longitude']:
            cleaned_data['decimal_longitude'] = self.fields['decimal_longitude'].initial
        return cleaned_data

    def to_str(self):
        c = self.clean()
        return '-'.join([
            c['type'], c['taxon'], c['q'], c['dataset'] or '', ''.join(c['basis_of_record']),
            str(c['decimal_latitude'].lower), str(c['decimal_latitude'].upper),
            str(c['decimal_longitude'].lower), str(c['decimal_longitude'].upper)
            ])

    def to_dict(self):
        c = self.clean()
        return {
            'type': c['type'],
            'taxon': c['taxon'],
            'q': c['q'],
            'dataset': c['dataset'] or '',
            'basis_of_record': ''.join(c['basis_of_record']),
            'decimal_latitude_lower': c['decimal_latitude'].lower,
            'decimal_latitude_upper': c['decimal_latitude'].upper,
            'decimal_longitude_lower': c['decimal_longitude'].lower,
            'decimal_longitude_upper': c['decimal_longitude'].upper
        }


class TaxonSearchForm(forms.Form):
    """Search taxa form"""
    choices = (('2d59e5db-57ad-41ff-97d6-11f5fb264527', 'World Register of Marine Species'),
               ('d7dddbf4-2cf0-4f39-9b2a-bb099caae36c', 'GBIF Backbone Taxonomy'))
    q = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'placeholder': ' search'}))
    backbone = forms.MultipleChoiceField(required=False, choices=choices, widget=forms.CheckboxSelectMultiple())

    def clean(self):
        cleaned_data = super(TaxonSearchForm, self).clean()
        return cleaned_data


class RegistrationForm(UserCreationForm):
    """
    Account registration form using default Django user authentication
    It uses default Django User model which has unique constraint on username but not email.
    In this form, we enforce email as value for username.
    """
    username = forms.EmailField(max_length=200, help_text='Required', label='Email')
    accept_terms = forms.BooleanField(required=True, widget=forms.CheckboxInput())

    class Meta:
        model = get_user_model()
        exclude = ('email',)
        fields = ('username', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['username']
        return email
