import datetime
import requests
from data_manager.models import HarvestedDataset
from data_manager.management.commands.harvest_datasets import harvest, harvest_datasets_from_installations
from django.test import TestCase, TransactionTestCase


class HarvestDatasetsTestCase(TransactionTestCase):
    """
    Test case for 'python manage.py harvest_datasets' command
    """
    def setUp(self):
        harvest([{'q': 'MAPPPD'}])

    def test_harvest(self):
        """
        Ensure that MAPPPD dataset is harvested and inserted into HarvestedDataset table.
        """
        harvested_dataset = HarvestedDataset.objects.get(key='f7c30fac-cf80-471f-8343-4ec5d8594661')
        self.assertEqual(harvested_dataset.hostingOrganizationKey, 'fb10a11f-4417-41c8-be6a-13a5c8535122')
        self.assertEqual(harvested_dataset.publishingOrganizationKey, '104e9c96-791b-4f14-978c-f581cb214912')
        self.assertEqual(harvested_dataset.hostingOrganizationTitle, 'Antarctic Biodiversity Information Facility (ANTABIF)')
        self.assertEqual(harvested_dataset.license, 'http://creativecommons.org/licenses/by/4.0/legalcode')
        self.assertEqual(harvested_dataset.publishingCountry, 'GB')
        self.assertEqual(harvested_dataset.publishingOrganizationTitle, 'SCAR - AntOBIS')
        self.assertEqual(harvested_dataset.recordCount, 3630)
        self.assertEqual(harvested_dataset.title, 'Mapping Application for Penguin Populations and Projected Dynamics (MAPPPD): Count data')
        self.assertEqual(harvested_dataset.type, 'OCCURRENCE')
        self.assertFalse(harvested_dataset.deleted_from_gbif)
        self.assertIsNone(harvested_dataset.include_in_antabif)
        self.assertIsNone(harvested_dataset.import_full_dataset)
        self.assertIsNone(harvested_dataset.dataset_id)
        self.assertEqual(harvested_dataset.harvested_on.date(), datetime.datetime.today().date())
        # ensure the Plazi.org datasets are not harvested
        self.assertFalse(HarvestedDataset.objects.filter(hostingOrganizationKey='7ce8aef0-9e92-11dc-8738-b8a03c50a862')
                         .exists())


class HarvestDatasetsFromInstallation(TestCase):
    """Ensure that harvest quits while loop upon endOfRecords = True"""

    # all datasets from AADC IPT installation are hosted by AADC
    installation_key = '1cbabffe-9073-4007-ba1e-40ebcda6e302'  # AADC IPT installation
    organization_key = '3693ff90-4c16-11d8-b290-b8a03c50a862'  # AADC hosting organization

    def setUp(self):
        harvest_datasets_from_installations(self.installation_key)

    def test_harvest(self):
        """Ensure harvest and HarvestedDataset instances created have the same count"""
        response = requests.get('https://api.gbif.org/v1/installation/{}/dataset'.format(self.installation_key))
        r = response.json()
        count = r.get('count')
        self.assertEqual(HarvestedDataset.objects.all().count(), count)
        self.assertEqual(HarvestedDataset.objects.filter(publishingOrganizationKey=self.organization_key).count(),
                         count)
