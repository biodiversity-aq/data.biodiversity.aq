# -*- coding: utf-8 -*-
from collections import defaultdict
from data_manager.models import *
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.messages import get_messages
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, tag, override_settings, Client
from django.utils.six import StringIO
from django.urls import reverse
from django.contrib.auth import get_user_model
from zipfile import is_zipfile
import datetime
import random
import secrets
import tempfile
import uuid

User = get_user_model()

TEST_USER_1 = {'username': 'user@email.com', 'password': secrets.token_hex(16)}
TEST_USER_2 = {'username': 'myuser@email.com', 'password': secrets.token_hex(16)}


@override_settings(URL_PREFIX=r'^data/')
class BaseUrlViewsTest(TestCase):
    """Ensure url resolved"""

    def setUp(self):
        """Create object for following tests"""
        d = Dataset.objects.create(dataset_key="123", title="dataset title")
        GBIFOccurrence.objects.create(gbifID=1, scientificName='my scientific name', dataset=d,
                                      decimalLatitude=0, decimalLongitude=0,
                                      row_json_text='dataset title my scientific name')

    # TEST DATASET URL PATTERNS
    def test_dataset_search(self):
        """Ensure it uses the template"""
        url = reverse('dataset-search')
        response = self.client.get(url, {'q': 'dataset title'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('dataset-list.html')

    def test_dataset_async_download(self):
        """Ensure dataset download redirect to dataset search results page"""
        url = reverse('dataset-download')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        redirected_url = reverse('login') + "?next=" + url
        self.assertRedirects(response, redirected_url)
        response = self.client.get(redirected_url)
        self.assertContains(response, "Sign in")
        self.assertTemplateUsed(response, template_name='registration/login.html')

    def test_dataset_detail(self):
        """Ensure the dataset page exists"""
        d = Dataset.objects.get(title="dataset title")
        url = reverse('dataset-detail-view', args=[d.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataset-detail.html')

    def test_dataset_activity(self):
        """Ensure this dataset page also has an activity page"""
        d = Dataset.objects.get(title="dataset title")
        url = reverse('dataset-activity', args=[d.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataset-activity.html')

    # TEST TAXON URL PATTERNS
    def test_taxon_search(self):
        """Ensure taxon search resolves"""
        url = reverse('taxon-search')
        response = self.client.get(url, {'q': 'animalia'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'taxon-list.html')

    def test_taxon_detail(self):
        """Ensure taxon detail page resolved"""
        url = reverse('taxon-detail', args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'taxon-detail.html')

    # TEST OCCURRENCE URL PATTERNS
    def test_occurrence_search(self):
        """Ensure occurrence search uses the right template"""
        url = reverse('occurrence-search')
        response = self.client.get(url, {'q': 'my scientific name'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'occurrence-list-async.html')

    def test_occurrence_async_download(self):
        """Ensure occurrence download redirects to occurrence list view"""
        url = reverse('occurrence-download')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        redirected_url = reverse('login') + "?next=" + url
        self.assertRedirects(response, redirected_url)
        response = self.client.get(redirected_url)
        self.assertContains(response, "Sign in")
        self.assertTemplateUsed(response, template_name='registration/login.html')

    # TEST API URL PATTERNS
    def test_api_db_stats(self):
        """Ensure api page resolves"""
        url = reverse('db-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_api_occurrence_grids(self):
        """Ensure api page resolves"""
        url = reverse('api-occurrence-grid')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # ALL OTHER URL PATTERNS
    def test_home(self):
        """Ensure home page resolves"""
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_haproxy(self):
        """Ensure haproxy view returns 'ok'"""
        url = reverse('haproxy')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ok', html=True)

    def test_contact(self):
        """Ensure contact resovles"""
        url = reverse('contact')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')

    def test_policy(self):
        """Ensure policyt resolves"""
        url = reverse('policy')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'policies.html')

    def test_data_source(self):
        """Ensure data source page resolves"""
        url = reverse('data-source')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data-source.html')

    def test_help(self):
        """Ensure that help resolves"""
        url = reverse('help')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'help.html')

    def test_register(self):
        """Ensure that register resolves"""
        url = reverse('register')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')


@tag('require_celery')
@override_settings(URL_PREFIX=r'^data/')
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class DownloadDatasetAsyncTest(TestCase):
    """Detail Dataset asynchronous download tests"""

    fixtures = ['occurrence_download_fixtures.json']

    def setUp(self):
        """Create Dataset, Occurrence and User objects for test"""
        User.objects.create_user(**TEST_USER_1)

    def test_objects_created(self):
        """Ensure objects are created"""
        self.assertTrue(User.objects.filter(username=TEST_USER_1.get('username')).exists())

    def test_download_without_login(self):
        """Ensure that user is redirected to sign in page when attempt to download"""
        url = reverse('dataset-download')
        query = {'q': 'antarctic dataset'}
        response = self.client.get(url, query, follow=True)
        self.assertContains(response, "Sign in")
        self.assertTemplateUsed(response, template_name='registration/login.html')

    def test_success_download_after_login(self):
        """Ensure that message is displayed to inform user that an email will be sent to user once download is ready"""
        url = reverse('dataset-download')
        query = {'q': 'antarctic dataset'}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'An email will be sent to you once the download is ready.')

    def test_download_nothing_after_login(self):
        """Ensure that message is displayed to inform user that no results to download here"""
        url = reverse('dataset-download')
        query = {'q': 'nothing to look for'}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'Nothing to download')

    def test_download_metadata_only_dataset_after_login(self):
        """Ensure that messages is displayed to inform user that download of metadata is not supported"""
        url = reverse('dataset-download')
        query = {'q': 'metadata'}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'Sorry, download of metadata-only datasets is currently not supported')

    @override_settings(MAX_OCCURRENCE_COUNT_PERMITTED=0)
    def test_download_too_many_records_after_login(self):
        """Ensure that messages is displayed to inform user that download file is too large"""
        url = reverse('dataset-download')
        query = {'q': ''}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'Download abort. File size too large')


@tag('require_celery')
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
@override_settings(URL_PREFIX=r'^data/')
class DownloadOccurrenceAsyncTest(TestCase):
    fixtures = ['occurrence_download_fixtures.json']

    def setUp(self):
        """Create Dataset, Occurrence and User objects for test"""
        User.objects.create_user(**TEST_USER_1)

    def test_user_created(self):
        """Ensure User is created."""
        self.assertTrue(User.objects.filter(username=TEST_USER_1.get('username')).exists())

    def test_download_without_login(self):
        """Ensure that user is redirected to sign in page when attempt to download"""
        url = reverse('occurrence-download')
        response = self.client.get(url, {'q': 'dataset object'}, follow=True)
        self.assertContains(response, "Sign in")
        self.assertTemplateUsed(response, template_name='registration/login.html')

    def test_download_success_after_login(self):
        """Ensure that message is displayed if download is within number of records permitted after logged in"""
        url = reverse('occurrence-download')
        query = {'taxon': [''], 'dataset': [''], 'decimal_longitude_min': ['80'], 'decimal_longitude_max': ['150'],
                 'decimal_latitude_min': ['-90'], 'q': [''], 'decimal_latitude_max': ['90']}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'An email will be sent to you once the download is ready.')
        user = User.objects.get(username=TEST_USER_1.get('username'))
        download = Download.objects.get(user=user)
        self.assertEqual(download.query, "{}".format(query))

    def test_download_no_results_after_login(self):
        url = reverse('occurrence-download')
        query = {'taxon': '', 'dataset': '', 'decimal_longitude_min': '80', 'decimal_longitude_max': '150',
                 'decimal_latitude_min': '-90', 'q': 'I am not looking for anything',
                 'decimal_latitude_max': '90'}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'Nothing to download')

    @override_settings(MAX_OCCURRENCE_COUNT_PERMITTED=0)
    def test_download_too_many_records_after_login(self):
        """Ensure that a message is displayed to inform user that download size is too large"""
        url = reverse('occurrence-download')
        query = {'taxon': '', 'dataset': '', 'decimal_longitude_min': '80', 'decimal_longitude_max': '150',
                 'decimal_latitude_min': '-90', 'q': '',
                 'decimal_latitude_max': '90'}
        c = Client()
        c.login(**TEST_USER_1)
        response = c.get(url, query, follow=True)
        storage = list(get_messages(response.wsgi_request))
        self.assertEqual(storage[0].message, 'Download abort. File size too large')


@override_settings(URL_PREFIX=r'^data/')
class DatasetListViewTest(TestCase):
    """Ensure Dataset ListView returns correct QuerySet"""
    fixtures = ['datasetlistview_fixtures.json']

    def test_person_objects_created(self):
        """Ensure that Person and PersonTypeRole objects are created correctly"""
        person_1 = Person.objects.get(full_name="Person 1", email="person1@email.com")
        person_1_new_email = Person.objects.get(full_name="Person 1", email="person1_new@email.com")
        self.assertTrue(PersonTypeRole.objects.filter(person=person_1, person_type="personnel").exists())
        self.assertTrue(PersonTypeRole.objects.filter(person=person_1, person_type="contact").exists())
        self.assertTrue(PersonTypeRole.objects.filter(person=person_1_new_email, person_type="contact").exists())

    def test_dataset_list_view_all_queryset(self):
        """Ensure all datasets are rendered in dataset list view template"""
        url = reverse('dataset-search')
        response = self.client.get(url, {'q': ''}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, template_name='dataset-list.html')
        # First dataset
        self.assertContains(response, "First dataset title", status_code=200, html=True)
        self.assertContains(response, "Antarctic Biodiversity Information Facility", status_code=200, html=True)
        self.assertContains(response, "CC BY 4.0", status_code=200, html=True)
        self.assertContains(response, "First dataset abstract", status_code=200, html=True)
        self.assertContains(response, "Occurrence dataset &bull; 90 occurrence records", html=True)
        # Second dataset
        self.assertContains(response, "Second dataset title", status_code=200, html=True)
        self.assertContains(response, "Royal Belgian Institute of Natural Sciences", status_code=200, html=True)
        self.assertContains(response, "Public domain 1.0", status_code=200, html=True)
        self.assertContains(response, "Second dataset abstract", status_code=200, html=True)
        self.assertContains(response, "Checklist dataset &bull; 200 occurrence records", html=True)
        # dataset list view should not contains these information
        # First dataset
        self.assertNotContains(response, "10", status_code=200, html=True)  # deleted_record_count
        self.assertNotContains(response, "100", status_code=200, html=True)  # full_record_count
        self.assertNotContains(response, "89", status_code=200, html=True)  # percentage_records_retained
        self.assertNotContains(response, "antabif project", status_code=200, html=True)
        self.assertNotContains(response, "antabif funding", status_code=200, html=True)
        self.assertNotContains(response, "antabif-key", status_code=200, html=True)
        # Second dataset
        self.assertNotContains(response, "0", status_code=200, html=True)  # deleted_record_count
        self.assertNotContains(response, "100", status_code=200, html=True)  # percentage_records_retained
        self.assertNotContains(response, "bedic project", status_code=200, html=True)
        self.assertNotContains(response, "bedic funding", status_code=200, html=True)
        self.assertNotContains(response, "bedic-key", status_code=200, html=True)

    def test_dataset_list_view_1_queryset(self):
        """Ensure that queryset is filtered correctly"""
        data_type = DataType.objects.get(data_type='Occurrence')
        Dataset.objects.get(title="First dataset title")
        Project.objects.get(title__contains='antabif')
        publisher = Publisher.objects.get(publisher_key="antabif-key")
        url = reverse('dataset-search')
        response = self.client.get(url, {'q': 'First dataset abstract', 'data_type': data_type.id,
                                         'project': 'antabif', 'keyword': 'Occurrence', 'publisher': publisher.id},
                                   follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, template_name='dataset-list.html')
        # First dataset
        self.assertContains(response, "First dataset title", status_code=200, html=True)
        self.assertContains(response, "Antarctic Biodiversity Information Facility", status_code=200, html=True)
        # Form initial
        self.assertContains(response, '<input type="text" name="q" value="First dataset abstract" placeholder=" search" maxlength="100" id="id_q" />', status_code=200, html=True)
        self.assertContains(response, '<input type="checkbox" name="data_type" value="{}" id="id_data_type_0" checked />'.format(data_type.id), status_code=200, html=True)
        self.assertContains(response, '<input type="checkbox" name="publisher" value="{}" id="id_publisher_0" checked />'.format(publisher.id), status_code=200, html=True)
        self.assertContains(response, '<option value="Occurrence" selected>Occurrence</option>', status_code=200, html=True)
        self.assertContains(response, '<input type="text" name="project" value="antabif" placeholder=" search project title" id="id_project" />', status_code=200, html=True)
        # dataset list view should not contains these information
        # Second dataset
        self.assertNotContains(response, "Second dataset title", status_code=200, html=True)
        self.assertNotContains(response, "Royal Belgian Institute of Natural Sciences", status_code=200, html=True)

    def test_dataset_list_view_form(self):
        """Ensure that form is populated correctly"""
        checklist = DataType.objects.get(data_type="Checklist")
        url = reverse('dataset-search')
        response = self.client.get(url, {'q': '', 'data_type': checklist.id}, follow=True)
        # Second dataset
        self.assertContains(response, "Second dataset title", status_code=200, html=True)
        self.assertContains(response, "Royal Belgian Institute of Natural Sciences", status_code=200, html=True)
        # FORM
        # data type initial and option
        self.assertContains(response, '<input type="checkbox" name="data_type" value="{}" id="id_data_type_0" checked />'.format(checklist.id), status_code=200, html=True)
        # keywords
        self.assertContains(response, '<option value="Checklist">Checklist</option>', status_code=200, html=True)
        self.assertContains(response, '<option value="RBINS">RBINS</option>', status_code=200, html=True)

    def test_project_contact_in_form(self):
        """Ensure project contact checkbox is checked"""
        dataset_1 = Dataset.objects.get(title="First dataset title")
        project = Project.objects.get(title__contains='antabif')
        project_contact = Person.objects.get(personTypeRole__person_type="personnel", personTypeRole__dataset=dataset_1,
                                             personTypeRole__project=project)
        url = reverse('dataset-search')
        response = self.client.get(url, {'q': '', 'project_contact': project_contact.id}, follow=True)
        self.assertContains(response, '<input type="checkbox" name="project_contact" value="{}" id="id_project_contact_0" checked />'.format(project_contact.id), status_code=200, html=True)

    def test_ensure_download_button_in_template(self):
        """Ensure that download button is in template"""
        url = reverse('dataset-search')
        response = self.client.get(url)
        download_url = reverse('dataset-download')
        self.assertTemplateUsed(response, 'dataset-list.html')
        self.assertContains(response,
                            '<input class="btn btn-primary" type="submit" value="Download" formaction="{}">'.format(download_url))


@override_settings(URL_PREFIX=r'^data/')
@override_settings(DOWNLOADS_DIR="data_manager/tests/test_data")
class DatasetDetailViewTest(TestCase):
    """Ensure Dataset detail populate template with the right information"""

    maxDiff = None

    def setUp(self):
        # import fixture
        out = StringIO()
        HarvestedDataset.objects.create(key='3d1231e8-2554-45e6-b354-e590c56ce9a8', include_in_antabif=True, import_full_dataset=True)
        call_command('import_datasets', '-f', 'test-import.zip', stdout=out, verbosity=3)

    def test_dataset_detail_view_context(self):
        # ensure that context contains correct information
        dataset = Dataset.objects.get(dataset_key='3d1231e8-2554-45e6-b354-e590c56ce9a8')
        url = reverse('dataset-detail-view', args=(dataset.id,))
        response = self.client.get(url)
        self.assertEqual(response.context['doi'], '10.15468/gouexm')
        self.assertQuerysetEqual(response.context['contacts'], ['<Person: Els De Bie>'])
        self.assertQuerysetEqual(response.context['contributors'], ['<Person: Els De Bie>', '<Person: Dimitri Brosens>', '<Person: Peter Desmet>'], ordered=False)
        self.assertEqual(response.context['alternate_links'], ['http://data.inbo.be/ipt/resource?r=inboveg-niche-vlaanderen-events'])
        self.assertEqual(response.context['citation'], "De Bie E, Brosens D, Desmet P (2016). InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium. Version 1.6. Research Institute for Nature and Forest (INBO). Sampling event dataset https://doi.org/10.15468/gouexm")
        self.assertEqual(response.context['keywords'], defaultdict(None, {'GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml': ['Samplingevent'], 'n/a': ['WATINA', 'groundwater dependent vegetation', 'relevés', 'terrestrial survey']}))
        self.assertQuerysetEqual(response.context['organizations'], ["('Dimitri Brosens', 'Research Institute for Nature and Forest (INBO)')", "('Els De Bie', 'Research Institute for Nature and Forest (INBO)')", "('Peter Desmet', 'Research Institute for Nature and Forest (INBO)')"], ordered=False)
        self.assertTemplateUsed(response, 'dataset-detail.html')

    def test_occurrence_dataset_template(self):
        """
        Ensure download button is rendered with the link to download for occurrence dataset
        """
        dataset = Dataset.objects.get(dataset_key='3d1231e8-2554-45e6-b354-e590c56ce9a8')
        url = reverse('dataset-detail-view', args=(dataset.id,))
        response = self.client.get(url)
        occurrence_download_url = reverse('occurrence-download')
        download_button_html = '<a href="{}?dataset={}" class="btn btn-primary"><span class="glyphicon glyphicon-download-alt"></span> Download</a>'.format(occurrence_download_url, dataset.id)
        self.assertContains(response, download_button_html, status_code=200, html=True)

    def test_metadata_dataset_template(self):
        """
        Ensure download button is rendered with the link to EML for metadata only dataset
        """
        data_type = DataType.objects.create(data_type='Metadata')
        Dataset.objects.create(dataset_key='de7916fd-f4ec-496b-9059-f4ae6ba95406', data_type=data_type)
        dataset = Dataset.objects.get(dataset_key='de7916fd-f4ec-496b-9059-f4ae6ba95406')
        url = reverse('dataset-detail-view', args=(dataset.id,))
        response = self.client.get(url)
        download_button_html = '<a href="https://api.gbif.org/v1/dataset/{}/document" class="btn btn-primary"><span class="glyphicon glyphicon-download-alt"></span> Download</a>'.format(dataset.dataset_key)
        self.assertContains(response, download_button_html, status_code=200, html=True)

    def test_other_dataset_template(self):
        """
        Ensure download button is NOT rendered for Event and Checklist dataset
        """
        data_types = ['Event', 'Checklist']
        for data_type in data_types:
            dataset_key = 'my-dataset-key-{}'.format(data_type)
            dataset_type = DataType.objects.create(data_type=data_type)
            Dataset.objects.create(dataset_key=dataset_key, data_type=dataset_type)
            dataset = Dataset.objects.get(dataset_key=dataset_key)
            url = reverse('dataset-detail-view', args=(dataset.id,))
            response = self.client.get(url)
            download_button_html = '<a href="https://api.gbif.org/v1/dataset/{}/document" class="btn btn-primary"><span class="glyphicon glyphicon-download-alt"></span> Download</a>'.format(
                dataset.dataset_key)
            self.assertNotContains(response, download_button_html, status_code=200, html=True)
            occurrence_download_url = reverse('occurrence-download')
            download_button_html = '<a href="{}?dataset={}" class="btn btn-primary"><span class="glyphicon glyphicon-download-alt"></span> Download</a>'.format(
                occurrence_download_url, dataset.id)
            self.assertNotContains(response, download_button_html, status_code=200, html=True)


@override_settings(URL_PREFIX=r'^data/')
class OccurrenceListViewTest(TestCase):
    """Tests for occurrenceListView"""
    def setUp(self):
        """Create objects for tests"""
        dataset = Dataset.objects.create(title='antarctic occurrence', dataset_key='123-456', eml_text='antarctic occurrence 123-456')
        bor = BasisOfRecord.objects.create(basis_of_record="HUMAN_OBSERVATION")
        for i in range(103):
            GBIFOccurrence.objects.create(gbifID=i, datasetKey="123-456", decimalLatitude=-80,
                                          decimalLongitude=-175, geopoint=GEOSGeometry('POINT(-175 -80)'),
                                          scientificName='electrona antarctica', taxonKey=2405929, dataset=dataset,
                                          basis_of_record=bor, row_json_text='HUMAN_OBSERVATION antarctic occurrence electrona antarctica')
        for i in range(103, 111):
            GBIFOccurrence.objects.create(gbifID=i, datasetKey="123-456", decimalLatitude=55,
                                          decimalLongitude=120, geopoint=GEOSGeometry('POINT(120 55)'),
                                          scientificName='orca orca', taxonKey=5722659, dataset=dataset,
                                          basis_of_record=bor, row_json_text='HUMAN_OBSERVATION antarctic occurrence orca orca')

    def test_objects_created(self):
        """Ensure that objects are created"""
        self.assertTrue(Dataset.objects.filter(title='antarctic occurrence').exists())
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID=0).exists())
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID=110).exists())
        self.assertFalse(GBIFOccurrence.objects.filter(gbifID=111).exists())

    def test_form_queryset_and_initial(self):
        dataset = Dataset.objects.get(title='antarctic occurrence')
        bor = BasisOfRecord.objects.get(basis_of_record='HUMAN_OBSERVATION')
        url = reverse('occurrence-search')
        response = self.client.get(url, {'q': 'electrona', 'offset': '0', 'page': '1', 'dataset': dataset.id,
                                         'basis_of_record': bor.id, 'decimal_latitude_min': '-85',
                                         'decimal_latitude_max': '-75', 'decimal_longitude_min': '-180',
                                         'decimal_longitude_max': '-170'},
                                   follow=True)
        self.assertTemplateUsed(response, 'occurrence-list-async.html')
        # form initial
        # dataset
        self.assertContains(response, '<option value="{}" selected>antarctic occurrence</option>'.format(dataset.id), status_code=200, html=True)
        # q
        self.assertContains(response, '<input type="text" name="q" value="electrona" placeholder=" search" maxlength="100" id="id_q" />', status_code=200, html=True)
        # basis of record
        self.assertContains(response, '<input type="checkbox" name="basis_of_record" value="{}" id="id_basis_of_record_0" checked />'.format(bor.id), status_code=200, html=True)
        # decimal latitude
        self.assertContains(response, '<input type="number" name="decimal_latitude_min" value="-85" step="any" id="id_decimal_latitude_0" />', status_code=200, html=True)
        self.assertContains(response, '<input type="number" name="decimal_latitude_max" value="-75" step="any" id="id_decimal_latitude_1" />', status_code=200, html=True)
        # decimal longitude
        self.assertContains(response, '<input type="number" name="decimal_longitude_min" value="-180" step="any" id="id_decimal_longitude_0" />', status_code=200, html=True)
        self.assertContains(response, '<input type="number" name="decimal_longitude_max" value="-170" step="any" id="id_decimal_longitude_1" />', status_code=200, html=True)

    def test_ensure_download_button_in_template(self):
        """Ensure that download button is in template"""
        url = reverse('occurrence-search')
        response = self.client.get(url)
        download_url = reverse('occurrence-download')
        self.assertTemplateUsed(response, 'occurrence-list-async.html')
        self.assertContains(response,
                            '<input class="btn btn-primary" type="submit" value="Download" formaction="{}">'.format(download_url))


