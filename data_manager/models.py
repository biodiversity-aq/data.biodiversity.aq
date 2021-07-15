# -*- coding: utf-8 -*-
import datetime
import os
import json
import logging
import urllib
import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from time import strftime

from data_manager.managers import PublisherManager, DatasetManager, ProjectManager, KeywordManager, \
    GBIFOccurrenceManager, GBIFVerbatimOccurrenceManager, HexGridManager, DataTypeManager, HarvestedDatasetManager, \
    BasisOfRecordManager
from django_celery_results.models import TaskResult
from pygbif import registry, occurrences

TDWG_RESOURCE = settings.TDWG_RESOURCE
GBIF_RESOURCE = settings.GBIF_RESOURCE
EML_RESOURCE = settings.EML_RESOURCE
PURL_BASE = settings.PURL_BASE

# LOGGING CONFIGURATION
logger = logging.getLogger(__name__)


# move from data_manager.helpers due to circular imports
def delete_by_batch(queryset):
    """
    Delete QuerySet by batch of 2000.
    Calling GBIFOccurrence.objects.filter(foo=bar).delete() will load all python objects into memory.
    Avoid having this in Manager method to prevent calling model.objects.delete() which delete every record in table.
    """
    count_records_to_delete = queryset.count()
    if count_records_to_delete > 0:
        if count_records_to_delete > 2000:
            offset = list(range(0, count_records_to_delete, 2000))
            for i in offset:
                queryset.filter(pk__in=queryset.values_list('pk')[:i + 2000]).delete()
        queryset.delete()
    return


class HarvestedDataset(models.Model):
    """
    A list of all datasets on GBIF that match our query. Can be manually edited to flag
    which ones should be imported and which shouldn't.
    """
    hostingOrganizationKey = models.CharField(max_length=150, null=True, blank=True,
                                              help_text='Hosting organization UUID key')
    hostingOrganizationTitle = models.CharField(max_length=150, null=True, blank=True,
                                                help_text='Hosting organization title')
    key = models.CharField(max_length=150, unique=True, help_text='UUID of a dataset')
    license = models.TextField(null=True, blank=True, help_text='The type of license applied to the dataset')
    publishingCountry = models.CharField(max_length=150, null=True, blank=True,
                                         help_text="The country of the organization which own the dataset given as a ISO 639-1 (2 letter) country code")
    publishingOrganizationKey = models.CharField(max_length=150, null=True, blank=True,
                                                 help_text='Publishing organization UUID key')
    publishingOrganizationTitle = models.CharField(max_length=500, null=True, blank=True,
                                                   help_text='publishing organization title')
    recordCount = models.PositiveIntegerField(null=True, blank=True,
                                              help_text='The number of record associated with the dataset')
    title = models.CharField(max_length=500, null=True, blank=True, help_text='The title of the dataset')
    type = models.CharField(max_length=150, null=True, blank=True,
                            help_text='The type of dataset given in <a href="http://api.gbif.org/v1/enumeration/basic/DatasetType">DatasetType enum</a>')
    modified = models.DateField(default=datetime.date.today,
                                help_text='The last modified date time of the dataset instance')
    deleted_from_gbif = models.NullBooleanField(blank=True, null=True, default=False, db_index=True,
                                                help_text='Marked as deleted on GBIF')
    include_in_antabif = models.NullBooleanField(blank=True, null=True, default=None, db_index=True,
                                                 help_text='Flag to import the dataset into database')
    import_full_dataset = models.NullBooleanField(blank=True, null=True, default=None, db_index=True,
                                                  help_text='Flag that indicates whether the full dataset or only records within SCAR-marbin area should be imported')
    dataset = models.ForeignKey('Dataset', blank=True, null=True, on_delete=models.SET_NULL,
                                help_text='The Dataset instance associated with the HarvestedDataset instance')
    harvested_on = models.DateTimeField(auto_now_add=True, null=True, blank=True,
                                        help_text='The date time when the HarvestedDataset instance is first created')
    objects = HarvestedDatasetManager()

    def __str__(self):
        return '{} - {}'.format(self.key, self.title)

    def delete_related_objects(self):
        """Delete all objects related to this HarvestedDataset except the HarvestedDataset instance"""
        if self.dataset:
            delete_by_batch(GBIFOccurrence.objects.filter(dataset=self.dataset))
            Dataset.objects.filter(dataset_key=self.key).delete()
        return


