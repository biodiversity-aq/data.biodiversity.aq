# -*- coding: utf-8 -*-
from django.core.management import call_command
from django.test import TestCase, override_settings, SimpleTestCase
from data_manager.management.commands.import_datasets import *
import datetime
import os


@override_settings(GRIDS_DIR="data_manager/tests/test_data/grids/")
@override_settings(DOWNLOADS_DIR="data_manager/tests/test_data/")
class ImportDatasetsTest(TestCase):
    """
    Test the outcome of django-admin commands `python manage.py import_datasets`
    """
    # see full print out if test fail
    maxDiff = None

    def setUp(self):
        # to avoid having to load grids - time consuming
        HexGrid.objects.create(left=-7950000.0, bottom=-7678762.16044571, right=-7916666.65112499,
                               top=-7649894.63352675,
                               geom='MULTIPOLYGON (((-7950000 -7664328.39698623, -7941666.662781247 -7649894.633526745,'
                                    ' -7924999.988343742 -7649894.633526745, -7916666.651124989 -7664328.39698623, '
                                    '-7924999.988343742 -7678762.160445714, -7941666.662781247 -7678762.160445714, '
                                    '-7950000 -7664328.39698623)))')
        HarvestedDataset.objects.create(key="3d1231e8-2554-45e6-b354-e590c56ce9a8", include_in_antabif=True,
                                        import_full_dataset=True)
        # create these objects to ensure that GBIFOccurrence instances without Dataset will be deleted by
        # import_datasets command.
        for i in range(1, 50):
            GBIFOccurrence.objects.create(gbifID=i)

    def test_import(self):
        """
        Ensure all objects were imported as expected
        """
        call_command('import_datasets', '-f', 'test-import.zip')
        query = DataType.objects.get(dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.data_type, 'Sampling Event')
        # ---------------
        # Publisher
        # ---------------
        # ensure publisher objects created as expected
        query = Publisher.objects.get(dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.publisher_key, '1cd669d0-80ea-11de-a9d0-f1765f95f18b')
        self.assertEqual(query.publisher_name, 'Research Institute for Nature and Forest (INBO)')
        # ---------------
        # Project
        # ---------------
        # ensure Project objects are imported correctly
        query = Project.objects.filter(dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertFalse(query.exists())
        # ---------------
        # HarvestedDataset
        # ---------------
        # ensure HarvestedDataset object was assigned a dataset fk
        query = HarvestedDataset.objects.get(dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        dataset = Dataset.objects.get(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.dataset_id, dataset.id)
        # ---------------
        # Dataset
        # ---------------
        # ensure Dataset fields are populated correctly.
        query = Dataset.objects.get(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        # ensure that GBIFOccurrence without dataset from setUp is deleted
        self.assertEqual(GBIFOccurrence.objects.filter(gbifID=123).exists(), False)
        # Dataset class
        self.assertEqual(query.dataset_key, "3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.alternate_identifiers,
                         ["10.15468/gouexm", "http://data.inbo.be/ipt/resource?r=inboveg-niche-vlaanderen-events",
                          "3d1231e8-2554-45e6-b354-e590c56ce9a8"])
        self.assertEqual(query.doi, "10.15468/gouexm")
        self.assertEqual(query.title,
                         "InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium")
        self.assertEqual(query.bounding_box.coords,
                         (((2.54, 50.68), (2.54, 51.51), (5.92, 51.51), (5.92, 50.68), (2.54, 50.68)),))  # GIS bbox
        self.assertEqual(query.bounding_box.geom_type, 'Polygon')  # GIS bbox
        self.assertEqual(query.pub_date, datetime.date(2016, 8, 3))
        self.assertEqual(query.download_on, datetime.datetime(2018, 10, 19, 12, 23, 38))
        self.assertEqual(query.intellectual_right, "Public Domain (CC0 1.0)")
        self.assertEqual(query.citation,
                         "De Bie E, Brosens D, Desmet P (2016). InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium. Version 1.6. Research Institute for Nature and Forest (INBO). Sampling event dataset https://doi.org/10.15468/gouexm accessed via GBIF.org on 2018-10-19.")
        self.assertEqual(query.tag, [])
        self.assertEqual(query.full_record_count, 8593)
        self.assertEqual(query.filtered_record_count, GBIFOccurrence.objects.filter(
            dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8").count())
        self.assertEqual(query.deleted_record_count, 8584)  # the dwca is reduced to only 10 records for tests
        self.assertEqual(query.percentage_records_retained, 0.105)
        # ---------------
        # Person
        # ---------------
        # Ensure Person objects are imported correctly
        els_debie = Person.objects.get(given_name="Els", surname="De Bie")
        self.assertEqual(els_debie.full_name, "Els De Bie")
        self.assertEqual(els_debie.email, "els.debie(a)inbo.be")
        # ---------------
        # PersonTypeRole
        # ---------------
        # ensure PersonTypeRole objects are imported correctly
        self.assertEqual(PersonTypeRole.objects.filter(person__full_name="Els De Bie",
                                                       dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8").count(),
                         3)
        dimitri_brosens = PersonTypeRole.objects.get(person_type="creator", person__full_name="Dimitri Brosens")
        self.assertEqual(dimitri_brosens.dataset.dataset_key, "3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(dimitri_brosens.project, None)
        self.assertEqual(dimitri_brosens.person_type, "creator")
        # ---------------
        # Keyword
        # ---------------
        # 1 thesaurus 1 keyword
        sampling_event = Keyword.objects.get(keyword="Samplingevent")
        self.assertEqual(sampling_event.thesaurus,
                         "GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml")
        self.assertQuerysetEqual(sampling_event.dataset.values("dataset_key"),
                                 ["{'dataset_key': '3d1231e8-2554-45e6-b354-e590c56ce9a8'}"])
        # 1 thesaurus N keywords
        na_thesaurus = Keyword.objects.filter(thesaurus="n/a").values_list("keyword", flat=True)
        self.assertEqual(sorted(na_thesaurus),
                         sorted(["groundwater dependent vegetation", "relevés", "terrestrial survey", "WATINA"]))
        # ---------------
        # GBIFOccurrence
        # ---------------
        query = GBIFOccurrence.objects.get(gbifID="1316184895")
        self.assertEqual(query.gbifID, "1316184895")
        self.assertEqual(query.accessRights, "http://www.inbo.be/en/norms-for-data-use")
        self.assertEqual(query.license, "CC0_1_0")
        self.assertEqual(query.rightsHolder, "INBO")
        self.assertEqual(query._type, "Event")
        self.assertEqual(query.datasetID, "http://dataset.inbo.be/inboveg-niche-vlaanderen-events")
        self.assertEqual(query.institutionCode, "INBO")
        self.assertEqual(query.datasetName,
                         '"InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium"')
        self.assertEqual(query.basisOfRecord, "HUMAN_OBSERVATION")
        self.assertEqual(query.occurrenceID, "INBO:INBOVEG:OCC:00407292")
        self.assertEqual(query.recordedBy, "Els De Bie")
        self.assertEqual(query.organismQuantity, "p1")
        self.assertEqual(query.organismQuantityType, "londo Scale (1976)")
        self.assertEqual(query.occurrenceStatus, "present")
        self.assertEqual(query.eventID, "INBO:INBOVEG:0IV2013102211361614")
        self.assertEqual(query.eventDate, "2004-07-02T00:00:00Z")
        self.assertEqual(query.verbatimEventDate, "2004-07-02/2004-07-02")
        self.assertEqual(query.samplingProtocol, "vegetation plot with Londo scale (1976): mosses identified")
        self.assertEqual(query.sampleSizeValue, "9")
        self.assertEqual(query.sampleSizeUnit, "m²")
        self.assertEqual(query.locationID, "SNOP027X")
        self.assertEqual(query.continent, "EUROPE")
        self.assertEqual(query.countryCode, "BE")
        self.assertEqual(query.verbatimLocality, "Snoekengracht")
        self.assertEqual(query.locationAccordingTo, "MILKLIM-areas")
        self.assertEqual(query.verbatimCoordinateSystem, "Belgian Lambert 72")
        self.assertEqual(query.verbatimSRS, "Belgium Datum 1972")
        self.assertEqual(query.taxonID, "INBSYS0000010112")
        self.assertEqual(query.scientificName, "Cerastium fontanum subsp. vulgare (Hartm.) Greuter & Burdet")
        self.assertEqual(query.kingdom, "Plantae")
        self.assertEqual(query.phylum, "Tracheophyta")
        self.assertEqual(query._class, "Magnoliopsida")
        self.assertEqual(query.order, "Caryophyllales")
        self.assertEqual(query.family, "Caryophyllaceae")
        self.assertEqual(query.genus, "Cerastium")
        self.assertEqual(query.specificEpithet, "fontanum")
        self.assertEqual(query.infraspecificEpithet, "vulgare")
        self.assertEqual(query.taxonRank, "SUBSPECIES")
        self.assertEqual(query.datasetKey, "3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.taxonKey, "3811517")
        self.assertEqual(query.kingdomKey, '6')
        self.assertEqual(query.phylumKey, "7707728")
        self.assertEqual(query.classKey, "220")
        self.assertEqual(query.orderKey, "422")
        self.assertEqual(query.familyKey, "2518")
        self.assertEqual(query.genusKey, "2873815")
        self.assertEqual(query.subgenusKey, "")
        self.assertEqual(query.speciesKey, "3085458")
        #  field
        self.assertEqual(query.decimalLatitude, 50.83567)
        self.assertEqual(query.decimalLongitude, 4.84022)
        self.assertEqual(query.coordinateUncertaintyInMeters, 30)
        self.assertEqual(query.coordinatePrecision, None)
        self.assertEqual(query.geopoint.coords, (4.84022, 50.83567))  # GIS field
        self.assertEqual(query.modified, '')
        self.assertEqual(query.year, 2004)
        self.assertEqual(query.month, 7)
        self.assertEqual(query.day, 2)
        self.assertEqual(bool(query.date_created), True)  # DateTimeField with auto_now_add=True
        self.assertEqual(bool(query.date_last_modified), True)  # DateTimeField with auto_now_add=True
        self.assertEqual(query.depth, None)
        # foreign keys
        self.assertEqual(query.dataset.dataset_key, "3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(query.basis_of_record.basis_of_record, "HUMAN_OBSERVATION")
        # ensure that headers of occurrence and verbatim are not created as object
        self.assertEqual(GBIFVerbatimOccurrence.objects.filter(gbifID="gbifID").exists(), False)
        self.assertEqual(GBIFOccurrence.objects.filter(gbifID="1316184895").exists(), True)
        # no test for row_json
        # ensure GBIFOccurrence object will still be created if datasetKey field is empty
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID="1316184894").exists())
        # ---------
        # VERBATIM
        # ---------
        # ensure that the number of GBIFOccurrence & GBIFVerbatim objects created are correct
        # remove duplicated gbifID, so become 9 records of GBIFOccurrence
        self.assertEqual(GBIFOccurrence.objects.filter(
            dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8").count(), 9)
        verbatim_gbifid = ["1316184895", "1316184894"]
        # self.assertEqual(GBIFVerbatimOccurrence.objects.filter(gbifID__in=verbatim_gbifid).count(), 2)
        ### disable verbatim import for now
        # self.assertEqual(GBIFVerbatimOccurrence.objects.filter(gbifID__in=verbatim_gbifid).count(), 2)
        # ensure that only one row is inserted into database
        self.assertEqual(GBIFOccurrence.objects.filter(gbifID="1316184895").count(), 1)
        # verbatim.txt of this dwca also contains 2 identical rows with gbifID="1316184895"
        # self.assertEqual(GBIFVerbatimOccurrence.objects.filter(gbifID="1316184895").count(), 1)
        # occurrence without dataset FK should be deleted by import_datasets command
        self.assertFalse(GBIFOccurrence.objects.filter(dataset__isnull=True).exists())

    def test_verbatim_import(self):
        """
        Ensure GBIFOccurrence and GBIFVerbatimOccurrence instances are created. A verbatim occurrence not associated
        with an occurrence record will not be created.

        occurrence.txt
        gbifID
        1316184895
        1316184895 (duplicated ID)
        1316184894
        1316184893

        verbatim.txt
        gbifID
        1316184895
        1316184895 (duplicated ID)
        1316184894
        1316184893
        1316184892 (only present in verbatim.txt but absent in occurrence.txt)
        """
        with self.settings(DOWNLOADS_DIR="data_manager/tests/test_data"):
            call_command('import_datasets', '-f', 'import-verbatim-without-occurrence-gbifID.zip')
        d = Dataset.objects.get(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(GBIFOccurrence.objects.filter(dataset=d).count(), 3)
        # self.assertEqual(GBIFVerbatimOccurrence.objects.filter(occurrence__dataset=d).count(), 3)
        # disable verbatim import for now
        self.assertEqual(GBIFVerbatimOccurrence.objects.filter(occurrence__dataset=d).count(), 0)
        self.assertEqual(d.full_record_count, 8593)
        self.assertEqual(d.filtered_record_count, 3)
        self.assertEqual(d.deleted_record_count, 8590)
        self.assertEqual(d.percentage_records_retained, 0.035)

    def test_import_with_filter(self):
        """
        Ensure that non antarctic occurrence records, duplicated occurrence, duplicated verbatim and verbatim
        without occurrence record will not be imported.

        Ensure filter works correctly - only unique antarctic/subantarctic occurrence and verbatim occurrence
        records are imported.
        occurrence.txt
        gbifID        decimalLatitude     decimalLongitude  remarks
        1316184895    50.83567            4.84022           not antarctic
        1316184895    50.83567            4.84022           duplicated - not antarctic
        1316184894    -85                 -86               antarctic
        1316184893    -85                 -87               antarctic

        verbatim.txt
        gbifID        decimalLatitude     decimalLongitude  remarks
        1316184895    50.83567            4.84022           not antarctic
        1316184895    50.83567            4.84022           duplicated - not antarctic
        1316184894    -85                 -86               antarctic
        1316184893    -85                 -87               antarctic
        1316184892    -85                 -88               has no record in occurrence.txt
        """
        harvested_dataset = HarvestedDataset.objects.get(key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        harvested_dataset.import_full_dataset = False
        harvested_dataset.save()
        with self.settings(DOWNLOADS_DIR="data_manager/tests/test_data"):
            call_command('import_datasets', '-f', 'test-import-filter.zip')
        d = Dataset.objects.get(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        self.assertEqual(d.filtered_record_count, 2)
        self.assertEqual(d.full_record_count, 8593)
        self.assertEqual(d.deleted_record_count, 8591)
        self.assertEqual(GBIFOccurrence.objects.count(), 2)
        self.assertEqual(GBIFVerbatimOccurrence.objects.count(), 0)  # disable verbatim import for now
        # self.assertEqual(GBIFVerbatimOccurrence.objects.count(), 2)
        self.assertFalse(GBIFOccurrence.objects.filter(gbifID=1316184895).exists())
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID=1316184894).exists())
        self.assertTrue(GBIFOccurrence.objects.filter(gbifID=1316184893).exists())
        self.assertFalse(GBIFVerbatimOccurrence.objects.filter(gbifID=1316184895).exists())
        # disable verbatim import for now
        # self.assertTrue(GBIFVerbatimOccurrence.objects.filter(gbifID=1316184894).exists())
        # self.assertTrue(GBIFVerbatimOccurrence.objects.filter(gbifID=1316184893).exists())
        self.assertFalse(GBIFVerbatimOccurrence.objects.filter(gbifID=1316184892).exists())


class ImportDatasetFunctionsTest(TestCase):
    """
    Test functions in import_datasets command
    """

    def setUp(self):
        HarvestedDataset.objects.create(key='f7c30fac-cf80-471f-8343-4ec5d8594661', include_in_antabif=True,
                                        type='OCCURRENCE')
        HarvestedDataset.objects.create(key='6899818d-a6f5-4a18-81d2-047d84ee28b8', include_in_antabif=True,
                                        type='OCCURRENCE')
        Dataset.objects.create(dataset_key='4fa7b334-ce0d-4e88-aaae-2e0c138d049e')
        # metadata only dataset
        # new metadata-only dataset to be imported
        HarvestedDataset.objects.create(key='93d9eebd-2b10-4cdc-a699-21e11723001d', include_in_antabif=True,
                                        import_full_dataset=True, type='METADATA', dataset=None)
        # outdated metadata only dataset
        metadata_type = DataType.objects.create(data_type='Metadata')
        HarvestedDataset.objects.create(key='a5aa5dde-aba1-475e-8781-d3a451b0eb15', type='METADATA',
                                        include_in_antabif=True, import_full_dataset=True)
        Dataset.objects.create(dataset_key='a5aa5dde-aba1-475e-8781-d3a451b0eb15', data_type=metadata_type,
                               download_on=datetime.datetime(2000, 1, 1))

    def test_get_metadata_dataset_to_download(self):
        """
        Ensure that outdated and new metadata only HarvestedDataset is returned
        """

        metadata_datasets = get_metadata_dataset_to_download()
        self.assertEqual(metadata_datasets.count(), 2)
        self.assertQuerysetEqual(metadata_datasets.values('key'),
                                 ["{'key': '93d9eebd-2b10-4cdc-a699-21e11723001d'}",
                                  "{'key': 'a5aa5dde-aba1-475e-8781-d3a451b0eb15'}"], ordered=False)

    @override_settings(DOWNLOADS_DIR="data_manager/tests/test_data/")
    def test_get_archives(self):
        """Ensure that archives to be imported are found by get_archives()"""
        archives = get_archives(settings.DOWNLOADS_DIR)
        path = os.path.join(settings.DOWNLOADS_DIR, 'test-import.zip')
        self.assertIn(path, archives)

    @override_settings(DOWNLOADS_DIR="tests/test_data/")
    def test_get_archives_exception(self):
        """Ensure exception is raised if directory not found by get_archives()"""
        self.assertRaises(CommandError, get_archives, settings.DOWNLOADS_DIR)

    def test_remove_duplicate(self):
        """
        Ensure duplicated objects are removed
        """
        BasisOfRecord.objects.create(basis_of_record="HumanObservation")
        BasisOfRecord.objects.create(basis_of_record="HumanObservation")
        BasisOfRecord.objects.create(basis_of_record="HumanObservation")
        remove_duplicates(BasisOfRecord.objects.all())
        self.assertEqual(BasisOfRecord.objects.all().count(), 1)

    def test_delete_dataset_flagged_include_in_antabif_to_false(self):
        """
        Ensure that HarvestedDataset with include_in_antabif changed to False will have corresponding Dataset deleted.
        """
        dataset = Dataset.objects.create(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        HarvestedDataset.objects.create(key="3d1231e8-2554-45e6-b354-e590c56ce9a8", include_in_antabif=True,
                                        dataset=dataset)
        GBIFOccurrence.objects.create(gbifID='foo', dataset=dataset)
        self.assertTrue(HarvestedDataset.objects.get(key="3d1231e8-2554-45e6-b354-e590c56ce9a8").include_in_antabif)
        # flag HarvestedDataset instance with include_in_antabif=False
        HarvestedDataset.objects.filter(key="3d1231e8-2554-45e6-b354-e590c56ce9a8").update(include_in_antabif=False)
        self.assertFalse(HarvestedDataset.objects.get(key="3d1231e8-2554-45e6-b354-e590c56ce9a8").include_in_antabif)
        harvested_dataset = HarvestedDataset.objects.get(key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
        harvested_dataset.delete_related_objects()
        # ensure that foreign key is set null when Dataset is deleted
        self.assertTrue(HarvestedDataset.objects.filter(key="3d1231e8-2554-45e6-b354-e590c56ce9a8",
                                                        dataset__isnull=True).exists())
        # ensure Dataset instance is deleted
        self.assertFalse(Dataset.objects.filter(dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8").exists())
        # ensure GBIFOccurrence instance associated with the Dataset is also deleted
        self.assertFalse(GBIFOccurrence.objects.filter(dataset__dataset_key="3d1231e8-2554-45e6-b354-e590c56ce9a8")
                         .exists())

    def test_get_eml_of_metadata_only_datasets_with_malformed_uuid(self):
        """
        Ensure ValueError if dataset_key provided is a malformed hexadecimal UUID string
        """
        with self.assertRaises(ValueError):
            get_eml_of_metadata_only_datasets(dataset_key='dataset_key')

    def test_get_eml_of_metadata_only_datasets_with_nonexistant_uuid(self):
        """
        Ensure that function returns empty dict when dataset is a UUID which does not exist in GBIF
        """
        empty_dict = get_eml_of_metadata_only_datasets(dataset_key='11111111-1111-1111-1111-111111111111')
        self.assertFalse(any(empty_dict))

    def test_get_eml_of_metadata_only_datasets_success(self):
        """Ensure that when a correct dataset key is given to function, a dict of
        {dataset uuid: xml Element of EML} is returned by the function
        """
        dataset = get_eml_of_metadata_only_datasets(dataset_key='93d9eebd-2b10-4cdc-a699-21e11723001d')
        self.assertIn('93d9eebd-2b10-4cdc-a699-21e11723001d', dataset.keys())

    def test_import_metadata_only_datasets_with_malformed_dataset_uuid(self):
        """
        Ensure dataset will not be created when HarvestedDataset with a malformed key passed as argument
        """
        qs = HarvestedDataset.objects.filter(key='fake-dataset-key')
        import_metadata_only_datasets(qs)
        self.assertFalse(Dataset.objects.filter(dataset_key='fake-dataset-key').exists())

    def test_import_metadata_only_datasets_with_wrong_model_queryset(self):
        """
        Ensure AttributeError is raised when Dataset Queryset passed to import_metadata_only_datasets
        """
        qs = Dataset.objects.filter(dataset_key='4fa7b334-ce0d-4e88-aaae-2e0c138d049ev')
        with self.assertRaises(WrongModelException):
            import_metadata_only_datasets(qs)

    def test_import_metadata_only_datasets_success(self):
        """
        Ensure Dataset instance is created if a HarvestedDataset queryset with proper uuid which exists in GBIF
        passed to import_metadata_only_datasets
        """
        qs = HarvestedDataset.objects.filter(key='93d9eebd-2b10-4cdc-a699-21e11723001d')
        import_metadata_only_datasets(qs)
        self.assertTrue(Dataset.objects.filter(dataset_key='93d9eebd-2b10-4cdc-a699-21e11723001d').exists())
        self.assertEqual(HarvestedDataset.objects.get(key='93d9eebd-2b10-4cdc-a699-21e11723001d').dataset,
                         Dataset.objects.get(dataset_key='93d9eebd-2b10-4cdc-a699-21e11723001d'))

    def test_import_metadata_only_datasets_success_without_data_type(self):
        """
        Ensure if HarvestedDataset does not specified a type, the Dataset will still be imported
        """
        key = '93d9eebd-2b10-4cdc-a699-21e11723001d'
        qs = HarvestedDataset.objects.filter(key=key)
        import_metadata_only_datasets(qs)
        self.assertTrue(Dataset.objects.filter(dataset_key=key).exists())
        self.assertEqual(HarvestedDataset.objects.get(key=key).dataset, Dataset.objects.get(dataset_key=key))

    def test_update_dataset_with_gbif_api(self):
        """Ensure that Publisher and DataType are assigned to the dataset"""
        Dataset.objects.create(dataset_key='f7c30fac-cf80-471f-8343-4ec5d8594661')
        update_dataset_with_gbif_api(Dataset.objects.filter(dataset_key='f7c30fac-cf80-471f-8343-4ec5d8594661'))
        dataset = Dataset.objects.get(dataset_key='f7c30fac-cf80-471f-8343-4ec5d8594661')
        self.assertEqual(dataset.publisher.publisher_name, 'SCAR - AntOBIS')
        self.assertEqual(dataset.data_type.data_type, 'Occurrence')


class ImportFunctionTest(SimpleTestCase):
    """
    Tests functions in data_manager.management.commands.import_dataset which do not require access to database.
    """

    def setUp(self):
        self.dwca = DwCAReader('data_manager/tests/test_data/0072629-200221144449610.zip')
        self.row = self.dwca.get_corerow_by_position(0)
        return self

    def tearDown(self):
        self.dwca.close()

    def test_get_extension_data_from_core_row(self):
        """
        Ensure that the extension row of core row is returned
        """
        verbatim_row = get_extension_data_from_core_row(self.row,
                                                        extension_uri='http://rs.tdwg.org/dwc/terms/Occurrence')
        verbatim_row_0 = {'http://rs.gbif.org/terms/1.0/gbifID': '1316184895', 'http://purl.org/dc/terms/abstract': '',
                          'http://purl.org/dc/terms/accessRights': 'http://www.inbo.be/en/norms-for-data-use',
                          'http://purl.org/dc/terms/accrualMethod': '',
                          'http://purl.org/dc/terms/accrualPeriodicity': '',
                          'http://purl.org/dc/terms/accrualPolicy': '', 'http://purl.org/dc/terms/alternative': '',
                          'http://purl.org/dc/terms/audience': '', 'http://purl.org/dc/terms/available': '',
                          'http://purl.org/dc/terms/bibliographicCitation': '',
                          'http://purl.org/dc/terms/conformsTo': '', 'http://purl.org/dc/terms/contributor': '',
                          'http://purl.org/dc/terms/coverage': '', 'http://purl.org/dc/terms/created': '',
                          'http://purl.org/dc/terms/creator': '', 'http://purl.org/dc/terms/date': '',
                          'http://purl.org/dc/terms/dateAccepted': '', 'http://purl.org/dc/terms/dateCopyrighted': '',
                          'http://purl.org/dc/terms/dateSubmitted': '', 'http://purl.org/dc/terms/description': '',
                          'http://purl.org/dc/terms/educationLevel': '', 'http://purl.org/dc/terms/extent': '',
                          'http://purl.org/dc/terms/format': '', 'http://purl.org/dc/terms/hasFormat': '',
                          'http://purl.org/dc/terms/hasPart': '', 'http://purl.org/dc/terms/hasVersion': '',
                          'http://purl.org/dc/terms/identifier': 'INBO:INBOVEG:0IV2013102211361614',
                          'http://purl.org/dc/terms/instructionalMethod': '', 'http://purl.org/dc/terms/isFormatOf': '',
                          'http://purl.org/dc/terms/isPartOf': '', 'http://purl.org/dc/terms/isReferencedBy': '',
                          'http://purl.org/dc/terms/isReplacedBy': '', 'http://purl.org/dc/terms/isRequiredBy': '',
                          'http://purl.org/dc/terms/isVersionOf': '', 'http://purl.org/dc/terms/issued': '',
                          'http://purl.org/dc/terms/language': 'en',
                          'http://purl.org/dc/terms/license': 'http://creativecommons.org/publicdomain/zero/1.0/',
                          'http://purl.org/dc/terms/mediator': '', 'http://purl.org/dc/terms/medium': '',
                          'http://purl.org/dc/terms/modified': '', 'http://purl.org/dc/terms/provenance': '',
                          'http://purl.org/dc/terms/publisher': '', 'http://purl.org/dc/terms/references': '',
                          'http://purl.org/dc/terms/relation': '', 'http://purl.org/dc/terms/replaces': '',
                          'http://purl.org/dc/terms/requires': '', 'http://purl.org/dc/terms/rights': '',
                          'http://purl.org/dc/terms/rightsHolder': 'INBO', 'http://purl.org/dc/terms/source': '',
                          'http://purl.org/dc/terms/spatial': '', 'http://purl.org/dc/terms/subject': '',
                          'http://purl.org/dc/terms/tableOfContents': '', 'http://purl.org/dc/terms/temporal': '',
                          'http://purl.org/dc/terms/title': '', 'http://purl.org/dc/terms/type': 'Event',
                          'http://purl.org/dc/terms/valid': '', 'http://rs.tdwg.org/dwc/terms/institutionID': '',
                          'http://rs.tdwg.org/dwc/terms/collectionID': '',
                          'http://rs.tdwg.org/dwc/terms/datasetID': 'http://dataset.inbo.be/inboveg-niche-vlaanderen-events',
                          'http://rs.tdwg.org/dwc/terms/institutionCode': 'INBO',
                          'http://rs.tdwg.org/dwc/terms/collectionCode': '',
                          'http://rs.tdwg.org/dwc/terms/datasetName': 'InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium',
                          'http://rs.tdwg.org/dwc/terms/ownerInstitutionCode': 'INBO',
                          'http://rs.tdwg.org/dwc/terms/basisOfRecord': 'HumanObservation',
                          'http://rs.tdwg.org/dwc/terms/informationWithheld': '',
                          'http://rs.tdwg.org/dwc/terms/dataGeneralizations': '',
                          'http://rs.tdwg.org/dwc/terms/dynamicProperties': '',
                          'http://rs.tdwg.org/dwc/terms/occurrenceID': 'INBO:INBOVEG:OCC:00407292',
                          'http://rs.tdwg.org/dwc/terms/catalogNumber': '',
                          'http://rs.tdwg.org/dwc/terms/recordNumber': '',
                          'http://rs.tdwg.org/dwc/terms/recordedBy': 'Els De Bie',
                          'http://rs.tdwg.org/dwc/terms/individualCount': '',
                          'http://rs.tdwg.org/dwc/terms/organismQuantity': 'p1',
                          'http://rs.tdwg.org/dwc/terms/organismQuantityType': 'londo Scale (1976)',
                          'http://rs.tdwg.org/dwc/terms/sex': '', 'http://rs.tdwg.org/dwc/terms/lifeStage': '',
                          'http://rs.tdwg.org/dwc/terms/reproductiveCondition': '',
                          'http://rs.tdwg.org/dwc/terms/behavior': '',
                          'http://rs.tdwg.org/dwc/terms/establishmentMeans': '',
                          'http://rs.tdwg.org/dwc/terms/occurrenceStatus': 'present',
                          'http://rs.tdwg.org/dwc/terms/preparations': '',
                          'http://rs.tdwg.org/dwc/terms/disposition': '',
                          'http://rs.tdwg.org/dwc/terms/associatedMedia': '',
                          'http://rs.tdwg.org/dwc/terms/associatedReferences': '',
                          'http://rs.tdwg.org/dwc/terms/associatedSequences': '',
                          'http://rs.tdwg.org/dwc/terms/associatedTaxa': '',
                          'http://rs.tdwg.org/dwc/terms/otherCatalogNumbers': '',
                          'http://rs.tdwg.org/dwc/terms/occurrenceRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/organismID': '',
                          'http://rs.tdwg.org/dwc/terms/organismName': '',
                          'http://rs.tdwg.org/dwc/terms/organismScope': '',
                          'http://rs.tdwg.org/dwc/terms/associatedOccurrences': '',
                          'http://rs.tdwg.org/dwc/terms/associatedOrganisms': '',
                          'http://rs.tdwg.org/dwc/terms/previousIdentifications': '',
                          'http://rs.tdwg.org/dwc/terms/organismRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/materialSampleID': '',
                          'http://rs.tdwg.org/dwc/terms/eventID': 'INBO:INBOVEG:0IV2013102211361614',
                          'http://rs.tdwg.org/dwc/terms/parentEventID': '',
                          'http://rs.tdwg.org/dwc/terms/fieldNumber': '',
                          'http://rs.tdwg.org/dwc/terms/eventDate': '2004-07-02',
                          'http://rs.tdwg.org/dwc/terms/eventTime': '',
                          'http://rs.tdwg.org/dwc/terms/startDayOfYear': '',
                          'http://rs.tdwg.org/dwc/terms/endDayOfYear': '', 'http://rs.tdwg.org/dwc/terms/year': '',
                          'http://rs.tdwg.org/dwc/terms/month': '', 'http://rs.tdwg.org/dwc/terms/day': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimEventDate': '2004-07-02/2004-07-02',
                          'http://rs.tdwg.org/dwc/terms/habitat': '',
                          'http://rs.tdwg.org/dwc/terms/samplingProtocol': 'vegetation plot with Londo scale (1976): mosses identified',
                          'http://rs.tdwg.org/dwc/terms/samplingEffort': '',
                          'http://rs.tdwg.org/dwc/terms/sampleSizeValue': '9',
                          'http://rs.tdwg.org/dwc/terms/sampleSizeUnit': 'm²',
                          'http://rs.tdwg.org/dwc/terms/fieldNotes': '',
                          'http://rs.tdwg.org/dwc/terms/eventRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/locationID': 'SNOP027X',
                          'http://rs.tdwg.org/dwc/terms/higherGeographyID': '',
                          'http://rs.tdwg.org/dwc/terms/higherGeography': '',
                          'http://rs.tdwg.org/dwc/terms/continent': 'Europe',
                          'http://rs.tdwg.org/dwc/terms/waterBody': '', 'http://rs.tdwg.org/dwc/terms/islandGroup': '',
                          'http://rs.tdwg.org/dwc/terms/island': '', 'http://rs.tdwg.org/dwc/terms/country': '',
                          'http://rs.tdwg.org/dwc/terms/countryCode': 'BE',
                          'http://rs.tdwg.org/dwc/terms/stateProvince': 'Flemish Brabant',
                          'http://rs.tdwg.org/dwc/terms/county': '',
                          'http://rs.tdwg.org/dwc/terms/municipality': 'Boutersem',
                          'http://rs.tdwg.org/dwc/terms/locality': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimLocality': 'Snoekengracht',
                          'http://rs.tdwg.org/dwc/terms/minimumElevationInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/maximumElevationInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimElevation': '',
                          'http://rs.tdwg.org/dwc/terms/minimumDepthInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/maximumDepthInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimDepth': '',
                          'http://rs.tdwg.org/dwc/terms/minimumDistanceAboveSurfaceInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/maximumDistanceAboveSurfaceInMeters': '',
                          'http://rs.tdwg.org/dwc/terms/locationAccordingTo': 'MILKLIM-areas',
                          'http://rs.tdwg.org/dwc/terms/locationRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/decimalLatitude': '50.83567',
                          'http://rs.tdwg.org/dwc/terms/decimalLongitude': '4.84022',
                          'http://rs.tdwg.org/dwc/terms/geodeticDatum': 'WGS84',
                          'http://rs.tdwg.org/dwc/terms/coordinateUncertaintyInMeters': '30',
                          'http://rs.tdwg.org/dwc/terms/coordinatePrecision': '',
                          'http://rs.tdwg.org/dwc/terms/pointRadiusSpatialFit': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimCoordinates': '',
                          'http://rs.tdwg.org/dwc/terms/verbatimLatitude': '169517.480',
                          'http://rs.tdwg.org/dwc/terms/verbatimLongitude': '183301.580',
                          'http://rs.tdwg.org/dwc/terms/verbatimCoordinateSystem': 'Belgian Lambert 72',
                          'http://rs.tdwg.org/dwc/terms/verbatimSRS': 'Belgium Datum 1972',
                          'http://rs.tdwg.org/dwc/terms/footprintWKT': '',
                          'http://rs.tdwg.org/dwc/terms/footprintSRS': '',
                          'http://rs.tdwg.org/dwc/terms/footprintSpatialFit': '',
                          'http://rs.tdwg.org/dwc/terms/georeferencedBy': '',
                          'http://rs.tdwg.org/dwc/terms/georeferencedDate': '',
                          'http://rs.tdwg.org/dwc/terms/georeferenceProtocol': '',
                          'http://rs.tdwg.org/dwc/terms/georeferenceSources': '',
                          'http://rs.tdwg.org/dwc/terms/georeferenceVerificationStatus': '',
                          'http://rs.tdwg.org/dwc/terms/georeferenceRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/geologicalContextID': '',
                          'http://rs.tdwg.org/dwc/terms/earliestEonOrLowestEonothem': '',
                          'http://rs.tdwg.org/dwc/terms/latestEonOrHighestEonothem': '',
                          'http://rs.tdwg.org/dwc/terms/earliestEraOrLowestErathem': '',
                          'http://rs.tdwg.org/dwc/terms/latestEraOrHighestErathem': '',
                          'http://rs.tdwg.org/dwc/terms/earliestPeriodOrLowestSystem': '',
                          'http://rs.tdwg.org/dwc/terms/latestPeriodOrHighestSystem': '',
                          'http://rs.tdwg.org/dwc/terms/earliestEpochOrLowestSeries': '',
                          'http://rs.tdwg.org/dwc/terms/latestEpochOrHighestSeries': '',
                          'http://rs.tdwg.org/dwc/terms/earliestAgeOrLowestStage': '',
                          'http://rs.tdwg.org/dwc/terms/latestAgeOrHighestStage': '',
                          'http://rs.tdwg.org/dwc/terms/lowestBiostratigraphicZone': '',
                          'http://rs.tdwg.org/dwc/terms/highestBiostratigraphicZone': '',
                          'http://rs.tdwg.org/dwc/terms/lithostratigraphicTerms': '',
                          'http://rs.tdwg.org/dwc/terms/group': '', 'http://rs.tdwg.org/dwc/terms/formation': '',
                          'http://rs.tdwg.org/dwc/terms/member': '', 'http://rs.tdwg.org/dwc/terms/bed': '',
                          'http://rs.tdwg.org/dwc/terms/identificationID': '',
                          'http://rs.tdwg.org/dwc/terms/identificationQualifier': '',
                          'http://rs.tdwg.org/dwc/terms/typeStatus': '',
                          'http://rs.tdwg.org/dwc/terms/identifiedBy': 'Els De Bie',
                          'http://rs.tdwg.org/dwc/terms/dateIdentified': '',
                          'http://rs.tdwg.org/dwc/terms/identificationReferences': '',
                          'http://rs.tdwg.org/dwc/terms/identificationVerificationStatus': '',
                          'http://rs.tdwg.org/dwc/terms/identificationRemarks': '',
                          'http://rs.tdwg.org/dwc/terms/taxonID': 'INBSYS0000010112',
                          'http://rs.tdwg.org/dwc/terms/scientificNameID': '',
                          'http://rs.tdwg.org/dwc/terms/acceptedNameUsageID': '',
                          'http://rs.tdwg.org/dwc/terms/parentNameUsageID': '',
                          'http://rs.tdwg.org/dwc/terms/originalNameUsageID': '',
                          'http://rs.tdwg.org/dwc/terms/nameAccordingToID': '',
                          'http://rs.tdwg.org/dwc/terms/namePublishedInID': '',
                          'http://rs.tdwg.org/dwc/terms/taxonConceptID': '',
                          'http://rs.tdwg.org/dwc/terms/scientificName': 'Cerastium fontanum Baumg. subsp. vulgare',
                          'http://rs.tdwg.org/dwc/terms/acceptedNameUsage': '',
                          'http://rs.tdwg.org/dwc/terms/parentNameUsage': '',
                          'http://rs.tdwg.org/dwc/terms/originalNameUsage': '',
                          'http://rs.tdwg.org/dwc/terms/nameAccordingTo': '',
                          'http://rs.tdwg.org/dwc/terms/namePublishedIn': '',
                          'http://rs.tdwg.org/dwc/terms/namePublishedInYear': '',
                          'http://rs.tdwg.org/dwc/terms/higherClassification': '',
                          'http://rs.tdwg.org/dwc/terms/kingdom': 'Plantae', 'http://rs.tdwg.org/dwc/terms/phylum': '',
                          'http://rs.tdwg.org/dwc/terms/class': '', 'http://rs.tdwg.org/dwc/terms/order': '',
                          'http://rs.tdwg.org/dwc/terms/family': '', 'http://rs.tdwg.org/dwc/terms/genus': '',
                          'http://rs.tdwg.org/dwc/terms/subgenus': '',
                          'http://rs.tdwg.org/dwc/terms/specificEpithet': '',
                          'http://rs.tdwg.org/dwc/terms/infraspecificEpithet': '',
                          'http://rs.tdwg.org/dwc/terms/taxonRank': 'subspecies',
                          'http://rs.tdwg.org/dwc/terms/verbatimTaxonRank': '',
                          'http://rs.tdwg.org/dwc/terms/scientificNameAuthorship': '(Hartm.) Greuter et Burdet',
                          'http://rs.tdwg.org/dwc/terms/vernacularName': '',
                          'http://rs.tdwg.org/dwc/terms/nomenclaturalCode': '',
                          'http://rs.tdwg.org/dwc/terms/taxonomicStatus': '',
                          'http://rs.tdwg.org/dwc/terms/nomenclaturalStatus': '',
                          'http://rs.tdwg.org/dwc/terms/taxonRemarks': '',
                          'http://rs.gbif.org/terms/1.0/recordedByID': '',
                          'http://rs.gbif.org/terms/1.0/identifiedByID': ''}
        self.assertEqual(verbatim_row, verbatim_row_0)

    def test_get_extension_data_from_core_row_extension_absent(self):
        """
        Ensure that the extension row is None if the type of extension does not exists
        """
        verbatim_row = get_extension_data_from_core_row(self.row,
                                                        extension_uri='http://rs.tdwg.org/dwc/terms/SamplingEvent')
        self.assertIsNone(verbatim_row)

    def test_get_core_gbifID_with_verbatim(self):
        """
        Ensure that the gbifID of a core row which has a verbatim record is returned correctly
        """
        gbif_ids = get_core_gbifID_with_verbatim(self.row, gbif_ids=set())
        self.assertEqual(gbif_ids, {'1316184895'})
