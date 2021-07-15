# -*- coding: utf-8 -*-
import os
import time
import logging
import requests

from data_manager.management.commands.import_datasets import join_hexgrid_occurrence
from data_manager.helpers import count_occurrence_per_hexgrid
from data_manager.models import Dataset, HarvestedDataset
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from pygbif import occurrences
from urllib.parse import urljoin


logger = logging.getLogger('import_datasets')


def delete_files_in_directory(directory):
    """
    Delete every files (not directory) within a directory.
    Raise FileNotFoundError if directory does not exists
    :param directory: relative path to a directory
    :return: None
    """
    for each_file in os.listdir(directory):
        file_path = os.path.join(directory, each_file)
        if os.path.isfile(file_path):
            os.unlink(file_path)
    return


def get_download_key(dataset_uuid):
    """
    Return a single download key from GBIF API.
    Uses pygbif.occurrences.download to spin up a download request for GBIF occurrence data.
    :param dataset_uuid: A set of dataset keys (uuid)
    :return: single download key for the request (e.g. 0098562-160910150852091)
    """

    query = ['datasetKey = {}'.format(dataset_uuid)]
    logger.debug('[DOWNLOAD]Obtaining download key for dataset: {}'.format(dataset_uuid))
    try:
        request_result = occurrences.download(query, user=settings.GBIF_USER, pwd=settings.GBIF_USER_PASSWORD,
                                              email=settings.GBIF_USER_EMAIL)
    except Exception as e:  # Too many simultaneous downloads throws Exception instead of a subclass of Exception
        logger.warning(e, dataset_uuid)
        return None
    download_key = request_result[0]
    return download_key


def update_harvested_dataset_fk():
    """
    Assign Dataset object to HarvestedDataset foreign key
    """
    harvested_datasets = HarvestedDataset.objects.filter(dataset__isnull=True, include_in_antabif=True)
    for harvested_dataset in harvested_datasets:
        try:
            harvested_dataset.dataset = Dataset.objects.get(dataset_key=harvested_dataset.key)
            harvested_dataset.save()
        except Dataset.DoesNotExist:
            continue
    return


def request_download(download_key, counter, total_downloads):
    """
    Performs polling based on a single download_key obtained from get_download_key()
    Once status of polling result status is 'SUCCEEDED', archive will be downloaded and save to
    settings.DOWNLOADS_DIR.
    """
    dataset_ok = False
    start_time = time.time()
    while not dataset_ok:
        polling_duration = time.time() - start_time
        if polling_duration > 10800:  # if polling last more than 3 hours
            download_resource_url = 'occurrence/download/request/{}'.format(download_key)
            download_url = urljoin(settings.GBIF_API_BASE, download_resource_url)
            requests.delete(download_url, auth=(settings.GBIF_USER_EMAIL, settings.GBIF_USER_PASSWORD))
            return dataset_ok
        try:
            results = occurrences.download_meta(key=download_key)
        except Exception as e:
            logger.error(e, download_key)
            return False
        if results['status'] == 'PREPARING' or results['status'] == 'RUNNING' or results['status'] == 'UNAVAILABLE':
            logger.debug('[DOWNLOAD]Polling {}/{} [{}] {}: {}'.format(
                counter, total_downloads, results['status'], results['key'], results['downloadLink']))
            time.sleep(60)  # wait for 60 seconds before requesting the status again
        elif results['status'] == 'SUCCEEDED':
            # status can be 'CANCELLED', 'KILLED' or 'RUNNING', only download when status is 'SUCCEEDED'
            dataset_ok = True
            filename = download_key + '.zip'
            logger.info('[DOWNLOAD]Downloading darwin core archive {}/{}'.format(counter, total_downloads))
            # retrieve archive and save to DOWNLOADS_DIR
            download_file_path = os.path.join(settings.DOWNLOADS_DIR, filename)
            download_link = results.get('downloadLink')
            response = requests.get(download_link, stream=True)
            handle = open(download_file_path, 'wb')
            for chunk in response.iter_content(chunk_size=512):  # write file by chunk
                if chunk:
                    handle.write(chunk)
            handle.close()
            logger.info('[DOWNLOAD]Archive downloaded: {}'.format(download_key))
        else:
            logger.info('[DOWNLOAD][{}] {}: {}'.format(results['status'], results['key'], results['downloadLink']))
            dataset_ok = True
    return True