class DataType(models.Model):
    """
    Row type of the Core used in a Darwin-Core Archive.

    Example:
        meta.xml
        --------
        <core rowType="http://rs.tdwg.org/dwc/terms/Occurrence">...</core>
        data_type in this case is the last word of the rowType link, "Occurrence".
    
    """
    data_type = models.TextField(unique=True,
                                 help_text='Row type of a Darwin-Core Archive. '
                                           'e.g.: "METADATA", "OCCURRENCE", "SAMPLING-EVENT"')
    objects = DataTypeManager()

    class Meta:
        ordering = ['data_type']

    def __str__(self):
        return self.data_type


class Publisher(models.Model):
    """
    Publisher of a dataset.
    This information is not recorded anywhere in the darwin-core archive.
    For now, information about publisher will be retrieved using PublisherManager.
    
    Attributes:
        publisher_key: UUID of a publisher
        publisher_name: Name of publisher
        publisher_from_gbif: JSON format of information retrieved via API.
        objects: models.Manager of this class
    
    Example:
        publisher_key: "fb10a11f-4417-41c8-be6a-13a5c8535122"
        publisher_name: "Antarctic Biodiversity Information Facility (ANTABIF)"
        publisher_from_gbif:
            {   "key": "fb10a11f-4417-41c8-be6a-13a5c8535122",
                "endorsingNodeKey": "51e4e8ff-bff0-4996-8b27-9107d61b3478",
                "endorsementApproved": true,
                "title": "Antarctic Biodiversity Information Facility (ANTABIF)",
                "language": "eng",
                "numPublishedDatasets": 87,
                "createdBy": "ADMIN",
                "modifiedBy": "ADMIN",
                "created": "2011-07-13T13:40:29.000+0000",
                "modified": "2011-07-13T13:40:29.000+0000",
                "contacts": ... 
            }
    """
    publisher_key = models.TextField(unique=True,
                                     help_text='UUID of a publisher in https://api.gbif.org/v1/organization/')
    publisher_name = models.TextField(blank=True,
                                      help_text='Name of a publisher in https://api.gbif.org/v1/organization/')
    publisher_from_gbif = models.TextField(default='', help_text='Response data of publisher retrieved from GBIF.')
    objects = PublisherManager()

    class Meta:
        ordering = ['publisher_name']

    def __str__(self):
        return self.publisher_name


