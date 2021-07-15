# -*- coding: utf-8 -*-
from data_manager.models import HarvestedDataset
from django.conf import settings
from django.core.management.base import BaseCommand
from queue import Queue
from pygbif import registry
from timeit import default_timer
import logging
import requests


logger = logging.getLogger(__name__)


def dataset_search_harvest(queue):
    """
    Harvest datasets from GBIF with pygbif.registry.dataset_search based on query parameters in the queue.
    This should NOT be performed with multiprocessing as GBIF limits the API calls. Multiple API calls at the
    same time will lead to long waiting time.
    :param queue: queue.Queue object with query parameters for pygbif.registry.dataset_search
    :return:
    """
    if not isinstance(queue, Queue):
        raise TypeError('Expect a queue.Queue instance')
    while not queue.empty():
        query_param = queue.get()
        # time function
        function_start = default_timer()
        # initialise variables
        limit = 100  # number of records returned per request
        offset = 0  # record starts from this index
        end_of_records = False
        # while it is not the last page of the query
        while not end_of_records:
            try:
                response = registry.dataset_search(offset=offset, limit=limit, **query_param)
            except requests.exceptions.HTTPError as e:
                logger.warning(e, query_param)
                continue  # can continue the harvest - the dataset will be harvested next time
            count = response.get('count', '')
            results = response.get("results", [])
            if results:
                HarvestedDataset.objects.create_from_list_of_dicts(results, query_param)
            logger.info('[HARVEST]QUERY: {}, COUNT:{}, OFFSET:{}, LIMIT:{}'.format(query_param, count, offset, limit))
            # increment offset and limit by 100
            offset += 100
            limit += 100
            # assign True to endOfRecords if there is no endOfRecords in response
            end_of_records = response.get("endOfRecords", True)
        function_end = default_timer()
        time_used = round(function_end - function_start)
        logger.info('[HARVEST]QUERY:{}\tTIME USED: {}s'.format(query_param, time_used))
    return


def harvest_datasets_from_installations(installation_key):
    """
    Harvest and create HarvestedDataset of all datasets from an installation which has
    installationKey == installation_key
    :param installation_key: UUID string of an installation on GBIF
    :return:
    """
    url = 'https://api.gbif.org/v1/installation/{}/dataset/'.format(installation_key)
    limit = 100
    offset = 0
    end_of_records = False
    while not end_of_records:
        params = {'limit': limit, 'offset': offset}
        response = requests.get(url, params=params).json()
        count = response.get('count')
        logger.info('[HARVEST]InstalltionKey: {}, COUNT:{}, OFFSET:{}, LIMIT:{}'.format(installation_key, count,
                                                                                        offset, limit))
        results = response.get('results', [])
        if results:
            HarvestedDataset.objects.create_from_list_of_dicts(results, query_param=None)
        end_of_records = response.get('endOfRecords', True)
        offset += 100
        limit += 100
    return


def harvest(query_parameters):
    """
    Harvest metadata of datasets with the given query parameters in parallel
    :query_parameters: a list of dictionaries of query for GBIF registry's API
    """
    # create queue
    task_queue = Queue()
    # put query parameters to queue
    for param in query_parameters:
        task_queue.put(param)
    dataset_search_harvest(queue=task_queue)
    return


class Command(BaseCommand):
    """
    Command to harvest metadata of datasets on GBIF and populate HarvestedDataset table in database with these metadata.
    Curator will then login to the admin interface to decide if the datasets should be downloaded and imported into
    database by flagging include_in_antabif = True/False.

    Example usage:
        DJANGO_SETTINGS_MODULE="data_biodiversity_aq,settings.development" python manage.py harvest_datasets
    """
    help = """
    Check if GBIF has new datasets. If new datasets exist, download metadata of these datasets and insert 
    them into HarvestedDataset model.
    """

    def handle(self, *args, **options):
        """
        Harvest new datasets from GBIF into HarvestedDataset model.
        Curator will assign True/False for include_in_antabif and import_full_dataset by logging into admin interface.
        """
        # All datasets associated with AADC IPT installation
        harvest_datasets_from_installations(installation_key='1cbabffe-9073-4007-ba1e-40ebcda6e302')
        harvest(query_parameters=settings.HARVEST_QUERY)
        return
