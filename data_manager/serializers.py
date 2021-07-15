import os
from data_manager.filters import OccurrenceFilter
from data_manager.models import HarvestedDataset, Dataset, Keyword, Project, BasisOfRecord, Publisher, GBIFOccurrence, \
    Download, DataType, HexGrid, TaskResult, Person, PersonTypeRole
from data_manager.tasks import prepare_download_file
from django.conf import settings
from django.urls import reverse
from django_filters import filters
from rest_framework import serializers


null_boolean_choices = [(True, 'Yes'), (False, 'No'), (None, 'Unknown')]
boolean_choices = [(False, 'No'), (True, 'Yes')]


def get_filter_field_name(filter_set):
    filter_fields = []
    for field, field_filter in filter_set.get_filters().items():
        if isinstance(field_filter, filters.RangeFilter):
            min_field_name = field + '_min'
            max_field_name = field + '_max'
            range_field_name = [min_field_name, max_field_name]
            filter_fields.extend(range_field_name)
        else:
            filter_fields.append(field)
    return filter_fields


class HarvestedDatasetSerializer(serializers.ModelSerializer):
    """
    Serialize HarvestedDataset instances
    """
    # enforce these fields to ensure that Users will not input other values
    include_in_antabif = serializers.ChoiceField(choices=null_boolean_choices,
                                                 style={'base_template': 'select.html'}, required=False)
    import_full_dataset = serializers.ChoiceField(choices=null_boolean_choices,
                                                  style={'base_template': 'select.html'}, required=False)
    deleted_from_gbif = serializers.ChoiceField(choices=boolean_choices,
                                                style={'base_template': 'select.html'}, required=False)
    key = serializers.UUIDField(required=True, format='hex_verbose')

    class Meta:
        model = HarvestedDataset
        fields = "__all__"


class DataTypeSerializer(serializers.ModelSerializer):
    """
    Serialize DataType instances. All fields are read-only.
    """

    class Meta:
        model = DataType
        fields = ('id', 'data_type')
        read_only_fields = fields


class KeywordSerializer(serializers.ModelSerializer):
    """
    Serialize Keyword instances
    """
    class Meta:
        model = Keyword
        fields = ('id', 'keyword', 'thesaurus')
        read_only_fields = fields


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serialize Project instances, all fields are read-only
    """
    class Meta:
        model = Project
        fields = ('id', 'title', 'funding',)
        read_only_fields = fields


class PublisherSerializer(serializers.ModelSerializer):
    """
    Serialize Publisher instances
    """
    class Meta:
        model = Publisher
        fields = ('id', 'publisher_key', 'publisher_name')
        read_only_fields = fields


class DatasetSerializer(serializers.ModelSerializer):
    """
    Serialize Dataset instances
    """
    data_type = DataTypeSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    keyword_set = KeywordSerializer(many=True, read_only=True)

    class Meta:
        model = Dataset
        fields = ('id', 'title', 'abstract', 'pub_date', 'intellectual_right', 'doi', 'alternate_identifiers',
                  'bounding_box', 'citation', 'data_type', 'project', 'keyword_set', 'publisher')


class BasisOfRecordSerializer(serializers.ModelSerializer):
    """
    Serialize BasisOfRecord instances
    """
    class Meta:
        model = BasisOfRecord
        fields = ('id', 'basis_of_record',)


class ProjectPersonnelSerializer(serializers.Serializer):

    def to_representation(self, instance):
        person_type_role = PersonTypeRole.objects.filter(person=instance)
        projects = [entry.project_id for entry in person_type_role]

        representation = {
            'id': instance.id,
            'surname': instance.surname,
            'givenName': instance.given_name,
            'project': projects,
        }
        return representation

    class Meta:
        model = Person


class OccurrenceSerializer(serializers.ModelSerializer):
    """
    Serialize GBIFOccurrence instances
    """

    class Meta:
        model = GBIFOccurrence
        fields = settings.OCCURRENCE_FIELDS


class DownloadSerializer(serializers.Serializer):
    """
    Serialize Download instance(s).
    """
    query = serializers.JSONField(required=False)

    def validate_query(self, value):
        """
        Validate query field ensure that all fields in the query are filterable by OccurrenceFilter
        """
        # get all field names of OccurrenceFilter
        if value:
            for key in value:
                if key not in get_filter_field_name(OccurrenceFilter):
                    error_message = 'Invalid field name: {}'.format(key)
                    raise serializers.ValidationError(detail=error_message)
        return value

    def create(self, validated_data):
        """
        Create Download instance with validated_data but will not saved into the database -
        because the user_id will be determined at views.
        """
        download = Download.objects.create(**validated_data)
        request = self.context.get('request')
        download_link = request.build_absolute_uri(reverse('my-download-file', args=(download.id,)))
        prepare_download_file.apply_async((download.id, download_link), retry=True)
        return download

    def to_representation(self, instance):
        """
        Convert Download instance to JSON representation
        :param instance: Download object
        :return: a Python dictionary
        """
        # Access the status of TaskResult using Download.task_id
        if TaskResult.objects.filter(task_id=instance.task_id).exists():
            status = TaskResult.objects.get(task_id=instance.task_id).status
        else:
            status = 'PENDING'
        if isinstance(instance.query, str):
            query = instance.query_string_to_dict()
        else:
            query = instance.query
        # access request in context passed to serializer in views. Absolute uri can only be determined in views.
        download_link = ""  # leave empty if the file is not generated yet
        if instance.file:
            if os.path.isfile(instance.file.path):
                request = self.context.get('request')
                download_link = request.build_absolute_uri(reverse('my-download-file', args=(instance.id,)))
        representation = {
            'id': instance.id,
            'status': status,
            'downloadLink': download_link,
            'created': instance.created_at,
            'recordCount': instance.record_count,
            'query': query,
        }
        return representation

    class Meta:
        model = Download


class HexGridSerializer(serializers.ModelSerializer):
    """
    Serialize HexGrid instances
    """
    class Meta:
        model = HexGrid
        fields = ('id', 'geom')
