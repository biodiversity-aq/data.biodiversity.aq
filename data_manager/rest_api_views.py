# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.serializers import serialize
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, filters, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from .filters import OccurrenceFilter, HarvestedDatasetFilter, DatasetFilter
from .helpers import get_occurrence_queryset_from_form
from .models import DataType, Dataset, HarvestedDataset, HexGrid, Keyword, Project, BasisOfRecord, \
    Publisher, GBIFOccurrence, Download, Person
from .permissions import IsAuthenticatedAndIsOwner
from .serializers import HarvestedDatasetSerializer, DatasetSerializer, KeywordSerializer, \
    ProjectSerializer, BasisOfRecordSerializer, PublisherSerializer, OccurrenceSerializer, \
    DataTypeSerializer, DownloadSerializer, ProjectPersonnelSerializer


logger = logging.getLogger('data_manager')


@swagger_auto_schema(methods=['get'], auto_schema=None)
@api_view(['GET'])
def database_statistics(request):
    """
    A view that returns the database content statistics. *Will be deprecated in future version*
    """
    qs = Dataset.objects.all().prefetch_related('data_type')
    d = DataType.objects.annotate(num_datasets=Count('dataset'))
    content = {
        'total number of datasets': qs.only('pk').count(),
        'total number of occurrence records': qs.aggregate(Sum('filtered_record_count'))['filtered_record_count__sum'],
        'number of datasets per data type': {}
    }
    for data_type in d:
        content['number of datasets per data type'][data_type.data_type] = data_type.num_datasets
    return Response(content)


@swagger_auto_schema(methods=['get'], auto_schema=None)
@api_view(['GET'])
def occurrence_grid(request):
    """
    Process queries for HexGrid objects. *Will be deprecated in future version*
    :param request: HTTP GET request
    :return: JSON format of HexGrid (only pk and count) or GeoJSON of the geom of HexGrid.
    """
    # key = zoom level, value = size of grid
    zoom_grid_size_dict = {'3': 250000,
                           '4': 100000,
                           '5': 50000,
                           '6': 25000}
    # OCCURRENCE
    occ_qs, form, latitude_range, longitude_range = get_occurrence_queryset_from_form(request.query_params)
    zoom = request.query_params.get('zoom', '3')
    extent = request.query_params.get('extent', '')
    # False to return geojson, True to return pk & count of a hexgrid
    count = request.query_params.get('count', False)
    qs = HexGrid.objects.filter(size=zoom_grid_size_dict[zoom]).only('id', 'geom')
    if extent:
        extent_array = extent.split(',')
        extent = [float(p) for p in extent_array]
        qs = qs.filter(left__gte=extent[0]).filter(bottom__gte=extent[1]).filter(right__lte=extent[2]).filter(top__lte=extent[3])
    qs = qs.filter(GBIFOccurrence__in=occ_qs).annotate(count=Count('GBIFOccurrence'))
    # qs = qs.filter(size=zoom_grid_size_dict[zoom]).annotate(count=Count('GBIFOccurrence')).order_by()
    if not count:
        # return geojson format of queryset
        # properties will contain 'pk'. annotate value could not be serialize.
        results = serialize('geojson', qs, geometry_field='geom', srid=3031, fields=('pk', 'geom'))
        return Response(data=json.loads(results))
    else:
        # return json format which contains only 'pk' and 'count' as 'geom' needs to be serialized.
        results = qs.values('pk', 'count')
        return Response({'results': list(results)})


@swagger_auto_schema(methods=['get'], auto_schema=None)
@api_view(['GET'])
@renderer_classes((TemplateHTMLRenderer, JSONRenderer))
def occurrence_search_view(request):
    """
    Search for GBIFOccurrences. *Will be deprecated in future version*
    if "format=json" is specified in url, JSON data will be returned. Otherwise response will be rendered using
    'templates/occurrence-table.html' template - according to the order in @renderer_classes decorator:
    e.g. /api/search/occurrence/?q=cnidaria&type=occurrence&format=json
    """
    page_size = int(settings.REST_FRAMEWORK.get('PAGE_SIZE', '20'))
    offset = int(request.GET.get('offset', '0'))
    limit = int(request.GET.get('limit', offset + page_size))
    qs, form, latitude_range, longitude_range = get_occurrence_queryset_from_form(request.GET)
    has_previous_page = False
    if offset == 0:  # if offset = 0, qs[offset-1] will throw AssertionError: Negative indexing is not supported.
        has_previous_page = False
    elif offset > 0:
        if qs.only('id')[offset-1]:
            has_previous_page = True
        else:
            has_previous_page = False
    has_next_page = True
    try:
        qs.only('id')[limit+1]
    except IndexError:
        has_next_page = False
    # use .only() to avoid select all other fields when executing SQL query
    qs = qs.only('id', 'scientificName', 'decimalLatitude', 'decimalLongitude', 'year', 'month',
                 'dataset_id', 'institutionCode', 'collectionCode', 'locality', 'dataset_title',
                 'taxonKey', 'basisOfRecord')[offset:limit]
    return Response({'limit': limit, 'offset': offset, 'page size': page_size, 'has_previous_page': has_previous_page,
                     'has_next_page': has_next_page, 'occurrences': [x.toJSON() for x in qs]},
                    template_name='occurrence-table.html')


