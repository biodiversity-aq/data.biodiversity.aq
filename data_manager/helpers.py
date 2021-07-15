# -*- coding: utf-8 -*-
from data_manager.forms import DatasetFilterForm, OccurrenceFilterForm
from data_manager.models import Download
from django.apps import apps
from django.contrib.postgres.search import SearchQuery
from django.conf import settings
from django.core.files import File
from django.db import connection
from django.db.models import Count
from pygbif import species
import csv
import logging
import os
import psycopg2
import tempfile
import zipfile


# LOGGING CONFIGURATION
logger = logging.getLogger(__name__)


class MailNotSent(Exception):
    """Exception to raise when email is not sent"""
    pass


class CouldNotCreateDownload(Exception):
    """Exception to raise when fail to create download file"""
    pass


def count_occurrence_per_hexgrid():
    """Compute number of occurrences per hexagon grid for all sizes using raw sql queries

    Connect to database, create a join table with fields:
    HexGrid.geom, HexGrid.size, occ_count (count of GBIFOccurrence.geopoint for the HexGrid.geom), category

    category is derived from range of occ_count so that it's easier to style the hexagons when rendered on map:
        occ_count = 0; category = 0
        1 <= occ_count < 10; category = 1
        10 <= occ_count < 100; category = 2
        100 <= occ_count < 1000; category = 3
        1000 <= occ_count < 10000; category = 4
        10000 <= occ_count < 100000; category = 5
        occ_count > 100000; category = 6
    Details about HexGrid, please see data_manager.models.HexGrid.

    Example::

    from data_manager.helpers import count_occurrence_per_hexgrid

    count_occurrence_per_hexgrid()

    ::

    # Go to  psql of database data_biodiversity_aq

    psql data_biodiversity_aq

    SELECT * FROM hexagon_grid_counts_all LIMIT 1;
    -[ RECORD 1 ]-------------------------------------------------
    geom      | 0106000020D70B00000100000001030000000100000007000000FA6266B517FB54C1F8441BB65ED233415877945DB6A954C1C0
                1390583006364114A0F0ADF30654C1C01390583006364172B41E5692B553C1F8441BB65ED2334114A0F0ADF30654C13076A613
                8D9E31415877945DB6A954C13076A6138D9E3141FA6266B517FB54C1F8441BB65ED23341
    size      | 250000
    occ_count | 27
    category  | 2

    :raises: psycopg2.Error
    :return: None
    """
    connection.close()
    conn = psycopg2.connect("dbname={} user={} password={} host={}".format(
        settings.DATABASES['default']['NAME'], settings.DATABASES['default']['USER'],
        settings.DATABASES['default']['PASSWORD'], settings.DATABASES['default']['HOST']))
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS hexagon_grid_counts_all;")
            cursor.execute(
                "CREATE TABLE hexagon_grid_counts_all AS ("
                "SELECT data_manager_hexgrid.geom, data_manager_hexgrid.size, COUNT(*) AS occ_count FROM "
                "data_manager_hexgrid INNER JOIN data_manager_gbifoccurrence ON "
                "ST_within(ST_Transform(data_manager_gbifoccurrence.geopoint, 3031), data_manager_hexgrid.geom) "
                "GROUP BY data_manager_hexgrid.geom, data_manager_hexgrid.size);"
            )
            cursor.execute(
                "ALTER TABLE hexagon_grid_counts_all ADD category integer;"
            )
            cursor.execute(
                "UPDATE hexagon_grid_counts_all "
                "SET category = CASE "
                "WHEN occ_count >= 1 AND occ_count < 10 THEN 1 "
                "WHEN occ_count > 10 AND occ_count <= 100 THEN 2 "
                "WHEN occ_count > 100 AND occ_count <= 1000 THEN 3 "
                "WHEN occ_count > 1000 AND  occ_count <= 10000 THEN 4 "
                "WHEN occ_count > 10000 AND occ_count <= 100000 THEN 5 "
                "WHEN occ_count > 100000 THEN 6 "
                "ELSE 0 "
                "END;"
            )
    except psycopg2.Error as e:
        logger.error(e)
        pass
    return