@override_settings(URL_PREFIX=r'^data/')
class HomePageViewTest(TestCase):
    """Tests for home page view"""
    def setUp(self):
        data_type_with_record_count = {
            'Occurrence': 10,
            'Metadata': 0,
            'Sampling Event': 25,
            'Checklist': 0
        }

        for key, value in data_type_with_record_count.items():
            data_type = DataType.objects.create(data_type=key)
            Dataset.objects.create(dataset_key=uuid.uuid4(), data_type=data_type, filtered_record_count=value)

    def test_home_page_context(self):
        """Ensure home page is populated with the correct information from the context"""
        url = reverse('home')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'home.html')
        self.assertEqual(response.context['total_datasets'], 4)
        self.assertEqual(response.context['occurrence_datasets_count'], 1)
        self.assertEqual(response.context['checklists_count'], 1)
        self.assertEqual(response.context['event_datasets_count'], 1)
        self.assertEqual(response.context['total_occurrences'], 35)
        self.assertEqual(response.context['GEOSERVER_HOST'], settings.GEOSERVER_HOST)

    def test_home_page_template(self):
        """Ensure that context are rendered in template"""
        url = reverse('home')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, '<li>Total number of datasets: 4</li>')
        self.assertContains(response, '<li>Total number of metadata-only datasets: 1</li>')
        self.assertContains(response, '<li>Total number of occurrence datasets: 1</li>')
        self.assertContains(response, '<li>Total number of sampling event datasets: 1</li>')
        self.assertContains(response, '<li>Total number of checklist datasets: 1</li>')
        self.assertContains(response, '<li>Total number of occurrence records: 35</li>')


