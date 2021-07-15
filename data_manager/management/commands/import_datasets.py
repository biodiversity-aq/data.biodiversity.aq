# -*- coding: utf-8 -*-
import multiprocessing as mp
import requests
import defusedxml.ElementTree as ET
from dwca.exceptions import InvalidArchive
from dwca.read import DwCAReader
from data_manager.models import *
from data_manager.helpers import count_occurrence_per_hexgrid, vacuum
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connections
from shapely.geometry import shape, Point


# Logging configuration
logger = logging.getLogger("import_datasets")


class WrongModelException(TypeError):
    """Raise when a QuerySet of a model other than the ones expected is used"""


def get_archives(directory):
    """Return full path of all darwin core archives downloaded to directory
    :param directory: Directory containing downloaded darwin-core archives.
    :raises: :class: `django.core.management.base.CommandError` if the directory does not exist.
    :return archives: A list of archives' full path
    """
    if not os.path.exists(directory):
        raise CommandError("Directory '{}' does not exist".format(directory))
    archives = []
    for (root, dirs, files) in os.walk(directory):
        for file in files:
            if file.endswith(".zip"):
                archives.append(os.path.join(root, file))
    return archives


def remove_duplicates(queryset):
    """Remove duplicate of identical queryset."""
    for i, instance in enumerate(queryset):
        if i != 0:
            instance.delete()
    return


def add_person_from_gbif_dwca_eml(eml_tree, dataset_object, project_object):
    """Create Person objects from GBIF"s <dataset_uuid>.xml file
    A Person will not be created if there is no individualName specified
    :param eml_tree: an xml Element object, (use defusedxml library)
        e.g.: <Element "{eml://ecoinformatics.org/eml-2.1.1}eml" at 0x10bf539f8>
    :param dataset_object: Dataset object
    :param project_object: Project object
    :return:
    """
    # Return a list of all parents of <individualName> tag
    # [<Element "creator" at 0x10caa2a48>, <Element "metadataProvider" at 0x10ca6a0e8>, ... ]
    individual_name_parent_list = eml_tree.findall(".//individualName/...")
    # If the list is not empty
    if individual_name_parent_list:
        for parent in individual_name_parent_list:
            # person_type is the parent of <individualName> which could be:
            # "creator", "metadataProvider", "associatedParty", "personnel" ...
            person_type = parent.tag
            # xpath to find if these nodes exist
            # <Element 'givenName' at 0x10caa2ae8>
            find_given_name = parent.find("./individualName/givenName")
            find_surname = parent.find("./individualName/surName")
            find_email = parent.find("./electronicMailAddress")
            find_organization = parent.find("./organizationName")
            # Only project personnel and associatedParty individual has attribute "role" in EML
            find_role = parent.find("./role")
            attributes = [find_given_name, find_surname, find_email, find_organization, find_role]
            # If nodes exist, give the text of the node
            # parent.find("./individualName/givenName").text = 'Els'
            given_name, surname, email, organization, role = \
                (attribute.text if attribute is not None else "" for attribute in attributes)
            full_name = given_name + " " + surname
            # Replace "_" in role with space
            role = role.replace("_", " ")
            email = email.replace("@", "(a)")
            # Create Person object, returns a tuple - the Person object, boolean to indicate if object was created
            # Person.objects.get_or_create(surname="John Doe")
            # (<Person:  John Doe>, False)
            try:
                person_object, created = Person.objects.get_or_create(given_name=given_name,
                                                                      surname=surname,
                                                                      email=email,
                                                                      full_name=full_name)
            except MultipleObjectsReturned:
                # delete all other duplicates and only keep one unique entry
                objects = Person.objects.filter(given_name=given_name, surname=surname, email=email, full_name=full_name)
                remove_duplicates(objects)
                person_object, created = Person.objects.get_or_create(given_name=given_name, surname=surname,
                                                                      email=email, full_name=full_name)
                pass
            # Create PersonTypeRole object
            try:
                PersonTypeRole.objects.get_or_create(person_type=person_type, role=role, organization=organization,
                                                     dataset=dataset_object, project=project_object,
                                                     person=person_object)
            except MultipleObjectsReturned:
                # delete all other duplicates and only keep one unique entry
                objects = PersonTypeRole.objects.filter(person_type=person_type, role=role, organization=organization,
                                                        dataset=dataset_object, project=project_object,
                                                        person=person_object)
                remove_duplicates(objects)
                pass
    return