def get_dataset_queryset_from_form(request):
    """Get Dataset queryset from DatasetFilterForm

    Filter Dataset Queryset based on the form field selected by user.

    :param request: QueryDict - a HTTP GET request
    :return: Dataset queryset and DatasetFilterForm populated with corresponding form queryset

    """
    Dataset = apps.get_model(app_label='data_manager', model_name='Dataset')
    DataType = apps.get_model(app_label='data_manager', model_name='DataType')
    Keyword = apps.get_model(app_label='data_manager', model_name='Keyword')
    Person = apps.get_model(app_label='data_manager', model_name='Person')
    Publisher = apps.get_model(app_label='data_manager', model_name='Publisher')
    qs = Dataset.objects.all()
    form = DatasetFilterForm(request, initial=request)
    # keyword choices cannot be empty
    keywords_qs = Keyword.objects.filter(dataset__in=qs).values('keyword').annotate(count=Count('keyword'))
    keywords = [(q['keyword'], q['keyword']) for q in keywords_qs]
    form.fields['keyword'].choices = keywords  # zip(keywords, keywords)
    if form.is_valid():
        # form only have cleaned_data attribute after is_valid() is called
        q = form.cleaned_data.get('q', '')
        data_type = form.cleaned_data.get('data_type', '')
        keyword = form.cleaned_data.get('keyword', '')
        project = form.cleaned_data.get('project', '')
        project_contact = form.cleaned_data.get('project_contact', '')
        publisher = form.cleaned_data.get('publisher', '')
        # filter search results by chaining queryset
        if q:
            # Ranking search results (SearchRank) imposes high cost
            qs = qs.filter(eml_text__icontains=q)
        if data_type:
            qs = qs.filter(data_type_id__in=data_type)
        if keyword:
            # group by id, remove duplicates
            qs = qs.filter(keyword__keyword__in=keyword).annotate(count=Count('keyword'))
        if project:
            qs = qs.filter(project__title__search=project)
        if project_contact:
            qs = qs.filter(personTypeRole__person_type='personnel', personTypeRole__person_id__in=project_contact)
        if publisher:
            qs = qs.filter(publisher_id__in=publisher)
    # populate queryset for form field based on the queryset of full text search
    keywords_qs = Keyword.objects.filter(dataset__in=qs).values('keyword').annotate(count=Count('keyword'))
    keywords = [(q['keyword'], q['keyword']) for q in keywords_qs]
    form.fields['keyword'].choices = keywords  # list of (keywords, keywords) tuples
    form.fields['data_type'].queryset = DataType.objects.filter(dataset__in=qs).annotate(count=Count('id'))
    form.fields['publisher'].queryset = Publisher.objects.filter(dataset__in=qs).annotate(count=Count('id'))
    form.fields['project_contact'].queryset = Person.objects.filter(
        personTypeRole__person_type='personnel', personTypeRole__dataset__in=qs).annotate(count=Count('id'))
    return qs, form


def get_occurrence_queryset_from_form(get_request):
    """
    Return GBIFOccurrence instances filtered by form with GET request
    :param get_request: QueryDict - a HTTP GET request
    :return: A tuple of filtered GBIFOccurrence queryset, form populated with GET request,
    decimal latitude range and decimal longitude range
    """
    # GBIFOccurrence filter form
    form = OccurrenceFilterForm(get_request)
    # full queryset
    BasisOfRecord = apps.get_model(app_label='data_manager', model_name='BasisOfRecord')
    Dataset = apps.get_model(app_label='data_manager', model_name='Dataset')
    GBIFOccurrence = apps.get_model(app_label='data_manager', model_name='GBIFOccurrence')
    if form.is_valid():
        q = form.cleaned_data.get('q', '')
        dataset = form.cleaned_data.get('dataset', '')
        basis_of_record = form.cleaned_data.get('basis_of_record', '')
        decimal_latitude = form.cleaned_data.get('decimal_latitude', '')
        decimal_longitude = form.cleaned_data.get('decimal_longitude', '')
        taxon = form.cleaned_data.get('taxon', '')
        qs = GBIFOccurrence.objects.all()
        # filter search by chaining queryset
        if q:
            qs = qs.filter(row_json_text__icontains=q)
        if dataset:
            qs = qs.filter(dataset_id=dataset)
        if basis_of_record:
            qs = qs.filter(basis_of_record__id__in=basis_of_record)
        if decimal_latitude:
            qs = qs.filter(decimalLatitude__contained_by=decimal_latitude)
        if decimal_longitude:
            qs = qs.filter(decimalLongitude__contained_by=decimal_longitude)
        if taxon:
            # AQ OCCURRENCES
            taxon_result = species.name_usage(key=taxon)
            rank = taxon_result.get('rank')  # rank returned is uppercase
            if rank in ['KINGDOM', 'PHYLUM', 'CLASS', 'ORDER', 'FAMILY', 'GENUS', 'SUBGENUS', 'SPECIES']:
                rank = rank.lower()
                field = '{}Key'.format(rank)
                kwargs = {'{}'.format(field): taxon}
                qs = qs.filter(**kwargs)
        # form fields queryset
        form.fields['basis_of_record'].queryset = BasisOfRecord.objects.all()
        form.fields['dataset'].queryset = Dataset.objects.all()
        return qs, form, decimal_latitude, decimal_longitude