class Person(models.Model):
    """
    The Person is used to enter two types of name parts for an individual associated with the resource.
    https://knb.ecoinformatics.org/emlparser/docs/eml-2.1.1/eml-party.html#Person
    """
    given_name = models.TextField(
        null=True, blank=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-party_xsd.html#Person_givenName'))
    surname = models.TextField(help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-party_xsd.html#Person_surName'))
    full_name = models.TextField(help_text='Concatenation of given_name and surname.')
    email = models.TextField(
        null=True, blank=True, help_text=urllib.parse.urljoin(EML_RESOURCE,
                                                              'schema/eml-party_xsd.html#ResponsibleParty_electronicMailAddress'))

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class PersonTypeRole(models.Model):
    """

    """
    person_type = models.TextField()
    role = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-party_xsd.html#RoleType'))
    organization = models.TextField(
        blank=True, null=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-party_xsd.html#ResponsibleParty_organizationName'))
    dataset = models.ForeignKey('Dataset', related_name='personTypeRole', blank=True, null=True,
                                on_delete=models.CASCADE)
    person = models.ForeignKey('Person', related_name='personTypeRole', blank=True, null=True, on_delete=models.CASCADE)
    project = models.ForeignKey('Project', related_name='personTypeRole', blank=True, null=True,
                                on_delete=models.CASCADE)

    def __str__(self):
        return 'person_type: {}, role: {}, dataset: {}'.format(self.person_type, self.role, self.dataset)


class Dataset(models.Model):
    """
    EML of a Darwin-Core Archive
    https://eml.ecoinformatics.org/
    """
    project = models.ForeignKey(
        'Project', related_name='dataset', blank=True, null=True, on_delete=models.CASCADE,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-project_xsd.html'))
    publisher = models.ForeignKey(
        'Publisher', related_name='dataset', blank=True, null=True, on_delete=models.SET_NULL,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-dataset_xsd.html#DatasetType_publisher'))
    data_type = models.ForeignKey(
        'DataType', related_name='dataset', blank=True, null=True, on_delete=models.SET_NULL,
        help_text='Row type of a Darwin-Core Archive. e.g.: "METADATA", "OCCURRENCE", "SAMPLING-EVENT"'
    )
    dataset_key = models.TextField(unique=True,
                                   help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml_xsd.html#eml_packageId'))
    alternate_identifiers = ArrayField(
        models.TextField(blank=True), blank=True, null=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-resource_xsd.html#ResourceGroup_alternateIdentifier')
    )
    doi = models.TextField(blank=True, null=True, help_text='doi that uniquely identify this dataset')
    title = models.TextField(
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-resource_xsd.html#ResourceGroup_title'))
    bounding_box = models.PolygonField(
        null=True, blank=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-coverage_xsd.html#Coverage_geographicCoverage'))
    download_on = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    modified = models.DateTimeField(auto_now=True, auto_now_add=False, null=True, blank=True)
    created = models.DateTimeField(auto_now=False, auto_now_add=True, null=True, blank=True)
    pub_date = models.DateField(auto_now=False, auto_now_add=False, null=True, blank=True,
                                help_text=urllib.parse.urljoin(EML_RESOURCE,
                                                               'schema/eml-resource_xsd.html#ResourceGroup_pubDate'))
    intellectual_right = models.TextField(
        blank=True, null=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-resource_xsd.html#ResourceGroup_intellectualRights'))
    abstract = models.TextField(
        blank=True, null=True,
        help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml-resource_xsd.html#ResourceGroup_abstract'))
    citation = models.TextField(blank=True, null=True,
                                help_text=urllib.parse.urljoin(EML_RESOURCE, 'schema/eml_xsd.html#eml_citation'))
    eml_text = models.TextField(default='')
    tag = ArrayField(models.TextField(blank=True), blank=True, null=True,
                     help_text='an array of texts to tag a dataset')
    filtered_record_count = models.IntegerField(blank=True, null=True, default=0,
                                                help_text='the number of darwin core records associated with this '
                                                          'dataset imported into the database')
    deleted_record_count = models.IntegerField(blank=True, null=True, default=0,
                                               help_text='the number of darwin core records associated with this '
                                                         'dataset not imported into the database')
    full_record_count = models.IntegerField(blank=True, null=True,
                                            help_text='the total number of darwin core records associated with this '
                                                      'dataset before imported into the database')
    percentage_records_retained = models.FloatField(blank=True, null=True, default=100,
                                                    help_text='the percentage of records associated with this dataset '
                                                              'imported into the database, derived using '
                                                              'filtered_record_count/full_record_count*100')
    objects = DatasetManager()

    class Meta:
        ordering = ['-filtered_record_count']

    def __str__(self):
        return self.title

    def get_keywords(self):
        return ', '.join([x.keyword for x in self.keyword_set.all()])

    def count_occurrence_per_dataset(self):
        """
        Update the count for GBIFOccurrence associated with this dataset.
        :return: None
        """
        occ_count = self.GBIFOccurrence.count()
        full_count = occurrences.search(datasetKey=self.dataset_key).get('count', 0)
        del_count = full_count - occ_count
        self.full_record_count = full_count
        self.filtered_record_count = occ_count
        self.deleted_record_count = del_count
        if del_count == 0:
            self.percentage_records_retained = 100
        else:
            self.percentage_records_retained = round(occ_count / (full_count + 1) * 100, 3)  # +1 to avoid division by 0
        self.save()
        return

    def has_new_version(self):
        """
        Check if Dataset is modified on GBIF.
        :return: Union [bool, str]
        """
        response = registry.datasets(uuid=self.dataset_key)
        modified_timestamp = response.get('modified', None)  # dataset does not necessarily has timestamp
        if self.deleted_on_gbif():
            return False
        if modified_timestamp:
            modified_on = parse_datetime(modified_timestamp)
            modified_datetime = modified_on.replace(tzinfo=None)
            if modified_datetime > self.download_on:  # raise TypeError if dataset.download_on is None
                return True
        return False  # not deleted, no modified timestamp

    def deleted_on_gbif(self):
        """
        Check if a dataset has "deleted" timestamp in GBIF.
        Flag HarvestedDataset deleted_from_gbif=True and include_in_antabif=False if Dataset is deleted on GBIF.
        :return: (Boolean) True if dataset is deleted on GBIF, else False.
        """
        # ensure that self.dataset_key is a valid uuid, because if dataset_key is None, response will return all
        # datasets
        uuid.UUID(self.dataset_key)  # raise ValueError if dataset_key is not a proper UUID
        response = registry.datasets(uuid=self.dataset_key)
        deleted = response.get('deleted', False)
        if deleted:
            self.harvesteddataset_set.update(deleted_from_gbif=True, include_in_antabif=False)
            return True
        else:
            return False


class Project(models.Model):
    """
    Research context information for Datasets
    https://knb.ecoinformatics.org/emlparser/docs/eml-2.1.1/eml-project.html
    """
    title = models.TextField(help_text=urllib.parse.urljoin(EML_RESOURCE, 'eml-project.html#title'))
    funding = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(EML_RESOURCE, 'eml-project.html#funding'))
    objects = ProjectManager()

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Keyword(models.Model):
    """
    The container for the 'keyword' and 'keywordThesaurus' fields
    https://knb.ecoinformatics.org/emlparser/docs/eml-2.1.1/eml-resource.html#keywordSet
    """
    keyword = models.TextField(help_text=urllib.parse.urljoin(EML_RESOURCE,
                                                              'schema/eml-resource_xsd.html#ResourceGroup_ResourceGroup_keywordSet_keyword'))
    thesaurus = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(EML_RESOURCE,
                                                              'schema/eml-resource_xsd.html#ResourceGroup_ResourceGroup_keywordSet_keywordThesaurus'))
    dataset = models.ManyToManyField('Dataset', blank=True)
    objects = KeywordManager()

    class Meta:
        ordering = ['keyword']

    def __str__(self):
        return self.keyword


class BasisOfRecord(models.Model):
    basis_of_record = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'basisOfRecord'))
    objects = BasisOfRecordManager()

    class Meta:
        ordering = ('basis_of_record',)

    def human_readable_basis_of_record(self):
        """
        By default, basisOfRecord from GBIF occurrence.txt are in upper case separated by underscore.
        e.g. HUMAN_OBSERVATION
        This function transform the value to lower case, separated by space
        e.g. human observation
        """
        if self.basis_of_record:
            return self.basis_of_record.replace('_', ' ')

    def __str__(self):
        return self.basis_of_record


class HexGrid(models.Model):
    """
    Hexagon grid
    QGIS was used to generate these shape files using MMQGIS

    The shape files contain these fields in EPSG:3031 projection:
    left, bottom, right, top, geom

    size is a label used to describe the size of grids
    """
    left = models.FloatField(null=True, db_index=True)
    bottom = models.FloatField(null=True, db_index=True)
    right = models.FloatField(null=True, db_index=True)
    top = models.FloatField(null=True, db_index=True)
    geom = models.MultiPolygonField(srid=3031)
    size = models.IntegerField(null=True, db_index=True)
    objects = HexGridManager()

    def __str__(self):
        return '{}'.format(self.pk)


class DarwinCoreOccurrence(models.Model):
    _type = models.TextField("type", blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'type'))
    license = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'license'))
    rightsHolder = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'rightsHolder'))
    accessRights = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'accessRights'))
    bibliographicCitation = models.TextField(blank=True, null=True,
                                             help_text=urllib.parse.urljoin(PURL_BASE, 'bibliographicCitation'))
    references = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'references'))
    datasetID = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'datasetID'))
    institutionCode = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'institutionCode'))
    collectionID = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'collectionID'))
    collectionCode = models.TextField(blank=True, null=True,
                                      help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'collectionCode'))
    institutionID = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'institutionID'))
    datasetName = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'datasetName'))
    dynamicProperties = models.TextField(blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'dynamicProperties'))

    # Occurrence
    occurrenceID = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'occurrenceID'))
    catalogNumber = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'catalogNumber'))
    recordedBy = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'recordedBy'))
    individualCount = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'individualCount'))
    organismQuantity = models.TextField(blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'organismQuantity'))
    organismQuantityType = models.TextField(blank=True, null=True,
                                            help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'organismQuantityType'))
    sex = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'sex'))
    lifeStage = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'lifeStage'))
    reproductiveCondition = models.TextField(blank=True, null=True,
                                             help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'reproductiveCondition'))
    behavior = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'behavior'))
    occurrenceStatus = models.TextField(db_index=False, blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'occurrenceStatus'))
    occurrenceRemarks = models.TextField(blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'occurrenceRemarks'))
    associatedReferences = models.TextField(blank=True, null=True,
                                            help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'associatedReferences'))
    associatedSequences = models.TextField(blank=True, null=True,
                                           help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'associatedSequences'))

    # MaterialSample | LivingSpecimen | PreservedSpecimen | FossilSpecimen
    materialSampleID = models.TextField(blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'materialSampleID'))

    # Event | HumanObservation | MachineObservation
    eventID = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'eventID'))
    parentEventID = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'parentEventID'))
    fieldNumber = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'fieldNumber'))
    eventDate = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'eventDate'))
    eventTime = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'eventTime'))
    verbatimEventDate = models.TextField(blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimEventDate'))
    samplingProtocol = models.TextField(db_index=False, blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'samplingProtocol'))
    sampleSizeValue = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'sampleSizeValue'))
    sampleSizeUnit = models.TextField(blank=True, null=True,
                                      help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'sampleSizeUnit'))
    samplingEffort = models.TextField(blank=True, null=True,
                                      help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'samplingEffort'))
    fieldNotes = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'fieldNotes'))
    eventRemarks = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'eventRemarks'))

    # Location
    locationID = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'locationID'))
    continent = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'continent'))
    waterBody = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'waterBody'))
    countryCode = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'countryCode'))
    locality = models.TextField(db_index=False, blank=True, null=True,
                                help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'locality'))
    verbatimLocality = models.TextField(blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimLocality'))
    verbatimDepth = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimDepth'))
    minimumDistanceAboveSurfaceInMeters = models.TextField(blank=True, null=True,
                                                           help_text=urllib.parse.urljoin(TDWG_RESOURCE,
                                                                                          'minimumDistanceAboveSurfaceInMeters'))
    maximumDistanceAboveSurfaceInMeters = models.TextField(blank=True, null=True,
                                                           help_text=urllib.parse.urljoin(TDWG_RESOURCE,
                                                                                          'maximumDistanceAboveSurfaceInMeters'))
    locationAccordingTo = models.TextField(blank=True, null=True,
                                           help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'locationAccordingTo'))
    locationRemarks = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'locationRemarks'))
    geodeticDatum = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'geodeticDatum'))
    footprintWKT = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'footprintWKT'))
    footprintSRS = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'footprintSRS'))
    verbatimSRS = models.TextField(blank=True, null=True,
                                   help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimSRS'))
    verbatimCoordinateSystem = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimCoordinateSystem'))

    # Identification
    identificationQualifier = models.TextField(blank=True, null=True,
                                               help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'identificationQualifier'))

    # Taxon
    taxonID = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'taxonID'))
    scientificNameID = models.TextField(db_index=False, blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'scientificNameID'))
    scientificName = models.TextField(db_index=False, blank=True, null=True,
                                      help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'scientificName'))
    kingdom = models.TextField(db_index=False, blank=True, null=True,
                               help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'kingdom'))
    phylum = models.TextField(db_index=False, blank=True, null=True,
                              help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'phylum'))
    _class = models.TextField("class", db_index=False, blank=True, null=True,
                              help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'class'))
    order = models.TextField(db_index=False, blank=True, null=True,
                             help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'order'))
    family = models.TextField(db_index=False, blank=True, null=True,
                              help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'family'))
    genus = models.TextField(db_index=False, blank=True, null=True,
                             help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'genus'))
    subgenus = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'subgenus'))
    specificEpithet = models.TextField(db_index=False, blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'specificEpithet'))
    infraspecificEpithet = models.TextField(blank=True, null=True,
                                            help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'infraspecificEpithet'))
    taxonRank = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'taxonRank'))
    verbatimTaxonRank = models.TextField(blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimTaxonRank'))
    scientificNameAuthorship = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'scientificNameAuthorship'))
    taxonRemarks = models.TextField(blank=True, null=True,
                                    help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'taxonRemarks'))

    class Meta:
        abstract = True


