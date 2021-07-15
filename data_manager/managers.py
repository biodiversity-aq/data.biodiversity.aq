# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.parser import parse
from django.apps import apps
from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.contrib.gis.utils import LayerMapping
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.core.validators import URLValidator
from django.db.utils import IntegrityError
from pygbif import registry, occurrences
from requests.exceptions import HTTPError
import defusedxml.ElementTree as ET
import logging
import os
import re
import requests

# LOGGING CONFIGURATION
logger = logging.getLogger('import_datasets')


class DataTypeManager(models.Manager):

    def create_from_gbif_api(self, dataset_key):
        """Get or create DataType from GBIF API"""
        eml_json = registry.datasets(uuid=dataset_key)
        data_type = eml_json.get('type', 'Unknown')
        # convert to title case and replace '_' with ' ' if exists
        data_type = data_type.title().replace('_', ' ')
        try:
            data_type_object = self.get_or_create(data_type=data_type)[0]
        except MultipleObjectsReturned:
            data_type_object = self.get(data_type=data_type)
        return data_type_object


class PublisherManager(models.Manager):
    """
    Manage Publisher object
    """

    def from_gbif_api(self, gbif_dataset_key):
        """
        Create Publisher object based on information retrieved from GBIF API.
        Publisher is not found in EML and hence the information can only be obtained via GBIF API.

        :param gbif_dataset_key: GBIF UUID of a dataset (e.g. 7b5b300c-f762-11e1-a439-00145eb45e9a)
        :return: Publisher object
        """
        dataset_from_gbif = {}
        publisher = None
        # ---------------------
        # get DATASET metadata
        # ---------------------
        r = requests.get(os.path.join('https://api.gbif.org/v1/dataset', gbif_dataset_key))
        if r.status_code == 200:
            # convert response to json format
            dataset_from_gbif = r.json()
        # obtain publisher key - publisher's name is not recorded in dataset meta data
        gbif_publisher_key = dataset_from_gbif.get('publishingOrganizationKey', '')
        # -----------------------
        # get PUBLISHER metadata
        # -----------------------
        # if gbif_publisher_key is not empty
        if gbif_publisher_key:
            # get the information of publisher
            r = requests.get(os.path.join('https://api.gbif.org/v1/organization', gbif_publisher_key))
            # convert response to json format
            publisher_from_gbif = r.json()
            # get publisher name
            publisher_name = publisher_from_gbif.get('title', '')
            # create publisher object
            publisher = self.update_or_create(publisher_key=gbif_publisher_key,
                                              defaults={'publisher_name': publisher_name,
                                                        'publisher_from_gbif': publisher_from_gbif})[0]
        return publisher