def get_eml_of_metadata_only_datasets(dataset_key):
    """
    Get EML of metadata-only datasets through GBIF API
    :param dataset_key: a valid uuid.UUID instance. UUID of a metadata-only dataset
    :return: a dict with key = dataset key, value = x
    """
    # ensure that dataset_key is a valid UUID. Raise ValueError if dataset_key is a malformed UUID
    gbif_uuid = uuid.UUID(dataset_key)
    uuid_eml_dict = dict()
    response = requests.get('https://api.gbif.org/v1/dataset/{}/document'.format(gbif_uuid))
    if response.status_code == 200:
        eml_text = response.text  # 404 will get a response but response.text will be ''
        if eml_text:
            eml = ET.fromstring(eml_text)
            uuid_eml_dict[dataset_key] = eml
    return uuid_eml_dict


def get_metadata_dataset_to_download():
    """
    Get a set of new and outdated metadata-only HarvestedDataset
    :return: HarvestedDataset QuerySet
    """
    # new metadata-only dataset to be downloaded and imported
    metadata_datasets = HarvestedDataset.objects.filter(include_in_antabif=True, type='METADATA',
                                                        dataset__isnull=True)
    # check metadata only datasets has new version
    for dataset in Dataset.objects.filter(data_type__data_type='Metadata'):
        if dataset.has_new_version():
            metadata_datasets | HarvestedDataset.objects.filter(key=dataset.dataset_key)  # merge queryset
    return metadata_datasets


def import_metadata_only_datasets(harvested_datasets):
    """
    Import metadata only datasets - only EML
    :param harvested_datasets: HarvestedDataset QuerySet
    :return:
    """
    if not harvested_datasets.model == HarvestedDataset:
        raise(WrongModelException('Requires data_manager.models.HarvestedDataset QuerySet not a {} Queryset'
                                  .format(harvested_datasets.model)))
    metadata_datasets = harvested_datasets.filter(type='METADATA')  # ensure that they are metadata only datasets
    for dataset in metadata_datasets:
        uuid_eml_dict = get_eml_of_metadata_only_datasets(dataset.key)
        if uuid_eml_dict:
            dataset_object = import_eml(uuid_eml_dict)
            dataset_object.count_occurrence_per_dataset()
            HarvestedDataset.objects.filter(key=dataset.key).update(dataset=dataset_object)
            logger.info('[IMPORT][METADATA-ONLY]Imported metadata only dataset: {}'.format(dataset.key))
    return


def import_eml(uuid_eml_dict):
    """
    Import EML to database
    :param uuid_eml_dict: a dictionary with key = dataset uuid, value = xml Element object (use defusedxml to parse xml)
    """
    if not isinstance(uuid_eml_dict, dict):
        raise TypeError('Requires a dict, not a {}'.format(type(uuid_eml_dict)))
    dataset_object = None
    for dataset_uuid, eml_tree in uuid_eml_dict.items():
        # check type of uuid_eml_dict
        uuid.UUID(dataset_uuid)  # check uuid
        # check if dataset was supposed to be harvested
        logger.info("[IMPORT][EML]Dataset key: {}".format(dataset_uuid))
        # delete occurrence records of datasets to be updated. Keep the rest, do not delete the full dataset and all
        # other cascade delete records - need to keep the id for Download objects
        old_occurrences = GBIFOccurrence.objects.filter(dataset__dataset_key=dataset_uuid)
        if old_occurrences.exists():
            delete_by_batch(old_occurrences)
        # create objects using model managers
        project_object = Project.objects.from_gbif_dwca_eml(eml_tree)
        dataset_object = Dataset.objects.from_gbif_dwca_eml(eml_tree, dataset_uuid, project_object)
        HarvestedDataset.objects.filter(key=dataset_uuid).update(dataset=dataset_object)
        Keyword.objects.from_gbif_dwca_eml(eml_tree, dataset_object)
        add_person_from_gbif_dwca_eml(eml_tree, dataset_object, project_object)
    return dataset_object


