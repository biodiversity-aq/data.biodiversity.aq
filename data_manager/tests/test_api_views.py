import secrets
import uuid
from data_manager.models import DataType, Dataset, GBIFOccurrence, HexGrid, User, Download
from django.apps import apps
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient


TEST_USER = {'username': 'user@email.com', 'password': secrets.token_hex(16)}
TEST_STAFF = {'username': 'staff@email.com', 'password': secrets.token_hex(16), 'is_staff': True, 'is_superuser': False}
TEST_ADMIN = {'username': 'admin@email.com', 'password': secrets.token_hex(16), 'is_staff': True, 'is_superuser': True}


# list view url name
FIXTURE_LIST_URLS = [
    'v1.0:basisofrecord-list', 'v1.0:dataset-list', 'v1.0:datatype-list', 'v1.0:gbifoccurrence-list', 'v1.0:keyword-list',
    'v1.0:project-list', 'v1.0:publisher-list', 'db-statistics', 'login'
]
# detail view url name
FIXTURE_URLS_WITH_ARGS = [
    ('v1.0:basisofrecord-detail', 1),
    ('v1.0:dataset-detail', 1),
    ('v1.0:datatype-detail', 1),
    ('v1.0:gbifoccurrence-detail', 1),
    ('v1.0:keyword-detail', 1),
    ('v1.0:project-detail', 1),
    ('v1.0:publisher-detail', 1),
]

# variable for tests
# HarvestedDataset
HARVESTED_DATASET_KEY = str(uuid.uuid4())
HARVESTED_DATASET = {'key': HARVESTED_DATASET_KEY, 'include_in_antabif': True, 'import_full_dataset': True}
UPDATE_HARVESTED_DATASET = {'key': 'ddbc7560-6646-47b0-ac51-9608dde25c44', 'include_in_antabif': False, 'import_full_dataset': False}
PATCH_HARVESTED_DATASET = {'title': 'patched title'}  # required field not supplied
# DataType
DATA_TYPE = {'data_type': 'MYDATATYPE'}
UPDATE_DATA_TYPE = {'data_type': 'NEWDATATYPE'}
# BasisOfRecord
BASIS_OF_RECORD = {'basis_of_record': 'MY_BASIS_OF_RECORD'}
UPDATE_BASIS_OF_RECORD = {'basis_of_record': 'NEW_BASIS_OF_RECORD'}
# Dataset
DATASET = {'dataset_key': HARVESTED_DATASET_KEY, 'title': 'my dataset'}
UPDATE_DATASET = {'dataset_key': HARVESTED_DATASET_KEY, 'title': 'new dataset title'}
PATCH_DATASET = {'title': 'patched dataset title'}
# Keyword
KEYWORD = {'keyword': 'my keyword', 'thesaurus': 'my thesaurus', 'dataset': 1}
UPDATE_KEYWORD = {'keyword': 'new keyword', 'dataset': 1}
PATCH_KEYWORD = {'thesaurus': 'my new thesaurus', 'dataset': 1}
# Occurrence
OCCURRENCE = {'gbifID': 1, 'dataset': 1, 'basis_of_record': 1, 'scientificName': 'my scientific name'}
UPDATE_OCCURRENCE = {'gbifID': 1, 'row_json_text': 'new row data'}  # `habitat` field is not serialized
PATCH_OCCURRENCE = {'row_json_text': 'patched row data'}
# Project
PROJECT = {'title': 'my project title', 'funding': 'my project funding'}
UPDATE_PROJECT = {'title': 'my project title', 'funding': 'new project funding'}
PATCH_PROJECT = {'funding': 'patched project funding'}
# Publisher
PUBLISHER_KEY = uuid.uuid4()
PUBLISHER = {'publisher_key': PUBLISHER_KEY, 'publisher_name': 'my publisher name'}
UPDATE_PUBLISHER = {'publisher_key': PUBLISHER_KEY, 'publisher_name': 'new publisher name'}
PATCH_PUBLISHER = {'publisher_name': 'patched publisher name'}
# Download
DOWNLOAD = {'query': {'dataset': [1,]}}
UPDATE_DOWNLOAD = {'task_id': 'f9bac22a-63ef-43a4-8229-dc89ffa9dc87', 'query': {'basisOfRecord': [1, 2]}}
PATCH_DOWNLOAD = {'query': {'basisOfRecord': [1, 2]}}