class DatasetManager(models.Manager):
    """Manage Dataset object"""
    def from_gbif_dwca_eml(self, eml_tree, dataset_uuid, project_object):
        """
        Create Dataset object based on information from GBIF EML.

        :param eml_tree: A xml Element object of EML (use defusedxml library).
        :param project_object: A Project object created using Django API.
        :return: Dataset object created using Django API
        """
        # initialise variables
        doi = ''
        bounding_box = GEOSGeometry(Polygon.from_bbox((0, 0, 0, 0)))
        # attribute.text
        try:
            alternate_identifiers_raw = eml_tree.findall('.dataset/alternateIdentifier')
            alternate_identifiers = [identifier.text for identifier in alternate_identifiers_raw]
        except AttributeError:
            alternate_identifiers = []
        if alternate_identifiers:
            doi = alternate_identifiers[0]
        try:
            title = eml_tree.find('.dataset/title').text  # required field
        except AttributeError:
            title = ''
        try:
            intellectual_right = eml_tree.find('.//intellectualRights/para/ulink/citetitle').text
        except AttributeError:
            intellectual_right = ''
        try:
            abstract = eml_tree.find('.//abstract/para').text
        except AttributeError:
            abstract = ''
        try:
            citation = eml_tree.find('.//citation').text
        except AttributeError:
            citation = ''
        try:
            download_on_raw = eml_tree.find('.additionalMetadata/metadata/gbif/dateStamp').text
            download_on = parse(download_on_raw.strip())  # parse_datetime(download_on_tag.text.strip())
        except AttributeError:
            download_on = datetime.now()  # should not be none
        try:  # strip white spaces and \n
            pub_date_raw = eml_tree.find('.//pubDate').text
            pub_date = parse(pub_date_raw.strip())
        except AttributeError:
            pub_date = None
        # save these coordinates as bounding box (Polygon's class method) if they exist
        for coordinate in eml_tree.findall('.//dataset/coverage/geographicCoverage/boundingCoordinates'):
            try:
                west = coordinate.find('./westBoundingCoordinate').text
            except AttributeError:
                west = 0
            try:
                east = coordinate.find('./eastBoundingCoordinate').text
            except AttributeError:
                east = 0
            try:
                north = coordinate.find('./northBoundingCoordinate').text
            except AttributeError:
                north = 0
            try:
                south = coordinate.find('./southBoundingCoordinate').text
            except AttributeError:
                south = 0
            bounding_box = GEOSGeometry(Polygon.from_bbox((west, south, east, north)))
        eml_text = ET.tostring(eml_tree, encoding='unicode', method='xml')
        # update or create dataset object
        dataset_object = self.update_or_create(dataset_key=dataset_uuid,
                                               defaults={'project': project_object,
                                                         'dataset_key': dataset_uuid,
                                                         'title': title,
                                                         'alternate_identifiers': alternate_identifiers,
                                                         'doi': doi,
                                                         'bounding_box': bounding_box,
                                                         'intellectual_right': intellectual_right,
                                                         'citation': citation,
                                                         'pub_date': pub_date,
                                                         'download_on': download_on,
                                                         'abstract': abstract,
                                                         'eml_text': eml_text,
                                                         'tag': []})[0]
        return dataset_object


class ProjectManager(models.Manager):
    """ Manage Project object """
    def from_gbif_dwca_eml(self, eml_tree):
        """
        Create Project object based on information from EML.
        Each dataset of darwin core archive can belongs to 0 or 1 project.
        :param eml_tree: A xml Element object of EML (use defusedxml library).
        :return: Project object
        """
        project_object = None
        project_title = None
        # './/project' selects all subelements, on all levels beneath the current element
        project = eml_tree.find('.//project')
        # FutureWarning: The behavior of this method will change in future versions.  Use specific 'len(elem)' or
        # 'elem is not None' test instead.
        if project is not None:
            # if project field exists, project_title should be mandatory
            try:
                project_title = project.find('.//title').text
            except AttributeError:
                pass
            try:
                # project_funding is not a mandatory field
                project_funding = project.find('.//funding/para').text
            except AttributeError:
                project_funding = ''
                pass
            if project_title:
                project_object = self.update_or_create(title=project_title, defaults={'funding': project_funding})[0]
        return project_object


class KeywordManager(models.Manager):
    """Manage Keyword object"""
    def from_gbif_dwca_eml(self, eml_tree, dataset_object):
        """
        Create Keyword object based on information from GBIF EML.
        :param eml_tree: A xml Element object of EML. (use defusedxml library)
        :param dataset_object: A Dataset object created using Django API.
        :return:
        """
        keyword_object = None
        # Keyword field is optional in eml
        for keyword_set in eml_tree.findall('.//dataset/keywordSet'):
            # If keywords field exists, both thesaurus and keyword list are required
            try:
                thesaurus = keyword_set.find('./keywordThesaurus').text
            except AttributeError:
                logger.debug('found keywordset without thesaurus')
                thesaurus = ''
            for keyword in keyword_set.findall('.//keyword'):
                try:
                    keyword = keyword.text
                except AttributeError:
                    keyword = ''
                if keyword:
                    try:
                        keyword_object = self.get_or_create(keyword=keyword, thesaurus=thesaurus)[0]
                    except MultipleObjectsReturned:
                        # delete all duplicates, only keep unique record
                        objects = self.filter(keyword=keyword, thesaurus=thesaurus)
                        object_count = objects.count()
                        for i, keyword in enumerate(objects):
                            if i != (object_count - 2) + 1:
                                keyword.delete()
                    try:
                        keyword_object.dataset.add(dataset_object)
                    except IntegrityError:  # means that the keyword is already associated with the dataset
                        pass
        return