class GBIFOccurrence(DarwinCoreOccurrence):
    """
    model of GBIF occurrence.txt
    """
    # terms introduced by GBIF
    gbifID = models.TextField(db_index=True, unique=True, blank=True, null=True,
                              help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'gbifID'))
    basisOfRecord = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'basisOfRecord'))
    datasetKey = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'datasetKey'))
    elevation = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'elevation'))
    distanceAboveSurface = models.TextField(blank=True, null=True,
                                            help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'distanceAboveSurface'))
    issue = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'issue'))
    mediaType = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'mediaType'))
    date = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(PURL_BASE, 'date'))

    # Taxa
    taxonKey = models.TextField(db_index=True, blank=True, null=True,
                                help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'taxonKey'))
    kingdomKey = models.TextField(db_index=True, blank=True, null=True,
                                  help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'kingdomKey'))
    phylumKey = models.TextField(db_index=True, blank=True, null=True,
                                 help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'phylumKey'))
    classKey = models.TextField(db_index=True, blank=True, null=True,
                                help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'classKey'))
    orderKey = models.TextField(db_index=True, blank=True, null=True,
                                help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'orderKey'))
    familyKey = models.TextField(db_index=True, blank=True, null=True,
                                 help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'familyKey'))
    genusKey = models.TextField(db_index=True, blank=True, null=True,
                                help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'genusKey'))
    subgenusKey = models.TextField(db_index=True, blank=True, null=True,
                                   help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'subgenusKey'))
    speciesKey = models.TextField(db_index=True, blank=True, null=True,
                                  help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'speciesKey'))

    # Geological
    decimalLatitude = models.FloatField(db_index=True, blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'decimalLatitude'))
    decimalLongitude = models.FloatField(db_index=True, blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'decimalLongitude'))
    coordinateUncertaintyInMeters = models.FloatField(blank=True, null=True,
                                                      help_text=urllib.parse.urljoin(TDWG_RESOURCE,
                                                                                     'coordinateUncertaintyInMeters'))  # not used
    coordinatePrecision = models.FloatField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE,
                                                                                                  'coordinatePrecision'))  # not used
    # GeoDjango specific fields
    geopoint = models.PointField(blank=True, null=True, srid=4326)  # default SRID = 4326 (WGS84)

    # DateTimeField
    modified = models.TextField(blank=True, null=True, default=None,
                                help_text=urllib.parse.urljoin(PURL_BASE, 'modified'))
    year = models.PositiveSmallIntegerField(blank=True, null=True, db_index=True,
                                            help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'year'))
    month = models.PositiveSmallIntegerField(validators=[MaxValueValidator(12), MinValueValidator(1)], db_index=True,
                                             blank=True, null=True,
                                             help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'month'))
    day = models.PositiveSmallIntegerField(validators=[MaxValueValidator(31), MinValueValidator(1)], db_index=True,
                                           blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'day'))
    # A time stamp that states when is this entry created and last modified
    # date of the entry created/last modified in THIS (data.biodiversity.aq) database
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)
    # GBIF does not have maximumDepthInMeters nor minimumDepthInMeters
    depth = models.FloatField(db_index=True, blank=True, null=True,
                              help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'depth'))
    row_json_text = models.TextField(blank=True, null=True)
    # foreign key: on_delete=CASCADE is default
    dataset = models.ForeignKey(Dataset, related_name="GBIFOccurrence", null=True, on_delete=models.CASCADE)
    basis_of_record = models.ForeignKey(BasisOfRecord, related_name="GBIFOccurrence", null=True,
                                        on_delete=models.SET_NULL)
    hexgrid = models.ManyToManyField(HexGrid, related_name="GBIFOccurrence")
    # add dataset title here, faster performance
    dataset_title = models.TextField(blank=True, null=True)
    # manager
    objects = GBIFOccurrenceManager()

    def __str__(self):
        return '{}--{}'.format(self.scientificName, self.gbifID)

    def human_readable_basis_of_record(self):
        if self.basisOfRecord:
            return self.basisOfRecord.replace('_', ' ').lower()
        else:
            return ''

    def toJSON(self):
        return {
            'id': self.id,
            'scientificName': self.scientificName,
            'taxonKey': self.taxonKey,
            'decimalLatitude': self.decimalLatitude,
            'decimalLongitude': self.decimalLongitude,
            'year': self.year,
            'month': self.month,
            'basisOfRecord': self.human_readable_basis_of_record(),
            'datasetId': self.dataset_id,
            'datasetTitle': self.dataset_title,
            'institutionCode': self.institutionCode,
            'collectionCode': self.collectionCode,
            'locality': self.locality
        }

    def to_csv_tuple(self):
        return [self.__getattribute__(x) for x in settings.OCCURRENCE_FIELDS]