@override_settings(URL_PREFIX=r'^data/')
class TaxonListViewTest(TestCase):
    """Test for taxon list view (query GBIF through REST API)"""
    def test_form_initial(self):
        """Ensure that the form initial is populated correctly"""
        url = reverse('taxon-search')
        response = self.client.get(url, {'q': 'electrona antarctica'})
        self.assertTemplateUsed(response, 'taxon-list.html')
        self.assertContains(response, '<input type="text" name="q" value="electrona antarctica" placeholder=" search" maxlength="100" id="id_q" />', status_code=200, html=True)

    def test_pagination(self):
        """Ensure that Previous/Next page button for pagination works when there are >20 results returned"""
        url = reverse('taxon-search')
        # First page, contains <Next> only
        response = self.client.get(url, {'q': 'animalia'})
        self.assertTemplateUsed(response, 'taxon-list.html')
        self.assertContains(response, 'Next')
        # second page, contains <Previous> and <Next>
        response = self.client.get(url, {'q': 'animalia', 'offset': 20})
        self.assertContains(response, 'Previous')
        self.assertContains(response, 'Next')

    def test_negative_offset(self):
        """Negative offset will fail silently and reset offset value to 0"""
        url = reverse('taxon-search')
        response = self.client.get(url, {'q': 'animalia', 'offset': -1})
        self.assertTemplateUsed(response, 'taxon-list.html')
        self.assertContains(response, 'Next', status_code=200, html=True)
        self.assertNotContains(response, 'Previous', status_code=200, html=True)