class BasisOfRecordManager(models.Manager):
    """
    Manage BasisOfRecord instance
    """
    def create_from_row(self, interpreted_data):
        """
        Get or create BasisOfRecord object from a dwca.rows.Row object
        :param interpreted_data: Data attribute of a dwca.rows.Row object
        :return: BasisOfRecord object
        """
        help_text = self.model._meta.get_field('basis_of_record').help_text
        basis_of_record = interpreted_data.get(help_text)
        return self.get_or_create(basis_of_record=basis_of_record)[0]


class DarwinCoreManager(models.Manager):
    """
    Manage Darwin Core instances e.g. Occurrence Core.
    """
    FLOAT_FIELDS = ['decimalLatitude', 'decimalLongitude', 'coordinateUncertaintyInMeters', 'coordinatePrecision',
                    'depth']
    INTEGER_FIELDS = ['year', 'month', 'day']

    def get_uri_field_name(self):
        """
        Get a dictionary of help_text as key if help_text is a url and field_name as value.
        """
        uri_field_name_dict = dict()  # { help_text uri: field name }
        for field in self.model._meta.fields:
            try:
                # only append field help_text and name if its help_text is a proper URI
                URLValidator()(field.help_text)  # verify if help_text is a proper URI
                uri_field_name_dict[field.help_text] = field.name
            except ValidationError:
                pass
        return uri_field_name_dict

    def string_to_float(self, interpreted_data, occ_row_dict):
        """
        Convert string to float for occurrence fields that are FloatField.
        :param interpreted_data: data attribute of a dwca.rows.Row object
        :param occ_row_dict: a dictionary for the occurrence record, key = field_name, value = value of the field
        :return: occ_row_dict appended with new float fields and corresponding values
        """
        for field in self.FLOAT_FIELDS:
            help_text = self.model._meta.get_field(field_name=field).help_text
            string_value = interpreted_data.get(help_text)
            try:
                float_value = float(string_value)
            except ValueError:
                float_value = None
            occ_row_dict[field] = float_value
        return occ_row_dict

    def string_to_int(self, interpreted_data, occ_row_dict):
        """
        Convert string to integer for occurrence fields that are integer field in database.
        :param interpreted_data: data attribute of a dwca.rows.Row object
        :param occ_row_dict: a dictionary for the occurrence record, key = field_name, value = value of the field
        :return: occ_row_dict appended with new float fields and corresponding values
        """
        for field in self.INTEGER_FIELDS:
            help_text = self.model._meta.get_field(field_name=field).help_text
            string_value = interpreted_data.get(help_text)
            try:
                int_value = int(string_value)
            except ValueError:
                int_value = None
            occ_row_dict[field] = int_value
        return occ_row_dict