API_TEST_DATA = [
    {
        'model': 'BasisOfRecord',
        'base_url_name': 'v1.0:basisofrecord',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': BASIS_OF_RECORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': BASIS_OF_RECORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': BASIS_OF_RECORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': BASIS_OF_RECORD},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_BASIS_OF_RECORD},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'Dataset',
        'base_url_name': 'v1.0:dataset',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': DATASET},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_DATASET},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_DATASET},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'DataType',
        'base_url_name': 'v1.0:datatype',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': DATA_TYPE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': DATA_TYPE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': DATA_TYPE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': DATA_TYPE},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_DATA_TYPE},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'HarvestedDataset',
        'base_url_name': 'v1.0:harvesteddataset',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': HARVESTED_DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': HARVESTED_DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': HARVESTED_DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': HARVESTED_DATASET},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_HARVESTED_DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_HARVESTED_DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_HARVESTED_DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_HARVESTED_DATASET},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_HARVESTED_DATASET},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_HARVESTED_DATASET},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_HARVESTED_DATASET},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_HARVESTED_DATASET},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'Keyword',
        'base_url_name': 'v1.0:keyword',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': KEYWORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': KEYWORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': KEYWORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': KEYWORD},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_KEYWORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_KEYWORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_KEYWORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_KEYWORD},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_KEYWORD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_KEYWORD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_KEYWORD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_KEYWORD},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'GBIFOccurrence',
        'base_url_name': 'v1.0:gbifoccurrence',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': OCCURRENCE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': OCCURRENCE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': OCCURRENCE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': OCCURRENCE},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_OCCURRENCE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_OCCURRENCE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_OCCURRENCE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_OCCURRENCE},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_OCCURRENCE},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_OCCURRENCE},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_OCCURRENCE},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_OCCURRENCE},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'Project',
        'base_url_name': 'v1.0:project',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PROJECT},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PROJECT},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PROJECT},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PROJECT},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_PROJECT},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_PROJECT},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_PROJECT},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_PROJECT},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_PROJECT},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_PROJECT},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_PROJECT},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_PROJECT},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'Publisher',
        'base_url_name': 'v1.0:publisher',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PUBLISHER},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PUBLISHER},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PUBLISHER},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PUBLISHER},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': UPDATE_PUBLISHER},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_PUBLISHER},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_PUBLISHER},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_PUBLISHER},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False, 'data': PATCH_PUBLISHER},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_PUBLISHER},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_PUBLISHER},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_PUBLISHER},
            ],
            'delete': [
                {'permission': 'anonuser', 'status_code': 405, 'success': False},
                {'permission': 'authuser', 'status_code': 405, 'success': False},
                {'permission': 'staff', 'status_code': 405, 'success': False},
                {'permission': 'admin', 'status_code': 405, 'success': False}
            ]
        }
    },
    {
        'model': 'Download',
        'base_url_name': 'v1.0:download',
        'tests': {
            'create': [
                {'permission': 'anonuser', 'status_code': 403, 'success': False, 'data': DOWNLOAD},
                {'permission': 'authuser', 'status_code': 201, 'success': True, 'data': DOWNLOAD},
                {'permission': 'staff', 'status_code': 201, 'success': True, 'data': DOWNLOAD},
                {'permission': 'admin', 'status_code': 201, 'success': True, 'data': DOWNLOAD},
            ],
            'update': [
                {'permission': 'anonuser', 'status_code': 403, 'success': False, 'data': UPDATE_DOWNLOAD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': UPDATE_DOWNLOAD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': UPDATE_DOWNLOAD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': UPDATE_DOWNLOAD},
            ],
            'partial_update': [
                {'permission': 'anonuser', 'status_code': 403, 'success': False, 'data': PATCH_DOWNLOAD},
                {'permission': 'authuser', 'status_code': 405, 'success': False, 'data': PATCH_DOWNLOAD},
                {'permission': 'staff', 'status_code': 405, 'success': False, 'data': PATCH_DOWNLOAD},
                {'permission': 'admin', 'status_code': 405, 'success': False, 'data': PATCH_DOWNLOAD}
            ]
        }
    }
]