class GBIFVerbatimOccurrence(DarwinCoreOccurrence):
    """
    model of GBIF verbatim.txt
    verbatim.txt has some fields from darwin core but not in gbif occurrence.txt
    inherit gbif occurrence
    """
    gbifID = models.TextField(db_index=True, unique=True, blank=True, null=True,
                              help_text=urllib.parse.urljoin(GBIF_RESOURCE, 'gbifID'))
    basisOfRecord = models.TextField(blank=True, null=True,
                                     help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'basisOfRecord'))
    country = models.TextField(blank=True, null=True,
                               help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'country'))  # not in GBIF occurrence.txt
    decimalLatitude = models.TextField(blank=True, null=True,
                                       help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'decimalLatitude'))
    decimalLongitude = models.TextField(blank=True, null=True,
                                        help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'decimalLongitude'))
    coordinateUncertaintyInMeters = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'coordinateUncertaintyInMeters'))
    coordinatePrecision = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'coordinatePrecision'))
    modified = models.TextField(blank=True, null=True, default=None,
                                help_text=urllib.parse.urljoin(PURL_BASE, 'modified'))
    year = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'year'))
    month = models.TextField(blank=True, null=True,
                             help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'month'))
    day = models.TextField(blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'day'))
    minimumElevationInMeters = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'minimumElevationInMeters'))  # not in gbif
    maximumElevationInMeters = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'maximumElevationInMeters'))  # not in gbif
    verbatimElevation = models.TextField(blank=True, null=True,
                                         help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'verbatimElevation'))
    minimumDepthInMeters = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'minimumDepthInMeters'))  # not in gbif
    maximumDepthInMeters = models.TextField(
        blank=True, null=True, help_text=urllib.parse.urljoin(TDWG_RESOURCE, 'maximumDepthInMeters'))  # not in gbif
    occurrence = models.ForeignKey(
        'GBIFOccurrence', null=True, blank=True, on_delete=models.CASCADE
    )

    # manager
    objects = GBIFVerbatimOccurrenceManager()

    def __str__(self):
        return self.gbifID