class GBIFOccurrenceManager(DarwinCoreManager):
    """Manage GBIFOccurrence instance"""

    def string_to_point(self, interpreted_data, occ_row_dict):
        """
        Convert string latitude, longitude to a GEOSGeometry Point object
        :param interpreted_data: data attribute of a dwca.rows.Row object
        :param occ_row_dict: a dictionary for the occurrence record, key = GBIFOccurrence field_name,
        value = value of the field
        :return: occ_row_dict appended with new float fields and corresponding values
        """
        decimal_longitude = interpreted_data.get("http://rs.tdwg.org/dwc/terms/decimalLongitude", None)
        decimal_latitude = interpreted_data.get("http://rs.tdwg.org/dwc/terms/decimalLatitude", None)
        if decimal_longitude and decimal_latitude:
            occ_row_dict['geopoint'] = GEOSGeometry('POINT({} {})'.format(decimal_longitude, decimal_latitude))
        else:
            occ_row_dict['geopoint'] = None
        return occ_row_dict

    def instantiate(self, interpreted_data, dataset_object):
        """
        Instantiate GBIFOccurrence objects
        :param interpreted_data: data attribute of a dwca.rows.Row object
        :param dataset_object: a Dataset object
        :return: instantiated GBIFOccurrence object containing data from the row
        """
        BasisOfRecord = apps.get_model(app_label='data_manager', model_name='BasisOfRecord')
        help_text_field_dict = self.get_uri_field_name()
        occ_row_dict = dict()
        for key in help_text_field_dict:  # key = uri of the field
            field_name = help_text_field_dict.get(key)
            occ_row_dict[field_name] = interpreted_data.get(key)
        # FloatField and IntegerField
        occ_row_dict = self.string_to_float(interpreted_data=interpreted_data, occ_row_dict=occ_row_dict)
        occ_row_dict = self.string_to_int(interpreted_data=interpreted_data, occ_row_dict=occ_row_dict)
        # Text search field
        occ_row_dict['row_json_text'] = list(occ_row_dict.values())
        # PointField
        occ_row_dict = self.string_to_point(interpreted_data=interpreted_data, occ_row_dict=occ_row_dict)
        # Foreign key
        occ_row_dict['basis_of_record'] = BasisOfRecord.objects.create_from_row(interpreted_data=interpreted_data)
        occ_row_dict['dataset'] = dataset_object
        occ_row_dict['dataset_title'] = dataset_object.title
        return self.model(**occ_row_dict)


class GBIFVerbatimOccurrenceManager(DarwinCoreManager):

    def verbatim_dict_from_row_data(self, verbatim_data):
        """
        Create a dictionary from a row without transforming the data (all text field)
        :param verbatim_data: data attribute of the verbatim dwca.rows.Row object
        :return: a dictionary with key=GBIFVerbatimOccurrence field name and value=data of that row
        """
        uri_field_name_dict = self.get_uri_field_name()
        verb_row_dict = dict()
        for key in uri_field_name_dict:
            field_name = uri_field_name_dict.get(key)
            verb_row_dict[field_name] = verbatim_data.get(key)
        return verb_row_dict

    def create_in_bulk(self, list_of_dict, fk_id_list):
        """
        Bulk create GBIFVerbatimOccurrence objects
        :param list_of_dict: a list of dictionary with key=GBIFVerbatimOccurrence field name and value=data
        :param fk_id_list: a list of gbifID which points to corresponding GBIFOccurrence
        :return:
        """
        GBIFOccurrence = apps.get_model(app_label='data_manager', model_name='GBIFOccurrence')
        gbifID_occ_dict = GBIFOccurrence.objects.in_bulk(id_list=fk_id_list, field_name='gbifID')
        list_of_verb = []
        for verbatim_dict in list_of_dict:
            gbif_id = verbatim_dict.get('gbifID')
            verbatim_dict['occurrence'] = gbifID_occ_dict.get(gbif_id)
            verbatim_obj = self.model(**verbatim_dict)
            list_of_verb.append(verbatim_obj)
        return self.bulk_create(list_of_verb, batch_size=5000)


class HexGridManager(models.Manager):

    def load_grids(self, grid_dir):
        """
        Load hexagon grids into database using LayerMapping.
        Hexagon grids were generated from QGIS using MMQGIS.
        :param grid_dir: String, a directory of hexagon grid with specific size
        :return:
        """
        if not os.path.isdir(grid_dir):
            raise NotADirectoryError(grid_dir)
        # Layermapping dictionary - generated using ogrinspect by running
        # `python manage.py ogrinspect path/to/.shp HexGrid --srid=3031 --mapping --multi`
        hexgrid_mapping = {
            "left": "left",
            "bottom": "bottom",
            "right": "right",
            "top": "top",
            "geom": "MULTIPOLYGON",
        }
        # size is the digits in the directory name, e.g. if grid10.shp resides in grid10/ then it has size=10
        size = re.findall(r"\d+", grid_dir)  # todo: prone to error, fix this in future.
        # Map shape file data into GeoDjango model HexagonGrid
        # .shp file from QGIS is already in EPSG: 3031 projection, thus transform=False
        logger.info("Loading grid from {}".format(grid_dir))
        lm = LayerMapping(model=self.model, data=grid_dir, mapping=hexgrid_mapping, transform=True)
        lm.save(progress=True, step=5000)  # Save to database.
        try:
            # Add size attribute to HexGrid objects.
            self.filter(size__isnull=True).update(size=size[0])
            logger.info("Updated size of grid: {}".format(size))
        except IntegrityError as e:  # the other threads have updated it
            logger.error(e)
            pass
        return 'done'

    def import_grids(self, grids_dir=settings.GRIDS_DIR):
        """
        Import grids
        :param grids_dir: string, parent directory of all hexagon grids. default to settings.GRIDS_DIR
        :return:
        """
        if not os.path.isdir(grids_dir):
            raise NotADirectoryError(grids_dir)  # GRIDS_DIR is not a directory
        grid_dirs_list = list()
        for root, dirs, files in os.walk(grids_dir):
            for directory in dirs:
                if not directory.startswith("."):  # ignore .DS_Store
                    grid_dir = os.path.join(os.path.join(root, directory), "")
                    grid_dirs_list.append(grid_dir)
        for grid_dir in grid_dirs_list:
            self.load_grids(grid_dir)
        return