# need to be tested separately because Download instance need to be created during the test due to the auto_now_add
# created_at attribute (datetime field)
DELETE_DOWNLOAD_TEST_DATA = [
    {'permission': 'anonuser', 'status_code': 403, 'success': False},
    {'permission': 'authuser', 'status_code': 204, 'success': True},
    {'permission': 'staff', 'status_code': 204, 'success': True},
    {'permission': 'admin', 'status_code': 204, 'success': True}
]


class HTTPMethodsTestCase(APITestCase):
    """
    Test case to be inherited for APITestCase with different permission level.
    """
    def options(self, url_name, status_code, **kwargs):
        """
        Test for OPTIONS request.
        :param url_name: A string. The name of a given url in data_manager.urls
        :param status_code: An integer. Expected status code of OPTIONS request
        :param kwargs: other keyword arguments for reverse() function
        """
        url = reverse(url_name, **kwargs)
        response = self.client.options(url)
        self.assertEqual(response.status_code, status_code)

    def get(self, url_name, status_code, **kwargs):
        """
        Test for GET request.
        :param url_name: A string. The name of a given url in data_manager.urls
        :param status_code: An integer. Expected status code of GET request
        :param kwargs: other keyword arguments for reverse() function
        """
        url = reverse(url_name, **kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code)

    def create(self, model_name, base_url_name, data, status_code, success):
        """
        Test to ensure whether an instance of a Model can be created with POST request.
        :param model_name: A string. The name of the model, must be a model in data_manager app.
        :param base_url_name: A string. The name of a given url in data_manager.urls.
        :param data: A dictionary. Key = field name, value = value of the field. The combination of all the
        fields and values provided must be able to uniquely identify the record.
        :param status_code: An integer. HTTP response status code expected for the request.
        :param success: A boolean. True if object is expected to be created, else False.
        """
        model = apps.get_model(app_label='data_manager', model_name=model_name)
        list_url = reverse('{}-list'.format(base_url_name))
        post_response = self.client.post(list_url, data, format='json')
        self.assertEqual(post_response.status_code, status_code)
        self.assertEqual(model.objects.filter(**data).exists(), success)
        if success:
            # verify if GET request can retrieve the object
            instance = model.objects.get(**data)
            detail_url = reverse('{}-detail'.format(base_url_name), args=(instance.id,))
            get_response = self.client.get(detail_url)
            self.assertEqual(get_response.status_code, 200)

    def update(self, model_name, base_url_name, data, status_code, success, object_id=1):
        """
        Test PUT request for updating of an instance.
        The test will update a model instance using PUT request, check if the update applied using GET request.
        :param model_name: A string. The name of the Model, must be a model in data_manager app.
        :param base_url_name: A string. The name of a given url in data_manager.urls.
        :param data: A dictionary that contains field and values to update the instance.
        :param status_code: An integer. HTTP response status code expected for the request.
        :param success: A boolean. True if object is expected to be updated, else False.
        :param object_id: An integer. ID of an instance of a Model (model_name) to be updated by PUT request.
        :raise UnexpectedHTTPMethod: Exception is raised if wrong value is given to http_method.
        """
        model = apps.get_model(app_label='data_manager', model_name=model_name)
        detail_url = reverse('{}-detail'.format(base_url_name), args=(object_id,))
        response = self.client.put(detail_url, data, format='json')
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(model.objects.filter(**data).exists(), success)
        get_response = self.client.get(detail_url)  # get instance
        if success:
            for key, value in data.items():  # check each field to ensure that the values are updated.
                self.assertEqual(get_response.data.get(key), value)

    def partial_update(self, model_name, base_url_name, data, status_code, success, object_id=1):
        """
        Test PATCH request for updating of an instance.
        The test will update a model instance using PATCH request, check if the update applied using GET request.
        :param model_name: A string. The name of the Model, must be a model in data_manager app.
        :param base_url_name: A string. The name of a given url in data_manager.urls.
        :param data: A dictionary that contains field and values to update the instance.
        :param status_code: An integer. HTTP response status code expected for the request.
        :param success: A boolean. True if object is expected to be updated, else False.
        :param object_id: An integer. ID of an instance of a Model (model_name) to be updated by PATCH request.
        :raise UnexpectedHTTPMethod: Exception is raised if wrong value is given to http_method.
        """
        model = apps.get_model(app_label='data_manager', model_name=model_name)
        detail_url = reverse('{}-detail'.format(base_url_name), args=(object_id,))
        response = self.client.patch(detail_url, data, format='json')
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(model.objects.filter(**data).exists(), success)
        get_response = self.client.get(detail_url)  # get instance
        if success:
            for key, value in data.items():  # check each field to ensure that the values are updated.
                self.assertEqual(get_response.data.get(key), value)

    def delete(self, model_name, base_url_name, status_code, success, data=None, object_id=1):
        """
        Test DELETE request for an instance
        :param model_name: A string. The name of the Model, must be a model in data_manager app.
        :param base_url_name: A string. The name of a given url in data_manager.urls.
        :param status_code: An integer. HTTP response status code expected for the request.
        :param success: A boolean. True if object is expected to be deleted, else False.
        :param data: A dictionary that contains field and values to identify the instance to be deleted.
        :param object_id: An integer. ID of an instance of a Model (model_name) to be deleted by DELETE request.
        """
        model = apps.get_model(app_label='data_manager', model_name=model_name)
        detail_url = reverse('{}-detail'.format(base_url_name), args=(object_id,))
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status_code)
        if success:
            # GET request to ensure the page returns 404
            get_response = self.client.get(detail_url)
            self.assertEqual(get_response.status_code, 404)
            self.assertFalse(model.objects.filter(id=object_id).exists())  # ensure object is deleted