def write_file(queryset, field_names, download, prepare_download_id):
    """
    Write Download file
    :param queryset: GBIFOccurrence Queryset
    :param field_names: a list of field names of GBIFOccurrence instances
    :param download: a Download instance
    :param prepare_download_id: UUID of prepare_download task
    :return:
    """
    csv_file_name = '{}.csv'.format(prepare_download_id)
    zip_file_name = '{}.zip'.format(prepare_download_id)
    download.task_id = prepare_download_id
    download.record_count = queryset.count()
    download.save()
    datasets = set()
    # write regular files in temporary dictionary
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file_path = os.path.join(tmpdir, csv_file_name)
        zip_file_path = os.path.join(tmpdir, zip_file_name)
        with open(os.path.join(tmpdir, csv_file_name), 'w+', encoding='utf-8', newline='') as outfile:
            # create a plain csv in the tmp dir with the requested occurrences
            writer = csv.writer(outfile)
            writer.writerow(field_names)
            for occ in queryset.iterator():
                datasets.add(occ.dataset)
                # Because all strings are returned from the database as str objects, model fields that are character
                # based (CharField, TextField, URLField, etc.) will contain Unicode values when Django retrieves data
                # from the database. This is always the case, even if the data could fit into an ASCII bytestring.
                writer.writerow(occ.to_csv_tuple())
        with zipfile.ZipFile(zip_file_path, mode='w') as zf:
            # write csv file above into ZipFile, arcname specifies the name of the csv file within this ZipFile
            zf.write(csv_file_path, arcname=csv_file_name, compress_type=zipfile.ZIP_DEFLATED)
        with open(zip_file_path, 'rb') as zf:
            download.file.save(zip_file_name, File(zf), save=True)
        download.dataset.set(datasets)
    return


def create_download_file(queryset, field_names, download):
    """
    todo: To be deprecated in the future.
    Create a zip file of a csv file, save it as Download instance.
    """
    task_id = download.task_id
    csv_file_name = '{}.csv'.format(task_id)
    zip_file_name = '{}.zip'.format(task_id)
    datasets = set()
    # write regular files in temporary dictionary
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file_path = os.path.join(tmpdir, csv_file_name)
        zip_file_path = os.path.join(tmpdir, zip_file_name)
        with open(os.path.join(tmpdir, csv_file_name), 'w+', encoding='utf-8', newline='') as outfile:
            # create a plain csv in the tmp dir with the requested occurrences
            writer = csv.writer(outfile)
            writer.writerow(field_names)
            for occ in queryset.iterator():
                datasets.add(occ.dataset)
                # Because all strings are returned from the database as str objects, model fields that are character
                # based (CharField, TextField, URLField, etc.) will contain Unicode values when Django retrieves data
                # from the database. This is always the case, even if the data could fit into an ASCII bytestring.
                writer.writerow(occ.to_csv_tuple())
        with zipfile.ZipFile(zip_file_path, mode='w') as zf:
            # write csv file above into ZipFile, arcname specifies the name of the csv file within this ZipFile
            zf.write(csv_file_path, arcname=csv_file_name, compress_type=zipfile.ZIP_DEFLATED)
        with open(zip_file_path, 'rb') as zf:
            download.file.save(zip_file_name, File(zf), save=True)
        download.dataset.set(datasets)
    return download


def vacuum():
    """Vacuum analyze database"""
    try:
        conn = psycopg2.connect("dbname={} user={} password={} host={}".format(
            settings.DATABASES['default']['NAME'], settings.DATABASES['default']['USER'],
            settings.DATABASES['default']['PASSWORD'], settings.DATABASES['default']['HOST']))
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        conn.cursor().execute("VACUUM ANALYZE;")
        logger.info("Vacuum performed")
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
        conn.close()
    except Exception as e:
        logger.error(e)
        pass
    return