def update_dataset_with_gbif_api(dataset_queryset):
    """
    Update DataType and Publisher of Dataset using GBIF web services:
    The most accurate way to determine the data type of a dataset is to use GBIF web services while Publisher
    information can only be obtained through web services.

    Many DwCA is mapped to a different core. e.g. Sampling Event dataset uses Occurrence core in the DwCA.
    This update needs to be a separated call because GBIF limits the number of API calls. If this is integrated in part
    of populate_db(), which will be run in threads, multiple API call will be performed together, this will lead to long
    waiting time of the command.
    :param dataset_queryset: QuerySet object of Dataset model
    :return:
    """
    logger.info('[IMPORT] Updating DataType, Publisher and occurrence count')
    if dataset_queryset.model != Dataset:
        raise WrongModelException('Expect a data_manager.models.Dataset QuerySet')
    if dataset_queryset:
        for dataset in dataset_queryset:
            data_type = DataType.objects.create_from_gbif_api(dataset.dataset_key)
            publisher = Publisher.objects.from_gbif_api(dataset.dataset_key)
            dataset.data_type = data_type
            dataset.publisher = publisher
            dataset.count_occurrence_per_dataset()
            dataset.save()
    return


def occurrence_is_antarctic(row, subantarctic_polygon):
    """Test if a geopoint is located within/touches subantarctic polygon.
    :param row: a row from dwca object
    :param subantarctic_polygon: a Polygon object
    :return: True if geopoint within polygon, else False
    """
    decimal_latitude = row.data.get("http://rs.tdwg.org/dwc/terms/decimalLatitude", None)
    decimal_longitude = row.data.get("http://rs.tdwg.org/dwc/terms/decimalLongitude", None)
    if decimal_latitude and decimal_longitude:
        geopoint = Point(float(decimal_longitude), float(decimal_latitude))
        if geopoint.within(subantarctic_polygon) or geopoint.touches(subantarctic_polygon):
            return True
        else:
            return False


def join_hexgrid_occurrence():
    """
    Assign HexGrid which contains the GBIFOccurrence's geopoint to the GBIFOccurrence.
    """
    qs = GBIFOccurrence.objects.exclude(geopoint__isnull=True).filter(hexgrid__isnull=True)
    for occ in qs.iterator():
        try:
            grid = HexGrid.objects.filter(geom__contains=occ.geopoint)
        except ObjectDoesNotExist:
            continue
        try:
            occ.hexgrid.set(grid)
        except IntegrityError:  # fk already exists
            pass
        except Exception as e:
            logger.error(e, "[HEXBIN]Occurrence id: {}".format(occ.id))
            pass
    return


def get_extension_data_from_core_row(core_row, extension_uri='http://rs.tdwg.org/dwc/terms/Occurrence'):
    """
    Get the row of a specific extension corresponds to this core row if it exists
    :param core_row: dwca.rows.Row object
    :param extension_uri: the uri of extension, default to verbatim occurrence
    :return: the row data of the extension
    """
    verbatim_data = None
    extensions = [e.rowtype for e in core_row.extensions]
    try:
        i = extensions.index(extension_uri)
        verbatim_data = core_row.extensions[i].data
    except ValueError:
        pass  # No verbatim data for this record
    return verbatim_data


def get_core_gbifID_with_verbatim(verbatim_row, gbif_ids):
    """
    Append gbifID of the row to the list of gbif_ids provided if there is a record in BOTH occurrence.txt and
    verbatim.txt
    :param verbatim_row: dwca.rows.Row object of the Core
    :param gbif_ids: a set of gbifID
    :return: a set of gbifID
    """
    gbif_id = verbatim_row.data.get('http://rs.gbif.org/terms/1.0/gbifID')
    if gbif_id:
        gbif_ids.add(gbif_id)
    return gbif_ids