class BasePermissionTestCase(HTTPMethodsTestCase):
    """
    TestCase for all permissions level
    """
    fixtures = ['api_test.json']
    test_data = API_TEST_DATA

    def setUp(self):
        self.permission = 'anonuser'
        self.user = None

    def get_tests(self, model_test_data, action):
        """
        Get tests for HTTP action specified for model test data with the appropriate permission
        :param model_test_data: A dictionary contains test data for each model per http action.
        :param action: A string. Either 'create', 'update', 'partial_update' or 'delete' which correspond to
        POST, PUT, PATCH, DELETE request.
        :return:
        """
        model_name = model_test_data['model']
        base_url_name = model_test_data['base_url_name']
        tests = model_test_data['tests'].get(action)
        if tests:
            for test in tests:
                permission = test.get('permission')
                data = test.get('data')
                status_code = test.get('status_code')
                success = test.get('success')
                if permission == self.permission:
                    self.__getattribute__(action)(model_name=model_name, base_url_name=base_url_name, data=data,
                                                  status_code=status_code, success=success)

    def test_delete_download(self):
        """
        Test DELETE request for Download instances.
        This test has to be separated because the Download instance needs to be created here so that the created_at
        attribute is set to now. If created_at is older than 7 days, get_queryset will not return this and hence
        the status_code will be 404.
        """
        task_id = '{}'.format(uuid.uuid4())
        download = Download.objects.create(user=self.user, task_id=task_id, query="{'basisOfRecord' : '1'}")
        for test in DELETE_DOWNLOAD_TEST_DATA:
            permission = test.get('permission')
            status_code = test.get('status_code')
            success = test.get('success')
            if permission == self.permission:
                self.delete(model_name='Download', base_url_name='v1.0:download', status_code=status_code,
                            success=success, object_id=download.id)

    def test_run(self):
        """
        Run tests in HTTPMethodsTestCase for API_TEST_DATA for POST, PUT, PATCH, DELETE
        """
        for model_test_data in self.test_data:
            self.get_tests(model_test_data=model_test_data, action='create')
            self.get_tests(model_test_data=model_test_data, action='update')
            self.get_tests(model_test_data=model_test_data, action='partial_update')
            self.get_tests(model_test_data=model_test_data, action='delete')