class Command(BaseCommand):
    help = '''
    This command will check if the same dataset on GBIF is modified.
    If dataset on GBIF was deleted -- it will delete the dataset.
    If new version of dataset is available, this command will request a download at GBIF and poll for the results. 
    The downloaded darwin-core archive will be stored in settings.DOWNLOADS_DIR. The following settings should be 
    configured in your django settings file:

    - GBIF_USER: the GBIF user that will request the download
    - GBIF_USER_PASSWORD: password for that user
    - GBIF_USER_EMAIL: email to which GBIF will send a notification email when the download is ready. Specifying the 
        email address here seems mandatory.
    - DOWNLOADS_DIR: the directory to save downloaded darwin-core archive
    
    It will then call the other command "python manage.py import_datasets" to import the downloaded datasets.
    '''

    def handle(self, *args, **options):
        if not os.path.isdir(settings.DOWNLOADS_DIR):
            os.mkdir(settings.DOWNLOADS_DIR)
        # Delete all archives from downloads/ directory
        delete_files_in_directory(settings.DOWNLOADS_DIR)
        # -----------------
        # DELETED DATASETS
        # -----------------
        # flag Dataset and HarvestedDataset objects if corresponding uuid is deleted from GBIF
        for dataset in Dataset.objects.all():
            dataset.deleted_on_gbif()  # check if dataset is deleted on GBIF
        # delete Dataset that has HarvestedDataset instance include_in_antabif changed to False <- this action can be
        # performed by admin or dataset.deleted_on_gbif() function
        for harvested_dataset in HarvestedDataset.objects.filter(include_in_antabif=False):
            harvested_dataset.delete_related_objects()
        # -------------------------------
        # GET DATASET UUIDS FOR DOWNLOAD
        # -------------------------------
        to_download = set()
        all_datasets = Dataset.objects.exclude(data_type__data_type='Metadata')
        # check if datasets have new version. If so, get those uuid
        for dataset in all_datasets:
            if dataset.has_new_version():
                to_download.add(dataset.dataset_key)
        # get the uuid of datasets discovered in harvest cycle that needs to be imported
        update_harvested_dataset_fk()
        # Metadata dataset will be updated/downloaded separately - occurrences.download() does not work for metadata
        # and checklist type dataset
        new_datasets_to_download = HarvestedDataset.objects.exclude(type__in=['METADATA', 'CHECKLIST'])\
            .filter(include_in_antabif=True, dataset__isnull=True, import_full_dataset__isnull=False, recordCount__gt=0)
        for dataset in new_datasets_to_download:
            to_download.add(dataset.key)
        # ------------------
        # DOWNLOAD DATASETS
        # ------------------
        i = 1
        for uuid in to_download:
            logger.info('[DOWNLOAD]Requesting download {}/{} dataset uuid: {}'.format(i, len(to_download), uuid))
            download_key = get_download_key(uuid)
            if download_key is not None:
                logger.debug(download_key)
                request_download(download_key, i, len(to_download))
                i += 1
            else:
                continue
            if i % 5 == 0:
                # import datasets
                call_command('import_datasets')
                delete_files_in_directory(settings.DOWNLOADS_DIR)
        call_command('import_datasets')  # remainder
        join_hexgrid_occurrence()  # assign HexGrid to each GBIFOccurrence record.
        count_occurrence_per_hexgrid()  # for home page map
        cache.clear()
        return 'Done!'