class HarvestedDatasetManager(models.Manager):

    def create_from_list_of_dicts(self, list_of_dicts, query_param):
        """
        Create HarvestedDataset based on a list of dictionaries obtained from GBIF webservices.
        :param list_of_dicts: a list of dictionaries, presumably each dictionary is one registry/dataset
        :param query_param: a dictionary query parameters for GBIF API (see pygbif documentation)
        :return:
        """
        exclude_hosting_org = ["7ce8aef0-9e92-11dc-8738-b8a03c50a862"]  # do not harvest from plazi
        search_term = ''
        if query_param:
            search_term = query_param.get('q', '')
        for dataset in list_of_dicts:
            modified = None
            dataset_uuid = dataset.get("key", None)
            if search_term:  # only apply extra filter when it is a search with q
                search_term = search_term.lower()
                title = dataset.get('title', '')
                abstract = dataset.get('description', '')
                if title:
                    title = title.lower()  # to avoid case sensitivity
                if abstract:
                    abstract = abstract.lower()  # to avoid case sensitivity
                if search_term not in title or search_term not in abstract:
                    continue
            if dataset_uuid:
                # registry.dataset_search() does not return metadata of modified date, hence registry.datasets() is
                # called for each dataset to retrieve more detail metadata
                hosting_organization_key = dataset.get("hostingOrganizationKey")
                if hosting_organization_key in exclude_hosting_org:
                    continue
                try:
                    dataset_detail = registry.datasets(uuid=dataset_uuid)
                except HTTPError:  # continue to the next key
                    continue
                try:
                    occurrence_data = occurrences.search(datasetKey=dataset_uuid)
                except HTTPError:  # continue to the next key
                    continue
                raw_modified = dataset_detail.get("modified", None)
                if raw_modified:
                    modified = datetime.date(parse(raw_modified, tzinfos=None))
                # HarvestedDataset model attributes
                hosting_organization_title = dataset.get("hostingOrganizationTitle")
                license = dataset.get("license")
                publishing_country = dataset.get("publishingCountry")
                publishing_organization_key = dataset.get("publishingOrganizationKey")
                publishing_organization_title = dataset.get("publishingOrganizationTitle")
                title = dataset.get("title")
                dataset_type = dataset.get("type")
                # registry.datasets(uuid=datasetKey) will not return recordCount - need to get this info using
                # pygbif.occurrences.search(datasetKey=datasetKey)
                record_count = occurrence_data.get('count', None)
                try:
                    self.create(key=dataset_uuid,
                                hostingOrganizationKey=hosting_organization_key,
                                hostingOrganizationTitle=hosting_organization_title,
                                license=license,
                                publishingCountry=publishing_country,
                                publishingOrganizationKey=publishing_organization_key,
                                publishingOrganizationTitle=publishing_organization_title,
                                recordCount=record_count,
                                title=title,
                                type=dataset_type,
                                modified=modified,
                                include_in_antabif=None,
                                import_full_dataset=None)
                except IntegrityError:  # other process can insert the record into database already
                    pass
        return