class Download(models.Model):
    """
    A Download based on a query from a User
    """

    def get_generated_file_dir(self, filename):
        """
        leaving this function in here for not breaking the migration files
        but this function is not used anymore in the app
        """
        return strftime('downloads/%Y/%m/%d/{}_{}'.format(self.user.username, filename))

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=100, blank=True, null=True)  # corresponds to task_id in TaskResult model
    file = models.FileField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dataset = models.ManyToManyField('Dataset', related_name='Download', blank=True)
    query = models.TextField(blank=True, null=True)
    record_count = models.IntegerField(null=True, blank=True)  # number of occurrence records

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.task_id

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        super(Download, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Deleting Download record also delete its physical file and TaskResult associated with the Download.
        """
        task_result = TaskResult.objects.filter(task_id=self.task_id)
        if task_result.exists():
            task_result.delete()
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super(Download, self).delete(*args, **kwargs)

    def query_string_to_dict(self):
        """
        Convert the string query values into dict
        """
        if self.query:
            double_quoted_query = self.query.replace("\'", "\"")
            dictionary = json.loads(double_quoted_query)
        else:
            dictionary = {}
        return dictionary

    def get_query_dict(self):
        """
        Create a QueryDict instance from string to be passed to FilterSet instance
        """
        query_dict = QueryDict('', mutable=True, encoding='utf-8')
        if self.query:
            d = self.query_string_to_dict()
            for key, values in d.items():
                if isinstance(values, list):
                    for item in values:
                        query_dict.appendlist(key, item)
                else:
                    query_dict.appendlist(key, values)
        return query_dict