class AnonUserTestCase(BasePermissionTestCase):
    """
    TestCase for all model instances for anonymous user permission (not logged in)
    """
    def setUp(self):
        self.user = None
        self.client = APIClient()
        self.permission = 'anonuser'

    def test_API_smoke_test(self):
        """
        API smoke test for every API endpoint
        """
        for url in FIXTURE_LIST_URLS:
            self.options(url_name=url, status_code=200)
            self.get(url_name=url, status_code=200)
        for url in FIXTURE_URLS_WITH_ARGS:
            self.options(url_name=url[0], status_code=200, args=(url[1],))
            self.get(url_name=url[0], status_code=200, args=(url[1],))


class AuthUserTestCase(BasePermissionTestCase):
    """
    Test cases for authenticated User permission.
    is_staff = False, is_active = False, is_superuser = False.
    """
    def setUp(self):
        """
        Setup User and Client for following tests
        """
        self.user = User.objects.get(username='user@email.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.permission = 'authuser'


class StaffTestCase(BasePermissionTestCase):
    """
    TestCase for all model instances with Staff permission.
    is_staff = True, is_active = True, is_superuser = False.
    """
    def setUp(self):
        """
        User and Client for following test cases.
        """
        self.user = User.objects.get(username='staff@email.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.permission = 'staff'


class AdminTestCase(BasePermissionTestCase):
    """
    TestCase for all model instances with Admin permission.
    is_staff = True, is_active = True, is_superuser = True.
    """
    def setUp(self):
        self.user = User.objects.get(username='admin@email.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.permission = 'admin'


@override_settings(URL_PREFIX=r'^data/')
class DatabaseStatisticsTests(APITestCase):
    """Test REST API which returns database content"""
    def setUp(self):
        data_type = DataType.objects.create(data_type='Occurrence')
        Dataset.objects.create(dataset_key="1",
                               title="InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium",
                               filtered_record_count=1,
                               data_type=data_type)
        dataset_pk = Dataset.objects.get(dataset_key="1")
        GBIFOccurrence.objects.create(gbifID='123', dataset=dataset_pk)

    def test_get_db_statistics(self):
        url = reverse('db-statistics')
        response = self.client.get(url)
        self.assertEqual(response.data.get('total number of occurrence records'), 1)
        self.assertEqual(response.data.get('total number of datasets'), 1)
        self.assertEqual(response.data.get('number of datasets per data type'), {'Occurrence': 1})


@override_settings(URL_PREFIX=r'^data/')
class OccurrenceSearchView(APITestCase):
    """Test for API occurrence search, pagination AND count"""

    def setUp(self):
        data_type = DataType.objects.create(data_type='Occurrence')
        d = Dataset.objects.create(dataset_key="1",
                                   title="test dataset title",
                                   filtered_record_count=1,
                                   data_type=data_type)
        for i in range(30):
            GBIFOccurrence.objects.create(gbifID=i, dataset=d, scientificName='belgica antarctica',
                                          decimalLatitude=-80, decimalLongitude=170,
                                          row_json_text='belgica antarctica test dataset title')
        Dataset.objects.create(dataset_key='123', title='First dataset', eml_text='First dataset 123',
                               deleted_record_count=0, full_record_count=3)
        dataset = Dataset.objects.get(dataset_key='123')
        GBIFOccurrence.objects.create(gbifID=31, geopoint=GEOSGeometry('POINT(-180 -90)'), decimalLatitude=-90,
                                      decimalLongitude=-180, dataset=dataset, scientificName='gbif_1')
        GBIFOccurrence.objects.create(gbifID=32, geopoint=GEOSGeometry('POINT(-180 -80)'), decimalLatitude=-80,
                                      decimalLongitude=-180, dataset=dataset, scientificName='gbif_2')
        GBIFOccurrence.objects.create(gbifID=33, geopoint=GEOSGeometry('POINT(-170 -80)'), decimalLatitude=-80,
                                      decimalLongitude=-170, dataset=dataset, scientificName='gbif_3')

    def test_occurrence_search_render_html(self):
        """Ensure html table is rendered with search"""
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'html'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('has_next_page'))
        self.assertFalse(response.context.get('has_previous_page'))
        self.assertTemplateUsed(response, 'occurrence-table.html')

    def test_occurrence_search_render_json(self):
        """Ensure response is rendered in json format"""
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'json'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, 'occurrence-table.html')
        self.assertEqual(len(response.data.get('occurrences')), settings.REST_FRAMEWORK.get('PAGE_SIZE'))

    def test_occurrence_search_set_limit(self):
        """Ensure limit offset works"""
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'json', 'limit': 10})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get('has_next_page'))
        self.assertFalse(response.data.get('has_previous_page'))
        self.assertTemplateNotUsed(response, 'occurrence-table.html')
        self.assertEqual(len(response.data.get('occurrences')), 10)

    def test_occurrence_search_set_offset(self):
        """Ensure limit offset works"""
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'json', 'offset': 20})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data.get('has_next_page'))
        self.assertTrue(response.data.get('has_previous_page'))
        self.assertTemplateNotUsed(response, 'occurrence-table.html')
        self.assertEqual(len(response.data.get('occurrences')), 10)

    def test_occurrence_search_set_limit_offset(self):
        """Ensure limit offset works"""
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'json', 'offset': 20, 'limit': 30})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data.get('has_next_page'))
        self.assertTrue(response.data.get('has_previous_page'))
        self.assertTemplateNotUsed(response, 'occurrence-table.html')
        self.assertEqual(len(response.data.get('occurrences')), 10)

    def test_occurrence_list_view_results_count(self):
        """Ensure the number of results return is 3"""
        dataset = Dataset.objects.get(dataset_key='123')
        url = reverse('api-occurrence-search')
        response = self.client.get(url, {'dataset': dataset.id}, follow=True)
        self.assertEqual(len(response.data.get('occurrences')), 3)