@override_settings(URL_PREFIX=r'^data/')
class TaxonDetailViewTest(TestCase):
    """Tests for taxon detail view"""
    def setUp(self):
        """Create occurrences with taxonKey = 1"""
        GBIFOccurrence.objects.create(gbifID=1, taxonKey=2405929, kingdomKey=1, geopoint=GEOSGeometry('POINT(-175 -80)'))

    def test_use_correct_template(self):
        """Ensure that the right template is rendered"""
        url = reverse('taxon-detail', args=(1,))
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'taxon-detail.html')

    def test_gbif_taxon(self):
        """Ensure that occurrences are returned"""
        url = reverse('taxon-detail', args=(1,))
        response = self.client.get(url)
        self.assertTrue(response.context['has_occurrence'])

    def test_worms_taxon(self):
        """Ensure that only taxa from GBIF taxonomy backbone returns occurrences"""
        url = reverse('taxon-detail', args=(154946057,))  # taxonKey for animalia (WoRMS)
        response = self.client.get(url)
        self.assertFalse(response.context['has_occurrence'])


@override_settings(URL_PREFIX=r'^data/')
class RegistrationTest(TestCase):

    def test_success_user_registration(self):
        """
        Ensure the flow of registration include sending email, redirect user to home page, show message on
        home page
        """
        url = reverse('register')
        response = self.client.post(url, {'username': TEST_USER_1.get('username'),
                                          'password1': TEST_USER_1.get('password'),
                                          'password2': TEST_USER_1.get('password'),
                                          'accept_terms': True})
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed(response, 'registration/acc_active_email.html')  # template used to send email
        self.assertEqual(len(mail.outbox), 1)  # email is sent
        self.assertRedirects(response, reverse('home'))  # redirects to home after user registration
        storage = list(get_messages(response.wsgi_request))
        # test messages appear on home page after redirection
        self.assertEqual(storage[0].message,
                         "Thank you. Please confirm your email address to complete the registration.")
        self.assertTrue(User.objects.filter(username=TEST_USER_1.get('username')).exists())  # user created

    def test_not_agree_terms(self):
        """
        Ensure the registration will be unsuccuessful and a user object will not be created if User did not check the
        agree to terms checkbox.
        """
        url = reverse('register')
        response = self.client.post(url, {'username': TEST_USER_2.get('username'),
                                          'password1': TEST_USER_2.get('password'),
                                          'password2': TEST_USER_2.get('password'),
                                          'accept_terms': False})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, 'registration/acc_active_email.html')  # template used to send email
        self.assertEqual(len(mail.outbox), 0)  # email is sent
        self.assertFalse(User.objects.filter(username=TEST_USER_2.get('username')).exists())  # user not created

    def test_numeric_password_only_registration(self):
        """Ensure to ask user retype password again if password is only numeric"""
        url = reverse('register')
        # nosec this part because the test is to ensure numeric only passwords are unacceptable by registration form
        random_int = random.randint(21035435135484, 3651384305168484)  # nosec
        response = self.client.post(url, {'username': TEST_USER_2.get('username'), 'password1': random_int,
                                          'password2': random_int, 'accept_terms': True})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertEqual(len(mail.outbox), 0)  # no email is sent
        self.assertFalse(User.objects.filter(username=TEST_USER_2.get('username')).exists())  # user not created

    def test_password_do_not_match(self):
        """Ensure to ask user retype password again if password is only numeric"""
        url = reverse('register')
        response = self.client.post(url, {'username': TEST_USER_2.get('username'),
                                          'password1': TEST_USER_2.get('password'),
                                          'password2': secrets.token_hex(16),
                                          'accept_terms': True})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertEqual(len(mail.outbox), 0)  # no email is sent
        self.assertFalse(User.objects.filter(username=TEST_USER_2.get('username')).exists())  # user not created

    def test_existing_user(self):
        """Ensure that existing user cannot register again"""
        User.objects.create_user(**TEST_USER_1)
        self.assertTrue(User.objects.filter(username=TEST_USER_1.get('username')).exists())
        url = reverse('register')
        response = self.client.post(url, {'username': TEST_USER_1.get('username'),
                                          'password1': TEST_USER_1.get('password'),
                                          'password2': TEST_USER_1.get('password'),
                                          'accept_terms': True})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertEqual(len(mail.outbox), 0)  # no email is sent
        self.assertEqual(User.objects.filter(username=TEST_USER_1.get('username')).count(), 1)


