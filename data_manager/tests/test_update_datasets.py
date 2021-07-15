from data_manager.management.commands.update_datasets import *
from data_manager.models import Dataset
from django.test import TestCase, override_settings
import os
import shutil
import tempfile


@override_settings(GRIDS_DIR="data_manager/tests/test_data/grids/")
class UpdateDatasetFunctionsTestCase(TestCase):
    """ Test functions in 'update_datasets' command """
    def setUp(self):
        # Dataset 7b5a19ba-f762-11e1-a439-00145eb45e9a is deleted on GBIF
        HarvestedDataset.objects.create(key="7b5a19ba-f762-11e1-a439-00145eb45e9a", include_in_antabif=True,
                                        import_full_dataset=True, deleted_from_gbif=False)
        HarvestedDataset.objects.create(key="ebe73e19-11eb-48d2-9263-fb0caa3b7b5a", include_in_antabif=True,
                                        import_full_dataset=True, deleted_from_gbif=False)
        Dataset.objects.create(title="Bacteria from Penguin Guano, Antarctica",
                               dataset_key="7b5a19ba-f762-11e1-a439-00145eb45e9a")
        Dataset.objects.create(title="Bacteria from Penguin Guano, Antarctica",
                               dataset_key="ebe73e19-11eb-48d2-9263-fb0caa3b7b5a")

    def test_delete_files_in_directory(self):
        """
        Ensure that files in directory is deleted by delete_files_in_directory()
        """
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, 'text.txt')
        with open(temp_file, 'w+') as f:
            f.write('hello')
        self.assertTrue(os.path.isfile(temp_file))
        delete_files_in_directory(temp_dir)
        self.assertFalse(os.path.isfile(temp_file))  # directory should be deleted by delete_files_in_directory
        shutil.rmtree(temp_dir)  # remove directory after test

    def test_exception_delete_files_in_directory(self):
        """
        Ensure FileNotFoundError raised when directory/file not found
        """
        with self.assertRaises(FileNotFoundError):
            delete_files_in_directory('directory-never-existed/')

    def test_get_download_key(self):
        """
        Ensure download_key can be obtained given dataset uuid, if too many simultaneous downloads,
        ensure function returns None.
        """
        download_key = get_download_key("ebe73e19-11eb-48d2-9263-fb0caa3b7b5a")
        if download_key:
            self.assertRegex(download_key, r'\d{7}\-\d{15}')  # download key has 7 digits + hyphen + 15 digits
        else:
            self.assertIsNone(download_key)

    def test_update_harvested_dataset_fk(self):
        """
        Ensure that Dataset object is assigned to HarvestedDataset foreign key 'dataset' if the Dataset exists
        """
        HarvestedDataset.objects.create(key='123', include_in_antabif=True)
        update_harvested_dataset_fk()  # ensure no Exception of Dataset.DoesNotExist thrown
        self.assertFalse(Dataset.objects.filter(dataset_key='123').exists())  # no Dataset with dataset_key=123
        # ensure that HarvestedDataset exists
        self.assertTrue(HarvestedDataset.objects.filter(key='123', include_in_antabif=True, dataset__isnull=True)
                        .exists())
        dataset = Dataset.objects.get(dataset_key="ebe73e19-11eb-48d2-9263-fb0caa3b7b5a")
        harvested_dataset = HarvestedDataset.objects.get(key="ebe73e19-11eb-48d2-9263-fb0caa3b7b5a")
        self.assertEqual(harvested_dataset.dataset_id, dataset.id)
        # dataset should also be assigned to HarvestedDataset even if the dataset is flagged deleted
        dataset = Dataset.objects.get(dataset_key="7b5a19ba-f762-11e1-a439-00145eb45e9a")
        harvested_dataset = HarvestedDataset.objects.get(key="7b5a19ba-f762-11e1-a439-00145eb45e9a")
        self.assertEqual(harvested_dataset.dataset_id, dataset.id)