@override_settings(URL_PREFIX=r'^data/')
class OccurrenceCountView(APITestCase):
    """Test for API occurrence count"""

    def setUp(self):
        for i in range(1000):
            GBIFOccurrence.objects.create(gbifID=i, scientificName='belgica antarctica',
                                          decimalLatitude=-80, decimalLongitude=170,
                                          row_json_text='belgica antarctica test dataset title')

    def test_occurrence_count(self):
        """Ensure occurrence count returns the total number of occurrences (regardless of limit offset)"""
        url = reverse('api-occurrence-count')
        response = self.client.get(url, {'q': 'belgica antarctica', 'format': 'json', 'offset': 20, 'limit': 30})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'count': '1,000'})


@override_settings(URL_PREFIX=r'^data/')
class OccurrenceGridView(APITestCase):
    """Ensure HexGrid is cached and HexGrid is assigned to GBIFOccurrence within it """

    def setUp(self):
        HexGrid.objects.import_grids(grids_dir='data_manager/tests/test_data/grids/')
        geopoint = GEOSGeometry('POINT (-150 -80)', srid=4326)
        dataset = Dataset.objects.create(dataset_key='my-key')
        GBIFOccurrence.objects.create(gbifID=123, scientificName='belgica antarctica', decimalLatitude=-80,
                                      decimalLongitude=-150, geopoint=geopoint,
                                      row_json_text='belgica antarctica', dataset=dataset)
        occ = GBIFOccurrence.objects.get(gbifID=123)
        # many to many relationship between HexGrid and GBIFOccurrence
        occ.hexgrid.add(HexGrid.objects.get(geom__contains=occ.geopoint))

    def test_hexgrid_contains_occurrence(self):
        """Ensure that manytomany relationship between HexGrid and GBIFOccurrence was established"""
        occurrence = GBIFOccurrence.objects.get(gbifID=123)
        # HexGrid which contains this occurrence exists
        self.assertTrue(HexGrid.objects.filter(geom__contains=occurrence.geopoint).exists())
        grid = HexGrid.objects.get(geom__contains=occurrence.geopoint)
        # ensure join table was created for HexGrid and GBIFOccurrence
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID=123, hexgrid=grid).exists())
