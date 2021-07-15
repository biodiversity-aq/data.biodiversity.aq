import django_filters as filters
from data_manager.models import Dataset, BasisOfRecord, GBIFOccurrence, DataType, Keyword, Publisher, Person, Project


class HarvestedDatasetFilter(filters.FilterSet):
    """
    FilterSet for HarvestedDataset instances
    """
    q = filters.CharFilter(field_name='title',
                           lookup_expr='icontains',
                           label='Search dataset title')
    include_in_antabif = filters.BooleanFilter(
        field_name='include_in_antabif',
        help_text='Boolean to select for datasets which are set to be imported into database.')
    import_full_dataset = filters.BooleanFilter(
        field_name='import_full_dataset',
        help_text='Boolean to select for datasets which all data records should be imported into database.')
    deleted_from_gbif = filters.BooleanFilter(
        field_name='deleted_from_gbif',
        help_text='Boolean to select for datasets which are harvested but are deleted on GBIF.')
    dataset_is_null = filters.BooleanFilter(
        field_name='dataset', label='Not imported',
        lookup_expr='isnull', help_text='True if dataset is not imported into database yet.')


class DatasetFilter(filters.FilterSet):
    """
    FilterSet for Dataset instances
    """
    q = filters.CharFilter(field_name='eml_text', lookup_expr='icontains', label='Search term')
    data_type = filters.ModelMultipleChoiceFilter(
        field_name='data_type', queryset=DataType.objects.all(), label='Data type',
        help_text='A list of integer values identifying the DataType.')
    keyword = filters.ModelMultipleChoiceFilter(
        field_name='keyword', queryset=Keyword.objects.all(),
        label='Keywords',
        help_text='A list of integer values identifying the Keyword.')
    project = filters.ModelMultipleChoiceFilter(
        field_name='project', queryset=Project.objects.all(), label='Project',
        help_text='A list of integer values identifying the Project.')
    publisher = filters.ModelMultipleChoiceFilter(
        field_name='publisher', queryset=Publisher.objects.all(), label='Publisher name',
        help_text='A list of integer values identifying the Publisher.')
    project_personnel = filters.ModelMultipleChoiceFilter(
        field_name='personTypeRole__person', queryset=Person.objects.filter(personTypeRole__person_type='personnel'),
        label='Project personnel', help_text='https://eml.ecoinformatics.org/schema/eml-project_xsd.html#ResearchProjectType_personnel'
    )


class OccurrenceFilter(filters.FilterSet):
    """
    FilterSet for GBIFOccurrence instances
    """
    q = filters.CharFilter(field_name='row_json_text', lookup_expr='icontains', label='Search term')
    # Taxon
    scientific_name = filters.CharFilter(
        field_name='scientificName', lookup_expr='icontains', label='Scientific name',
        help_text=GBIFOccurrence._meta.get_field('scientificName').help_text)
    taxon_key = filters.CharFilter(
        field_name='taxonKey', lookup_expr='exact', label='Taxon key',
        help_text=GBIFOccurrence._meta.get_field('taxonKey').help_text)
    # Spatial
    decimal_latitude = filters.RangeFilter(
        field_name='decimalLatitude', label='Decimal latitude',
        help_text=GBIFOccurrence._meta.get_field('decimalLatitude').help_text)
    decimal_longitude = filters.RangeFilter(
        field_name='decimalLongitude', label='Decimal longitude',
        help_text=GBIFOccurrence._meta.get_field('decimalLongitude').help_text)
    depth = filters.RangeFilter(
        field_name='depth', label='Depth in meters',
        help_text=GBIFOccurrence._meta.get_field('depth').help_text)
    # Temporal
    year = filters.RangeFilter(
        field_name='year', lookup_expr='exact', label='Year',
        help_text=GBIFOccurrence._meta.get_field('year').help_text)
    month = filters.RangeFilter(
        field_name='month', lookup_expr='exact', label='Month',
        help_text=GBIFOccurrence._meta.get_field('month').help_text)
    day = filters.RangeFilter(
        field_name='day', lookup_expr='exact', label='Day',
        help_text=GBIFOccurrence._meta.get_field('day').help_text)
    # sampling
    locality = filters.CharFilter(
        field_name='locality', lookup_expr='icontains', label='Locality',
        help_text=GBIFOccurrence._meta.get_field('locality').help_text)
    sampling_protocol = filters.CharFilter(
        field_name='samplingProtocol', lookup_expr='icontains', label='Sampling protocol',
        help_text=GBIFOccurrence._meta.get_field('samplingProtocol').help_text)
    occurrence_status = filters.CharFilter(
        field_name='occurrenceStatus', lookup_expr='iexact', label='Occurrence status',
        help_text=GBIFOccurrence._meta.get_field('occurrenceStatus').help_text)
    dataset = filters.ModelMultipleChoiceFilter(
        field_name='dataset', queryset=Dataset.objects.all(),
        help_text='A list of integer values identifying the Dataset.')
    basis_of_record = filters.ModelMultipleChoiceFilter(
        field_name='basis_of_record', queryset=BasisOfRecord.objects.all(), label='Basis of record',
        help_text='A list of integer values identifying the BasisOfRecord.')