@override_settings(URL_PREFIX=r'^data/')
class LoginViewTest(TestCase):
    """Tests for loginView"""

    def setUp(self):
        """Create user object for login test"""
        User.objects.create_user(**TEST_USER_1)

    def test_login_template(self):
        url = reverse('login')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login(self):
        """Test logging user in with correct credentials"""
        url = reverse('login')
        response = self.client.post(url, TEST_USER_1)
        self.assertEqual(response.status_code, 302)  # redirection
        self.assertRedirects(response, reverse('home'))  # redirects to home after user registration

    def test_login_without_register(self):
        """Ensure that an alert will be shown if user is inputing wrong username/password"""
        url = reverse('login')
        response = self.client.post(url, TEST_USER_2)
        self.assertEqual(response.status_code, 200)  # no redirection
        self.assertContains(response, '<div class="alert alert-danger" role="alert">Please enter a correct username and password. Note that both fields may be case-sensitive.</div>', html=True)


@override_settings(URL_PREFIX=r'^data/')
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class DownloadsTest(TestCase):
    """Tests for downloads view"""
    def setUp(self):
        # Create user object
        user = User.objects.create_user(**TEST_USER_1)
        # Create an download object from that user
        d = Download(user=user, task_id='user@example.com_2018-04-23T085301')
        d.file = SimpleUploadedFile('user@example.com_2018-04-23T085301.zip', b'these are the file contents')
        d.save()

    def test_download_object_created(self):
        self.assertTrue(Download.objects.filter(task_id='user@example.com_2018-04-23T085301').exists())

    def test_download_page(self):
        """Ensure that download page displays file is working"""
        self.client.login(**TEST_USER_1)
        url = reverse('my-downloads')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        # ensure that the file name is listed on the page
        self.assertContains(response, 'user@example.com_2018-04-23T085301', status_code=200, html=True)


