from data_manager.models import Download, Dataset
from data_manager.tasks import prepare_download
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from unittest.mock import patch
import dateutil.parser
import datetime
import secrets
import zipfile


TEST_USER_1 = {'username': 'user@email.com', 'password': secrets.token_hex(16)}


class UpdateDatasetsTestCase(TestCase):

    def setUp(self):
        """Create objects for test"""
        Dataset.objects.create(title='Penguins of Antarctica', dataset_key='7b657080-f762-11e1-a439-00145eb45e9a',
                               download_on=dateutil.parser.parse('2010-08-06T13:05:40.000+0000'))
        Dataset.objects.create(title='Antarctic, Sub-Antarctic and cold temperate echinoid database',
                               dataset_key='d8b06df0-81b3-41c9-bcf8-6ba5242e2b95',
                               download_on=dateutil.parser.parse('2110-04-06T13:05:40.000+0000'))

    def test_objects_created(self):
        """Ensure that objects are created"""
        d = Dataset.objects.get(title='Penguins of Antarctica')
        self.assertEqual(d.dataset_key, '7b657080-f762-11e1-a439-00145eb45e9a')
        self.assertEqual(d.download_on, datetime.datetime(2010, 8, 6, 13, 5, 40))
        d = Dataset.objects.get(dataset_key='d8b06df0-81b3-41c9-bcf8-6ba5242e2b95')
        self.assertEqual(d.download_on, datetime.datetime(2110, 4, 6, 13, 5, 40))

    def test_compare_datetime(self):
        """Ensure that datetime objects are comparable, test will fail if USE_TZ is set to True because now is
        naive datetime object (tzinfo=None)"""
        dataset = Dataset.objects.get(dataset_key='d8b06df0-81b3-41c9-bcf8-6ba5242e2b95')
        another_date = parse_datetime('2017-10-03T08:55:38.044+0000')
        another_date = another_date.replace(tzinfo=None)
        self.assertTrue(dataset.download_on > now())
        self.assertTrue(dataset.download_on > another_date)


class GenerateDownloadFile(TestCase):
    """Test case to ensure Download file is generated correctly"""
    fixtures = ['occurrence_download_fixtures.json']
    maxDiff = None

    def setUp(self):
        user = User.objects.create_user(**TEST_USER_1)
        user.save()

    def test_generate_occurrence_download_file_success(self):
        """Ensure download file is generated for Dataset query"""
        user = User.objects.get(username=TEST_USER_1.get('username'))
        query = {'taxon': [''], 'dataset': [''], 'decimal_longitude_min': [80], 'decimal_longitude_max': [150],
                 'decimal_latitude_min': [-90], 'q': ['Halobaena caerulea (Gmelin, 1789) Tromsø'],
                 'decimal_latitude_max': [90]}
        download = Download.objects.create(user=user, query=query)
        task_id = prepare_download('GBIFOccurrence', user_id=user.id, download_link='http://testserver',
                                   download_id=download.id)
        download = Download.objects.get(task_id=task_id, user=user, query=query)
        self.assertEqual(download.record_count, 1)
        # ensure the file is written correctly
        with zipfile.ZipFile(download.file) as myzip:
            with myzip.open('None.csv', 'r') as myfile:  # testing python function, so no celery task id
                byte_lines = myfile.read()  # Return the bytes of the file with csv_name in the archive
                field_names = byte_lines.splitlines()[0]  # split the bytes on \r\n, first line is field name
                field_names_str = field_names.decode('utf-8')  # decode to utf-8
                occurrence_fields_str = ','.join(settings.OCCURRENCE_FIELDS)  # convert list to csv
                self.assertEqual(field_names_str, occurrence_fields_str)  # check if they are equal
                content = byte_lines.splitlines()[1]  # second line
                content_str = content.decode('utf-8')
                self.assertEqual(content_str, '2,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,20.0,130.0,,,,"Halobaena caerulea (Gmelin, 1789) Tromsø",,,,,,,,,,,,,,occurrence-download-fixture,1')

    def test_generate_dataset_download_file_success(self):
        """Ensure download file is generated for Dataset query"""
        user = User.objects.get(username=TEST_USER_1.get('username'))
        query = {'q': ['antarctic dataset'], 'data_type': [2]}
        download = Download.objects.create(user=user, query=query)
        task_id = prepare_download('Dataset', user_id=user.id, download_link='http://testserver', download_id=download.id)
        download = Download.objects.get(task_id=task_id, user=user, query=query)
        self.assertEqual(download.record_count, 1)
        # ensure the file is written correctly
        with zipfile.ZipFile(download.file) as myzip:
            with myzip.open('None.csv', 'r') as myfile:  # testing python function, so no celery task id
                byte_lines = myfile.read()  # Return the bytes of the file with csv_name in the archive
                field_names = byte_lines.splitlines()[0]  # split the bytes on \r\n, first line is field name
                field_names_str = field_names.decode('utf-8')  # decode to utf-8
                occurrence_fields_str = ','.join(settings.OCCURRENCE_FIELDS)  # convert list to csv
                self.assertEqual(field_names_str, occurrence_fields_str)  # check if they are equal
                content = byte_lines.splitlines()[1]  # second line
                content_str = content.decode('utf-8')
                self.assertEqual(content_str, '21,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,20.0,120.0,,,,belgica antarctica,,,,,,,,,,,,,,antarctic-dataset,2')