@swagger_auto_schema(methods=['get'], auto_schema=None)
@api_view(['GET'])
def occurrence_count(request):
    """
    Count the total number of occurrences for given search parameters
    """
    cache_url = re.sub(r'\&offset\=\d+', '', request.META.get('QUERY_STRING'))
    cache_key = 'occurrencecount-humanize-' + cache_url
    logger.info('Cache key: {}'.format(cache_key))
    results_count = cache.get(cache_key)
    if not results_count:
        qs, form, latitude_range, longitude_range = get_occurrence_queryset_from_form(request.GET)
        results_count = "{:,}".format(qs.only('id').count())  # add comma to thousand
        cache.set(cache_key, results_count)
    return Response({
        'count': results_count
    })


class HarvestedDatasetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for HarvestedDataset instances. For admin only.

    list:
    Return a list of HarvestedDatasets

    retrieve:
    Return the given HarvestedDataset
    """
    queryset = HarvestedDataset.objects.all()
    serializer_class = HarvestedDatasetSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = HarvestedDatasetFilter


class DataTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint of viewing DataTypes. Order by `data_type` field.

    list:
    Return a list of DataType. `data_type` field is searchable with case-insensitive partial matches.

    retrieve:
    Return the given DataType
    """
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    ordering_fields = ('data_type',)


class KeywordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Keywords.

    list:
    Return a list of Keywords, order by keyword. `keyword` field is searchable with case-insensitive partial matches.

    retrieve:
    Return the given Keyword
    """
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('keyword',)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Projects.

    list:
    Return a list of Projects. `title` field is searchable with case-insensitive partial matches.

    retrieve:
    Return a Project instance.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('title',)


class BasisOfRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing BasisOfRecords. Order by `basis_of_record` field.

    list:
    Return a list of BasisOfRecord instances. `basis_of_record` field is searchable with case-insensitive partial
    matches.

    retrieve:
    Return the given BasisOfRecord
    """
    queryset = BasisOfRecord.objects.all()
    serializer_class = BasisOfRecordSerializer
    ordering_fields = ('basis_of_record',)


class PublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Publishers. Order by `publisher_name`.

    list:
    Return a list of Publisher instances. `publisher_name` field is searchable with case-insensitive partial matches.

    retrieve:
    Return the given Publisher
    """
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('publisher_name',)
    ordering_fields = ('publisher_name',)


class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Datasets. Order by `filtered_record_count`.

    list:
    Return a list of Dataset instances

    retrieve:
    Return the given Dataset
    """
    queryset = Dataset.objects.all().prefetch_related('data_type', 'publisher', 'keyword_set', 'project')
    serializer_class = DatasetSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = DatasetFilter
    ordering_fields = ('filtered_record_count',)


class ProjectPersonnelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Project personnel.

    list:
    Return a list of Project personnel.

    retrieve:
    Return the given Project personnel.
    """
    queryset = Person.objects.filter(personTypeRole__person_type='personnel', personTypeRole__project__isnull=False)\
        .annotate(count=Count('id'))  # annotate(count=Count('id')) for distinct record
    serializer_class = ProjectPersonnelSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('full_name',)


class OccurrenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Occurrences.

    list:
    Return a list of Occurrence instances.

    retrieve:
    Return the given Occurrence.
    """
    queryset = GBIFOccurrence.objects.all()
    serializer_class = OccurrenceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = OccurrenceFilter


class DownloadListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for creating and viewing Downloads.\

    list:
    Return a list of Download instances created by this user.

    create:
    Create a Download request.
    """
    queryset = Download.objects.filter(created_at__gt=datetime.now() - timedelta(days=7))
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = DownloadSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Called by CreateModelMixin. Only save object at view because user is not part of the request data
        """
        return serializer.save(user=self.request.user)


class DownloadRetrieveDestroyAPIView(generics.RetrieveDestroyAPIView):
    """
    API endpoint for retrieving and deleting Downloads.\

    retrieve:
    Return the given Download

    destroy:
    Delete the given Download
    """
    queryset = Download.objects.filter(created_at__gt=datetime.now() - timedelta(days=7))
    permission_classes = [IsAuthenticatedAndIsOwner, ]  # object level permission
    serializer_class = DownloadSerializer

    def perform_destroy(self, instance):
        return instance.delete()  # also delete the physical file generated