@override_settings(URL_PREFIX=r'^data/')
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class GetDownloadTest(TestCase):
    """Test for get_download view"""

    def setUp(self):
        # create Dataset object
        Dataset.objects.create(dataset_key='111', title='test dataset', eml_text='test dataset 111')
        # Create user object
        user = User.objects.create_user(**TEST_USER_1)
        # get dataset object
        dataset = Dataset.objects.get(dataset_key='111')
        # Create a download object from that user
        d = Download(user=user, task_id='user@example.com_2018-04-23T085301')
        d.file = SimpleUploadedFile('user@example.com_2018-04-23T085301.zip', b'these are the file contents')
        d.save()
        # add dataset to download object
        download = Download.objects.get(user=user, task_id='user@example.com_2018-04-23T085301')
        download.dataset.add(dataset)

    def test_get_download_without_login(self):
        """Ensure download will not be successful if user is not login"""
        user = User.objects.get(username=TEST_USER_1.get('username'))
        download = Download.objects.get(user=user)
        # download link as response
        url = reverse('my-download-file', args=[download.id])
        response = self.client.get(url, follow=True)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertContains(response, '<h2>Sign in</h2>', html=True)

    def test_get_download_after_login(self):
        """Ensure download will happen if user successfully login"""
        user = User.objects.get(username=TEST_USER_1.get('username'))
        download = Download.objects.get(user=user)
        self.client.login(**TEST_USER_1)
        url = reverse('my-download-file', args=[download.id])
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        # ensure the content of the file is as written
        self.assertEqual(response.content, b'these are the file contents')


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
@override_settings(URL_PREFIX=r'^data/')
class DatasetActivityTest(TestCase):
    """Test case for dataset_activity view"""
    def setUp(self):
        # avoid creating files in development environment which needs effort to delete
        # Dataset object
        dataset = Dataset.objects.create(title='test dataset', dataset_key='123456', eml_text='test dataset 123456')
        # User object
        User.objects.create_user(**TEST_USER_1)
        user = User.objects.get(username=TEST_USER_1.get('username'))
        # Download object from that user
        d = Download(user=user, task_id='user@example.com_2018-04-23T085301')
        d.file = SimpleUploadedFile('user@example.com_2018-04-23T085301.zip', b'these are the file contents')
        d.save()
        download = Download.objects.get(task_id='user@example.com_2018-04-23T085301')
        download.dataset.add(dataset)

    def test_dataset_activity_context(self):
        """Ensure that the correct template is used"""
        dataset = Dataset.objects.get(dataset_key='123456')
        url = reverse('dataset-activity', args=[dataset.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataset-activity.html')
        self.assertContains(response, '<p>Total number of downloads: 1</p>', status_code=200, html=True)

    def test_multiple_datasets(self):
        """Ensure that template shows total number of downloads of specific dataset"""
        Dataset.objects.create(title='another dataset', dataset_key='223456', eml_text='another dataset 223456')
        dataset = Dataset.objects.get(dataset_key='123456')
        url = reverse('dataset-activity', args=[dataset.id])
        response = self.client.get(url)
        self.assertContains(response, '<p>Total number of downloads: 1</p>', status_code=200, html=True)

    def test_multiple_downloads_multiple_datasets(self):
        """Ensure that template shows correct number of downloads"""
        datasets = Dataset.objects.all()
        user = User.objects.get(username=TEST_USER_1.get('username'))
        for i in range(2):
            name = '{}_{}'.format(user, i)
            d = Download(user=user, task_id=name)
            d.file = SimpleUploadedFile('name', b'these are the file contents')
            d.save()
            download = Download.objects.get(task_id=name)
            for dataset in datasets:
                download.dataset.add(dataset)
        dataset = Dataset.objects.get(dataset_key='123456')
        url = reverse('dataset-activity', args=[dataset.id])
        response = self.client.get(url)
        # expect 11 downloads (1 in setUp, 10 in this function)
        self.assertContains(response, '<p>Total number of downloads: 3</p>', status_code=200, html=True)

    def test_template_no_download(self):
        """Ensure that template doesn't show None if download count is 0"""
        Dataset.objects.create(dataset_key='1')
        dataset = Dataset.objects.get(dataset_key='1')
        url = reverse('dataset-activity', args=[dataset.id])
        response = self.client.get(url)
        self.assertContains(response, '<p>Total number of downloads: 0</p>', status_code=200, html=True)


@override_settings(URL_PREFIX=r'^data/')
class HaproxyViewTest(TestCase):
    """Ensure haproxy view resolve"""

    def test_haproxy_append_slash_false(self):
        """if the request URL does not match any of the patterns in the URLconf and it doesn’t end in a slash,
        an HTTP redirect is issued to the same URL with a slash appended"""
        url = reverse('haproxy')
        response = self.client.get(url.rstrip('/'))  # remove last slash in url
        self.assertEqual(response.status_code, 301)