def populate_db(archive, **options):
    """
    Populate database
    :param archive: the name of darwin-core archive
    :param options: kwargs from handle()
    :return:
    """
    bulk_create_count = 0
    try:
        dwca = DwCAReader(archive)
    except InvalidArchive:
        return
    # get dataset uuid of the archive being processed. Each dwca archive will only have 1 dataset.
    try:
        uuid = [key for key in dwca.source_metadata.keys()][0]
    except IndexError as e:  # sometimes dwca downloaded is empty - empty occurrence.txt, no EML file
        logger.warning('[IMPORT][FAIL]{}, message: {}'.format(archive, e))
        return
    # only import records if the core type is Occurrence
    if not dwca.descriptor.core.type == 'http://rs.tdwg.org/dwc/terms/Occurrence':
        return
    try:
        import_all_rows = HarvestedDataset.objects.get(key=uuid).import_full_dataset
    except HarvestedDataset.DoesNotExist:
        return
    # ----------------------------
    #  import eml: <datasetKey>.xml
    # ----------------------------
    dataset_object = import_eml(dwca.source_metadata)
    # -----------------------
    #  import occurrence.txt
    # -----------------------
    list_of_occ = []
    gbif_ids = set()
    # read occurrence.txt line by line to prevent overloading of memory
    for i, row in enumerate(dwca):
        interpreted_data = row.data
        gbif_id = interpreted_data.get('http://rs.gbif.org/terms/1.0/gbifID')
        # prevent duplicated record
        if GBIFOccurrence.objects.filter(gbifID=gbif_id).exists() or gbif_id in gbif_ids:
            continue
        # Filter out non subantarctic/antarctic occurrences
        if import_all_rows:
            gbif_ids.add(gbif_id)
            occ_object = GBIFOccurrence.objects.instantiate(interpreted_data, dataset_object)
        elif occurrence_is_antarctic(row, subantarctic_polygon):
            gbif_ids.add(gbif_id)
            occ_object = GBIFOccurrence.objects.instantiate(interpreted_data, dataset_object)
        else:
            continue
        list_of_occ.append(occ_object)
        # when the length of array is 5000 lines
        if len(list_of_occ) != 0 and len(list_of_occ) % 5000 == 0:
            GBIFOccurrence.objects.bulk_create(list_of_occ)
            bulk_create_count += 1
            logger.info('[IMPORT]Row: {}, Dataset: {}'.format(i, uuid))
            list_of_occ = []
            gbif_ids = set()
        # vacuum when there is too many insert/update
        if bulk_create_count != 0 and bulk_create_count % 200 == 0:
            vacuum()
    # remainder
    GBIFOccurrence.objects.bulk_create(list_of_occ)
    bulk_create_count += 1
    # update fk for HarvestedDataset
    HarvestedDataset.objects.filter(key=uuid).update(dataset=dataset_object)
    dwca.close()
    return


# subantarctic polygon
with open(os.path.join(settings.SHAPEFILES_DIR, "subantarctic_polygon.geojson")) as polygon_file:
    r = polygon_file.read()
    subantarctic_polygon = shape(json.loads(r))


class Command(BaseCommand):
    help = """
    Import datasets into database
    """

    def add_arguments(self, parser):
        """Add optional arguments to parser
        :param parser: ArgumentParser object
        :return:
        """
        parser.add_argument('-f', '--file', nargs='*', required=False,
                            help='Name of darwin-core archive(s) relative to path {}'.format(settings.DOWNLOADS_DIR))
        parser.add_argument('--hexbin', dest='hexbin', action='store_true', required=False,
                            help='perform hexbin on occurrences')
        parser.add_argument('--full-text-index', dest='full-text-index', action='store_true', required=False,
                            help='create index for full text search')

    def handle(self, *args, **options):
        cache.clear()
        # delete dataset in database which should not be imported
        for harvested_dataset in HarvestedDataset.objects.filter(include_in_antabif=False):
            harvested_dataset.delete_related_objects()
        # remove any orphan GBIFOccurrence instances
        delete_by_batch(GBIFOccurrence.objects.filter(dataset__isnull=True))
        # only the archive specified
        if options["file"]:
            for file in options["file"]:
                archive = os.path.join(settings.DOWNLOADS_DIR, file)
                if not os.path.exists(archive):
                    raise CommandError("[IMPORT]Directory '{}' does not exist".format(archive))
                populate_db(archive, **options)
        else:
            archives = get_archives(settings.DOWNLOADS_DIR)
            connections.close_all()
            with mp.Pool(processes=settings.CPU_COUNT, maxtasksperchild=1) as pool:
                # chops the iterable into a number of chunks which it submits to the process pool as separate tasks.
                pool.map(populate_db, archives, chunksize=settings.CPU_COUNT)
                pool.close()
                pool.join()
        metadata_datasets = get_metadata_dataset_to_download()
        import_metadata_only_datasets(metadata_datasets)
        update_dataset_with_gbif_api(Dataset.objects.filter(
            modified__gte=datetime.date.today()-datetime.timedelta(days=3),
            data_type__data_type__isnull=True))  # only update recently modified Dataset
        # Delete Project that is no longer associated with Dataset
        Project.objects.filter(dataset__isnull=True).delete()
        if options["hexbin"]:
            # assign hexgrids to each occurrence
            # load grid into db if HexGrid not exists
            grid_exists = HexGrid.objects.exists()
            if not grid_exists:
                HexGrid.objects.import_grids(grids_dir=settings.GRIDS_DIR)
            # assign grid to each occurrence record
            logger.info("[HEXBIN]Counting occurrence per grid")
            join_hexgrid_occurrence()  # assign HexGrid to each GBIFOccurrence record.
            count_occurrence_per_hexgrid()  # for home page map
        vacuum()
        cache.clear()
        return 'done'
