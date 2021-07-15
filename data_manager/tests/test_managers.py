# -*- coding: utf-8 -*-
from dwca.read import DwCAReader

from data_manager.management.commands.import_datasets import import_eml, get_extension_data_from_core_row
from data_manager.models import DataType, Dataset, HarvestedDataset, GBIFOccurrence, Publisher, Project, Keyword, \
    HexGrid, BasisOfRecord, GBIFVerbatimOccurrence
from dateutil import parser
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.conf import settings
from django.test import TestCase, override_settings
from pygbif import occurrences
import datetime
import os
import defusedxml.ElementTree as ET

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class DataTypeManagerTestCase(TestCase):

    def test_create_from_gbif_api(self):
        """Ensure DataType instance created as expected"""
        # Sampling event dataset
        uuid = '83cbb4fa-f762-11e1-a439-00145eb45e9a'
        data_type = DataType.objects.create_from_gbif_api(uuid)
        # ensure that data_type attribute is converted to title case (case sensitive)
        self.assertFalse(DataType.objects.filter(data_type='SAMPLING_EVENT').exists())  # as returned from GBIF API
        self.assertFalse(DataType.objects.filter(data_type='Sampling event').exists())  # capitalize is not title case
        self.assertEqual(data_type.data_type, 'Sampling Event')  # attribute in title case
        self.assertTrue(DataType.objects.filter(data_type='Sampling Event').exists())  # instance created in title case
        # Occurrence dataset
        uuid = 'f7c30fac-cf80-471f-8343-4ec5d8594661'
        data_type = DataType.objects.create_from_gbif_api(uuid)
        self.assertEqual(data_type.data_type, 'Occurrence')

    def test_duplicate_instances(self):
        """Ensure creating two identical DataType instances will not duplicate the instance"""
        DataType.objects.create(data_type='Sampling Event')
        # ensure that objects is already created
        self.assertTrue(DataType.objects.filter(data_type='Sampling Event').exists())
        uuid = '83cbb4fa-f762-11e1-a439-00145eb45e9a'
        # create the same instance again - should not lead to duplication
        data_type = DataType.objects.create_from_gbif_api(uuid)
        self.assertEqual(data_type.data_type, 'Sampling Event')
        self.assertEqual(DataType.objects.filter(data_type='Sampling Event').count(), 1)

    def test_case_sensitive(self):
        """Ensure that instances created are case sensitive"""
        DataType.objects.create(data_type='SAMPLING EVENT')
        DataType.objects.create_from_gbif_api('83cbb4fa-f762-11e1-a439-00145eb45e9a')
        self.assertEqual(DataType.objects.filter(data_type__iexact='sampling EVENT').count(), 2)


# =================
# KEYWORD MANAGER
# =================
test_keyword_xml = """
    <eml>
        <dataset>
            <keywordSet>
                <keyword>keyword</keyword>
                <keywordThesaurus>thesaurus</keywordThesaurus>
            </keywordSet>
        </dataset>
    </eml>
    """

keyword_is_none = """
    <eml>
        <dataset>
            <keywordSet>
                <keyword></keyword>
                <keywordThesaurus>thesaurus</keywordThesaurus>
            </keywordSet>
        </dataset>
    </eml>
    """

keyword_no_thesaurus = """
    <eml>
        <dataset>
            <keywordSet>
                <keyword>keyword</keyword>
            </keywordSet>
        </dataset>
    </eml>
    """

keyword_no_keyword = """
    <eml>
        <dataset>
            <keywordSet>
                <keywordThesaurus>thesaurus</keywordThesaurus>
            </keywordSet>
        </dataset>
    </eml>
    """


class KeywordTestCase(TestCase):
    """
    Tests for KeywordManager class.
    """

    def setUp(self):
        Keyword.objects.create(keyword='keyword_created', thesaurus='thesaurus_created')

    def test_create_distinct_keyword_from_different_thesaurus(self):
        """
        Ensure that keyword manager will create keywords and thesaurus distinct
        from the ones exist in database.

        Example:
        Database contains   { keyword: "keyword_created",       thesaurus: "thesaurus_created" }
        EML contains        { keyword: "keyword",               thesaurus: "thesaurus" }

        :return:
        """
        # create elementTree from xml string
        tree = ET.fromstring(test_keyword_xml)
        # create dataset object for keyword-dataset many-to-many relationship
        dataset = Dataset.objects.create(dataset_key='dataset-key')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        # test if new keyword object was created
        self.assertEqual(Keyword.objects.all().count(), 2)

    def test_create_same_keyword_from_different_thesaurus(self):
        """
        Ensure that keyword manager will create keyword from a distinct thesaurus if the
        same keyword from another thesaurus already exist in database.

        Example:
        Database contains   { keyword: "keyword",       thesaurus: "thesaurus one"},
        EML contains        { keyword: "keyword",       thesaurus: "thesaurus" }

        "keyword" exists in database but is from "thesaurus".
        Thus, KeywordManager should create a new entry for "keyword" from "thesaurus one".

        :return:
        """
        Keyword.objects.create(keyword="keyword", thesaurus="thesaurus one")
        tree = ET.fromstring(test_keyword_xml)
        dataset = Dataset.objects.create(dataset_key='dataset-key')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        self.assertEqual(Keyword.objects.all().count(), 3)

    def test_create_same_keyword_from_same_thesaurus(self):
        """
        Ensure that keyword manager will NOT create the same keyword from the same thesaurus
        if the pair already exists in database

        Example:
        Database already have       {keyword: "keyword",        thesaurus: "thesaurus"}
        When importing dataset with {keyword: "keyword",        thesaurus: "thesaurus"},
        these keywords will not be created again.

        :return:
        """
        Keyword.objects.create(keyword="keyword", thesaurus="thesaurus")
        tree = ET.fromstring(test_keyword_xml)
        dataset = Dataset.objects.create(dataset_key='dataset-key')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        self.assertEqual(Keyword.objects.all().count(), 2)

    def test_create_keyword_without_thesaurus_tag(self):
        """Ensure that keyword without thesaurus in eml will be created"""
        tree = ET.fromstring(keyword_no_thesaurus)
        dataset = Dataset.objects.create(dataset_key='dataset-no-thesaurus')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        self.assertQuerysetEqual(Keyword.objects.filter(dataset__dataset_key='dataset-no-thesaurus'),
                                 ['<Keyword: keyword>'])

    def test_dont_create_keyword_without_keyword_tag(self):
        """Ensure that <keywordSet> without <keyword> will not create Keyword"""
        tree = ET.fromstring(keyword_no_keyword)
        dataset = Dataset.objects.create(dataset_key='dataset-no-keyword')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        self.assertFalse(Keyword.objects.filter(dataset__dataset_key='dataset-no-keyword').exists())

    def test_dont_create_keyword_without_keyword(self):
        """Ensure that <keywordSet> with <keyword> tag but no 'keyword' will not create Keyword"""
        tree = ET.fromstring(keyword_no_keyword)
        dataset = Dataset.objects.create(dataset_key='dataset-keyword-is-none')
        Keyword.objects.from_gbif_dwca_eml(tree, dataset)
        self.assertFalse(Keyword.objects.filter(dataset__dataset_key='dataset-keyword-is-none').exists())


# ==================
# PUBLISHER MANAGER
# ==================
nonexistent_dataset_key = 'non-existent-dataset-key'


class PublisherTestCase(TestCase):
    """
    Tests for Publisher Manager class
    """

    def setUp(self):
        """
        Setting up test database.
        :return:
        """
        Publisher.objects.create(publisher_key='e2e717bf-551a-4917-bdc9-4fa0f342c530')

    def test_create_publisher_with_nonexistent_dataset_key(self):
        """
        Ensure that publisher object will not be created if dataset_key does not
        exists in GBIF.
        :return:
        """
        # ensure that publisher object was created from setup.
        self.assertEqual(Publisher.objects.all().count(), 1)
        # create publisher object with non-existent dataset key
        Publisher.objects.from_gbif_api(gbif_dataset_key=nonexistent_dataset_key)
        # ensure that publisher object is not created
        self.assertEqual(Publisher.objects.all().count(), 1)

    def test_create_publisher_with_empty_dataset_key(self):
        """
        Ensure that publisher object will not be created if dataset_key is empty
        :return:
        """
        self.assertEqual(len(Publisher.objects.all()), 1)
        Publisher.objects.from_gbif_api(gbif_dataset_key='')
        self.assertEqual(len(Publisher.objects.all()), 1)


# ==================
# PROJECT MANAGER
# ==================
project_xml = """
<eml>
    <dataset>
        <project>
            <title>Project title</title>
            <funding><para>Project funding</para></funding>
        </project>
    </dataset>
</eml>
"""

project_diff_funding_xml = """
<eml>
    <dataset>
        <project>
            <title>created project</title>
            <funding><para>Project funding is different</para></funding>
        </project>
    </dataset>
</eml>
"""

project_without_title_xml = """
<eml>
    <dataset>
        <project>
            <funding><para>Project funding</para></funding>
        </project>
    </dataset>
</eml>
"""

project_without_funding_tag_xml = """
<eml>
    <dataset>
        <project>
            <title>Project without funding tag</title>
        </project>
    </dataset>
</eml>
"""

project_without_funding_text_xml = """
<eml>
    <dataset>
        <project>
            <title>Project without funding text</title>
            <funding></funding>
        </project>
    </dataset>
</eml>
"""

dataset_without_project = """
<eml>
    <dataset>
        <title>Dataset title</title>
    </dataset>
</eml>
"""


class ProjectTestCase(TestCase):
    def setUp(self):
        Project.objects.create(title='created project', funding='created funding')

    def test_create_project_from_elementtree(self):
        """
        Ensure that project can be created
        :return:
        """
        self.assertEqual(Project.objects.all().count(), 1)
        tree = ET.fromstring(project_xml)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertEqual(Project.objects.all().count(), 2)

    def test_create_project_without_title(self):
        """
        Ensure that project without title will NOT be created
        :return:
        """
        tree = ET.fromstring(project_without_title_xml)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertEqual(Project.objects.all().count(), 1)

    def test_create_project_same_title_diff_funding(self):
        """
        Ensure that if project title exists, new entry with same title but different funding
        will update the current project funding.
        :return:
        """
        tree = ET.fromstring(project_diff_funding_xml)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertEqual(Project.objects.all().count(), 1)
        get_funding = Project.objects.get(title='created project')
        self.assertEqual(get_funding.funding, 'Project funding is different')

    def test_create_project_without_funding_tag(self):
        """Ensure that Project instance without funding tag can be created."""
        tree = ET.fromstring(project_without_funding_tag_xml)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertTrue(Project.objects.filter(title="Project without funding tag").exists())

    def test_create_project_without_funding_text(self):
        """Ensure that Project instance without funding text can be created."""
        tree = ET.fromstring(project_without_funding_text_xml)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertTrue(Project.objects.filter(title="Project without funding text").exists())

    def test_not_create_project(self):
        """Dataset without project tag will not create Project instance"""
        tree = ET.fromstring(dataset_without_project)
        Project.objects.from_gbif_dwca_eml(tree)
        self.assertFalse(Project.objects.filter(title="").exists())


# ==================
# DATASET MANAGER
# ==================
eml_xml = """<?xml version="1.0" encoding="utf-8"?>
<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd"
        packageId="7b4ac816-f762-11e1-a439-00145eb45e9a"  system="http://gbif.org" scope="system"
  xml:lang="en">

<dataset>
    <alternateIdentifier>doi:12345</alternateIdentifier>
    <alternateIdentifier>8210</alternateIdentifier>
    <title>Dataset title</title>
    <associatedParty>
        <electronicMailAddress>myname (at) domain.country</electronicMailAddress>
        <role>TECHNICAL_POINT_OF_CONTACT</role>
    </associatedParty>
    <pubDate>2017-07-31</pubDate>
    <language>en</language>
    <abstract>
        <para>Fixture's dataset abstract. Sometimes this will contains àćçéñt, sometimes won't.</para>
    </abstract>
    <citation>Dataset title. Occurrence Dataset https://doi.org/12345 accessed on 2017-07-31.</citation>
    <coverage>
        <geographicCoverage>
            <geographicDescription>Southern Ocean and sub-Antarctic region</geographicDescription>
            <boundingCoordinates>
                <westBoundingCoordinate>-180</westBoundingCoordinate>
                <eastBoundingCoordinate>180</eastBoundingCoordinate>
                <northBoundingCoordinate>-40</northBoundingCoordinate>
                <southBoundingCoordinate>-78</southBoundingCoordinate>
            </boundingCoordinates>
        </geographicCoverage>
    </coverage>
    <intellectualRights>
        <para>This work is licensed under a
            <ulink url="http://creativecommons.org/licenses/by/4.0/legalcode">
                <citetitle>Creative Commons Attribution (CC-BY) 4.0 License</citetitle>
            </ulink>.
        </para>
    </intellectualRights>
    <distribution scope="document">
        <online>
            <url function="information">http://data.aad.gov.au/aadc/biodiversity/display_collection.cfm?collection_id=130</url>
        </online>
    </distribution>
</dataset>

<additionalMetadata>
    <metadata>
      <gbif>
        <dateStamp>2017-03-31T08:11:13Z</dateStamp>
      <citation>See Metadata record http://data.aad.gov.au/aadc/metadata/metadata_redirect.cfm?md=AMD/AU/ANARE_whale_logs Contact Dave Watts for details on citation details.</citation>
        </gbif>
    </metadata>
</additionalMetadata>

</eml:eml>
"""

defused_eml = """<ns0:eml xmlns:ns0="eml://ecoinformatics.org/eml-2.1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd" packageId="7b4ac816-f762-11e1-a439-00145eb45e9a" system="http://gbif.org" scope="system" xml:lang="en">

<dataset>
    <alternateIdentifier>doi:12345</alternateIdentifier>
    <alternateIdentifier>8210</alternateIdentifier>
    <title>Dataset title</title>
    <associatedParty>
        <electronicMailAddress>myname (at) domain.country</electronicMailAddress>
        <role>TECHNICAL_POINT_OF_CONTACT</role>
    </associatedParty>
    <pubDate>2017-07-31</pubDate>
    <language>en</language>
    <abstract>
        <para>Fixture\'s dataset abstract. Sometimes this will contains àćçéñt, sometimes won\'t.</para>
    </abstract>
    <citation>Dataset title. Occurrence Dataset https://doi.org/12345 accessed on 2017-07-31.</citation>
    <coverage>
        <geographicCoverage>
            <geographicDescription>Southern Ocean and sub-Antarctic region</geographicDescription>
            <boundingCoordinates>
                <westBoundingCoordinate>-180</westBoundingCoordinate>
                <eastBoundingCoordinate>180</eastBoundingCoordinate>
                <northBoundingCoordinate>-40</northBoundingCoordinate>
                <southBoundingCoordinate>-78</southBoundingCoordinate>
            </boundingCoordinates>
        </geographicCoverage>
    </coverage>
    <intellectualRights>
        <para>This work is licensed under a
            <ulink url="http://creativecommons.org/licenses/by/4.0/legalcode">
                <citetitle>Creative Commons Attribution (CC-BY) 4.0 License</citetitle>
            </ulink>.
        </para>
    </intellectualRights>
    <distribution scope="document">
        <online>
            <url function="information">http://data.aad.gov.au/aadc/biodiversity/display_collection.cfm?collection_id=130</url>
        </online>
    </distribution>
</dataset>

<additionalMetadata>
    <metadata>
      <gbif>
        <dateStamp>2017-03-31T08:11:13Z</dateStamp>
      <citation>See Metadata record http://data.aad.gov.au/aadc/metadata/metadata_redirect.cfm?md=AMD/AU/ANARE_whale_logs Contact Dave Watts for details on citation details.</citation>
        </gbif>
    </metadata>
</additionalMetadata>

</ns0:eml>"""


class DatasetTestCase(TestCase):
    maxDiff = None

    def setUp(self):
        DataType.objects.create(data_type="Occurrence")
        Project.objects.create(title="Project title", funding="Project funding")

    def test_dataset_created_as_expected(self):
        """Ensure that dataset object is created"""
        project = Project.objects.get(title="Project title")
        tree = ET.fromstring(eml_xml)

        # ensure Dataset object is created
        Dataset.objects.from_gbif_dwca_eml(eml_tree=tree, project_object=project,
                                           dataset_uuid="7b4ac816-f762-11e1-a439-00145eb45e9a")
        self.assertEqual(Dataset.objects.all().count(), 1)

        # ensure that dataset_key is created correctly
        self.assertQuerysetEqual(Dataset.objects.filter(title="Dataset title").values('dataset_key'),
                                 ["{'dataset_key': '7b4ac816-f762-11e1-a439-00145eb45e9a'}"])

        # ensure that full_record_count is added correctly in the dataset
        self.assertQuerysetEqual(Dataset.objects.filter(title="Dataset title").values('full_record_count'),
                                 ["{'full_record_count': None}"])

        # ensure Dataset project is linked as expected
        project_title = Dataset.objects.filter(title="Dataset title").values("project__title")
        self.assertQuerysetEqual(project_title, ["{'project__title': 'Project title'}"])

        project_funding = Dataset.objects.filter(title="Dataset title").values("project__funding")
        self.assertQuerysetEqual(project_funding, ["{'project__funding': 'Project funding'}"])

        # ensure Dataset data type is linked as expected
        data_type_queried = Dataset.objects.get(title="Dataset title").data_type
        self.assertIsNone(data_type_queried)

        # ensure dataset title is created as expected
        dataset_title = Dataset.objects.filter(title="Dataset title").values("title")
        self.assertQuerysetEqual(dataset_title, ["{'title': 'Dataset title'}"])

        # ensure alternate id are created as expected
        alternate_identifiers = Dataset.objects.filter(title="Dataset title").values("alternate_identifiers")
        self.assertQuerysetEqual(alternate_identifiers, ["{'alternate_identifiers': ['doi:12345', '8210']}"])

        # ensure doi is created as expected
        doi = Dataset.objects.filter(title="Dataset title").values("doi")
        self.assertQuerysetEqual(doi, ["{'doi': 'doi:12345'}"])

        # ensure bounding box is created as expected
        bbox = Dataset.objects.annotate(json=AsGeoJSON('bounding_box')).get(title="Dataset title").json
        self.assertEqual(bbox, '{"type":"Polygon",'
                               '"coordinates":[[[-180,-78],[-180,-40],[180,-40],[180,-78],[-180,-78]]]}')

        # ensure pubDate is created as expected
        pub_date = Dataset.objects.filter(title="Dataset title").values("pub_date")
        self.assertQuerysetEqual(pub_date, ["{'pub_date': datetime.date(2017, 7, 31)}"])

        # ensure intellectual_right is created as expected
        intellectual_right = Dataset.objects.filter(title="Dataset title").values("intellectual_right")
        self.assertQuerysetEqual(intellectual_right,
                                 ["{'intellectual_right': 'Creative Commons Attribution (CC-BY) 4.0 License'}"])

        # ensure abstract is created as expected
        abstract = Dataset.objects.filter(title="Dataset title").values("abstract")
        self.assertQuerysetEqual(abstract, [str({'abstract': "Fixture's dataset abstract. "
                                                             "Sometimes this will contains àćçéñt, sometimes won't."})])

        # ensure that citation is created as expected
        citation = Dataset.objects.filter(title="Dataset title").values("citation")
        self.assertQuerysetEqual(citation, [
            str({'citation': "Dataset title. Occurrence Dataset https://doi.org/12345 accessed on 2017-07-31."})])

        # ensure that eml_text is created as expected
        dataset = Dataset.objects.get(title="Dataset title")
        self.assertEqual(dataset.eml_text, defused_eml)


class DatasetModelMethodTestCase(TestCase):
    """Test Model Methods for Dataset"""

    def setUp(self):
        # create instance of HarvestedDataset and Dataset which has dataset key that is deleted from GBIF
        dataset = Dataset.objects.create(dataset_key='2d2658b4-cde2-4724-bdf5-86f71c64e9ca',
                                         download_on=datetime.datetime.now())
        HarvestedDataset.objects.create(key='2d2658b4-cde2-4724-bdf5-86f71c64e9ca', dataset=dataset)
        # dataset that is not deleted
        Dataset.objects.create(dataset_key='f7c30fac-cf80-471f-8343-4ec5d8594661',
                               download_on=datetime.datetime(1010, 10, 10))  # ancient year

    def test_check_for_deleted_gbif_key(self):
        """Ensure Dataset deleted on GBIF will be flagged deleted, ensure that 'deleted' is not considered as
        'has_new_version'"""
        dataset = Dataset.objects.get(dataset_key='2d2658b4-cde2-4724-bdf5-86f71c64e9ca')
        dataset.deleted_on_gbif()
        # ensure that Dataset is flagged deleted
        self.assertTrue(Dataset.objects.filter(dataset_key='2d2658b4-cde2-4724-bdf5-86f71c64e9ca').exists())
        # ensure that HarvestedDataset of the dataset is also flagged deleted
        harvested_dataset = HarvestedDataset.objects.get(key='2d2658b4-cde2-4724-bdf5-86f71c64e9ca')
        self.assertTrue(harvested_dataset.deleted_from_gbif)
        self.assertFalse(harvested_dataset.include_in_antabif)
        # ensure that deleted != has new version
        self.assertFalse(dataset.has_new_version())

    def test_check_new_version(self):
        """Ensure that Dataset's modified timestamp on GBIF is more recent than the 'download_on' timestamp will return
         True for has_new_version()"""
        dataset = Dataset.objects.get(dataset_key='f7c30fac-cf80-471f-8343-4ec5d8594661')
        # because the Dataset instance was downloaded on 1010-10-10, it has a "new version"
        self.assertTrue(dataset.has_new_version())
        # ensure that .deleted() does not return True
        self.assertFalse(dataset.deleted_on_gbif())


class ForeignKeyTestCase(TestCase):
    """
    Ensure that foreign keys are set in the correct model
    Foreign keys on_delete default is cascade, ensure that cascade deletion is in correct direction
    """

    def test_Dataset_Project_foreign_key_on_delete_cascade(self):
        # ------------------
        # Create objects
        # ------------------
        # create object for foreign key
        Project.objects.create(title="project 1")
        # ensure objects are created
        self.assertEqual(Project.objects.filter(title="project 1").exists(), True)
        # create Dataset object with foreign keys
        project = Project.objects.get(title="project 1")  # foreign key
        Dataset.objects.create(dataset_key="dataset-key-1", title="dataset title 1",
                               project=project)
        # ensure Dataset object is created
        self.assertEqual(Dataset.objects.filter(dataset_key="dataset-key-1").exists(), True)
        # ensure foreign key is correctly established
        self.assertQuerysetEqual(Dataset.objects.filter(project__title="project 1"),
                                 ['<Dataset: dataset title 1>'])

        # -------------------------------------------------------------
        # Deleting Dataset object will not lead to deletion of Project
        # -------------------------------------------------------------
        Dataset.objects.filter(dataset_key="dataset-key-1").delete()
        # ensure dataset object is deleted
        self.assertEqual(Dataset.objects.filter(dataset_key="dataset-key-1").exists(), False)
        # ensure foreign key objects are not deleted
        self.assertEqual(Project.objects.filter(title="project 1").exists(), True)

        # ---------------------------------------------------------
        # Deleting Project object will lead to deletion of Dataset
        # ---------------------------------------------------------
        Dataset.objects.create(dataset_key="dataset-key-2", title="dataset title 2", project=project)
        self.assertEqual(Dataset.objects.filter(dataset_key="dataset-key-2").exists(), True)
        Project.objects.filter(title="project 1").delete()
        self.assertEqual(Project.objects.filter(title="project 1").exists(), False)
        self.assertEqual(Dataset.objects.filter(dataset_key="dataset-key-2").exists(), False)


class DatasetCountOccurrenceTest(TestCase):

    def setUp(self):
        """Create objects for tests"""
        d = Dataset.objects.create(dataset_key="7b4ac816-f762-11e1-a439-00145eb45e9a", title="dataset title")
        for i in range(100):
            GBIFOccurrence.objects.create(gbifID=i, dataset=d)

    def test_assign_default_value_to_count(self):
        """Ensure that default value is assigned to the fields: filtered_record_count, deleted_record_count and
        percentage_records_retained"""
        d = Dataset.objects.get(dataset_key="7b4ac816-f762-11e1-a439-00145eb45e9a", title="dataset title")
        self.assertEqual(d.filtered_record_count, 0)
        self.assertEqual(d.deleted_record_count, 0)
        self.assertEqual(d.percentage_records_retained, 100)

    def test_count_occurrence_per_dataset(self):
        """Ensure that occurrence count is updated according to info from GBIF API"""
        d = Dataset.objects.get(dataset_key="7b4ac816-f762-11e1-a439-00145eb45e9a", title="dataset title")
        d.count_occurrence_per_dataset()
        self.assertEqual(d.filtered_record_count, 100)
        self.assertEqual(d.deleted_record_count, 3868)
        self.assertEqual(d.full_record_count, 3968)
        self.assertEqual(d.percentage_records_retained, 2.520)


class GBIFOccurrenceTestCase(TestCase):
    maxDiff = None
    fixtures = ['occurrence.json']

    def test_to_csv_tuple(self):
        """Ensure occurrence object is transformed into csv tuple"""
        occ = GBIFOccurrence.objects.get(pk=3)
        o = occ.to_csv_tuple()
        self.assertEqual(o, [3, "license", "rightsHolder", "accessRights", "bibliographicCitation 中文", "references",
                             "institutionCode", "collectionCode", "datasetName Tromsø", "dynamicProperties",
                             "recordedBy",
                             "individualCount", "organismQuantity", "organismQuantityType", "sex", "lifeStage",
                             "occurrenceStatus",
                             "reproductiveCondition", "behavior", "occurrenceRemarks", "eventDate", "eventTime",
                             2016, 12, 6, "verbatimEventDate", "samplingProtocol", "sampleSizeValue",
                             "sampleSizeUnit", "samplingEffort", "fieldNotes", "locality", "verbatimLocality", 5.0,
                             "verbatimDepth",
                             "minimumDistanceAboveSurfaceInMeters", "maximumDistanceAboveSurfaceInMeters",
                             "locationAccordingTo", "locationRemarks", -85.0, -75.0, "geodeticDatum",
                             3.0, 1.0, "scientificName", "taxonKey", "kingdom", "phylum", "_class", "order", "family",
                             "genus",
                             "subgenus", "specificEpithet", "infraspecificEpithet", "taxonRank",
                             "scientificNameAuthorship", "basisOfRecord", "datasetKey", 1])

    def test_on_delete_cascade(self):
        """Ensure all GBIFOccurrence instances associated with a dataset will be cascade deleted"""
        self.assertEqual(GBIFOccurrence.objects.all().count(), 3)
        Dataset.objects.filter(dataset_key="my_dataset").delete()
        self.assertEqual(GBIFOccurrence.objects.all().count(), 0)


class CheckNewDatasetVersionExistsTestCase(TestCase):

    def setUp(self):
        Publisher.objects.from_gbif_api(gbif_dataset_key='7b657080-f762-11e1-a439-00145eb45e9a')
        publisher = Publisher.objects.get(publisher_key='104e9c96-791b-4f14-978c-f581cb214912')
        Dataset.objects.create(dataset_key='7b657080-f762-11e1-a439-00145eb45e9a', title='Penguins of Antarctica',
                               eml_text='Penguins of Antarctica', publisher=publisher,
                               download_on=parser.parse('2000-04-25T15:08:55Z'))
        Dataset.objects.create(dataset_key='8910e49e-f762-11e1-a439-00145eb45e9a', title='Antarctic Krill',
                               eml_text='Antarctic Krill', publisher=publisher,
                               download_on=parser.parse('2020-04-25T15:08:55Z'))

    def test_dataset_download_on_created(self):
        """Ensure that dataset.download_on is created in datetime format (naive)"""
        dataset = Dataset.objects.get(dataset_key='7b657080-f762-11e1-a439-00145eb45e9a')
        self.assertEqual(dataset.download_on, datetime.datetime(2000, 4, 25, 15, 8, 55))


class HarvestedDatasetManagerTestCase(TestCase):

    def test_create_instances_from_list_of_dicts(self):
        """
        Ensure manager create HarvestedDataset instance as expected.
        """
        results = [
            {
                "key": "6026ed0c-3113-4d31-9c85-a6468f09f699",
                "title": "Foraging zones of Macaroni Penguins breeding at Heard Island 2000",
                "description": "<p>With a population of about 2 million pairs macaroni penguins",
                "type": "OCCURRENCE",
                "hostingOrganizationKey": "3693ff90-4c16-11d8-b290-b8a03c50a862",
                "hostingOrganizationTitle": "Australian Antarctic Data Centre",
                "countryCoverage": [],
                "publishingCountry": "AU",
                "publishingOrganizationKey": "3693ff90-4c16-11d8-b290-b8a03c50a862",
                "publishingOrganizationTitle": "Australian Antarctic Data Centre",
                "license": "http://creativecommons.org/licenses/by/4.0/legalcode",
                "decades": [
                    2000
                ],
                "keywords": [
                    "Occurrence"
                ]
            },
            {
                "key": "59d46416-34e8-4da6-8d6f-1e3fc7b1b88b",
                "title": "The French National Collection of forage and turf species (grasses and legumes).",
                "description": "Academic scientists from INRA (French national agronomic research institute)",
                "type": "OCCURRENCE",
                "hostingOrganizationKey": "5d5e5d82-076c-4e9a-b5b0-c88d1b691a6a",
                "hostingOrganizationTitle": "GBIF France",
                "countryCoverage": [],
                "publishingCountry": "FR",
                "publishingOrganizationKey": "0b5846f7-20b5-410a-93c5-5de83b522deb",
                "publishingOrganizationTitle": "BRC Forage and turf, INRA Lusignan",
                "license": "http://creativecommons.org/licenses/by/4.0/legalcode",
                "decades": [
                    1960,
                    1970,
                    1980,
                    1990,
                    2000,
                    2010
                ],
                "keywords": [
                    "agriculture",
                    "genetic diversity",
                    "turf",
                    "legume",
                    "natural population",
                    "cultivar",
                    "grass",
                    "Vegetation",
                    "genetic resource",
                    "forage",
                    "landrace"
                ],
                "recordCount": 537
            }
        ]
        # get a random dataset key from the results of response
        HarvestedDataset.objects.create_from_list_of_dicts(results, query_param={'q': 'penguins'})
        harvested_dataset = HarvestedDataset.objects.get(key='6026ed0c-3113-4d31-9c85-a6468f09f699')
        self.assertEqual(harvested_dataset.hostingOrganizationKey, '3693ff90-4c16-11d8-b290-b8a03c50a862')
        self.assertEqual(harvested_dataset.hostingOrganizationTitle, 'Australian Antarctic Data Centre')
        self.assertEqual(harvested_dataset.key, '6026ed0c-3113-4d31-9c85-a6468f09f699')
        self.assertEqual(harvested_dataset.license, 'http://creativecommons.org/licenses/by/4.0/legalcode')
        self.assertEqual(harvested_dataset.publishingCountry, 'AU')
        self.assertEqual(harvested_dataset.publishingOrganizationKey, '3693ff90-4c16-11d8-b290-b8a03c50a862')
        self.assertEqual(harvested_dataset.publishingOrganizationTitle, 'Australian Antarctic Data Centre')
        self.assertEqual(harvested_dataset.recordCount, occurrences.search(
            datasetKey='6026ed0c-3113-4d31-9c85-a6468f09f699').get('count'))
        self.assertEqual(harvested_dataset.title, 'Foraging zones of Macaroni Penguins breeding at Heard Island 2000')
        self.assertEqual(harvested_dataset.type, 'OCCURRENCE')
        self.assertEqual(harvested_dataset.modified, parser.parse('2019-01-24T04:59:44.818+0000', tzinfos=None).date())
        self.assertEqual(harvested_dataset.harvested_on.date(), datetime.date.today())
        self.assertIsNone(harvested_dataset.include_in_antabif)
        self.assertIsNone(harvested_dataset.import_full_dataset)
        self.assertFalse(HarvestedDataset.objects.filter(key='59d46416-34e8-4da6-8d6f-1e3fc7b1b88b'))


class HarvestedDatasetModelMethodTestCase(TestCase):

    def setUp(self):
        project = Project.objects.create(title='my project tile', funding='my project funding')
        dataset = Dataset.objects.create(dataset_key='123', project=project)
        HarvestedDataset.objects.create(key='123', include_in_antabif=False, import_full_dataset=True, dataset=dataset)
        GBIFOccurrence.objects.create(gbifID='1', dataset=dataset)

    def test_delete_related_objects(self):
        """Ensure related objects of HarvestedDataset are deleted"""
        harvested_dataset = HarvestedDataset.objects.get(key='123')
        harvested_dataset.delete_related_objects()
        self.assertFalse(Dataset.objects.filter(dataset_key='123').exists())
        self.assertFalse(Project.objects.filter(title='my project title').exists())
        self.assertFalse(GBIFOccurrence.objects.filter(dataset__dataset_key='123').exists())
        # ensure that HarvestedDataset is still exist
        self.assertTrue(HarvestedDataset.objects.filter(key='123').exists())
        self.assertFalse(HarvestedDataset.objects.get(key='123').include_in_antabif)
        self.assertTrue(harvested_dataset.import_full_dataset)


class HexGridTestCase(TestCase):
    """Test HexGrid managers which load grids into database"""

    @override_settings(GRIDS_DIR='data_manager/tests/test_data/no_grids/')
    def test_import_grids_fail(self):
        """Ensure NotADirectoryError is raised when a wrong directory is provided"""
        with self.assertRaises(NotADirectoryError):
            HexGrid.objects.import_grids(grids_dir='path/not/found')

    @override_settings(GRIDS_DIR='data_manager/tests/test_data/grids/')
    def test_import_grids_success(self):
        """Ensure that HexGrid import is successful"""
        HexGrid.objects.import_grids(settings.GRIDS_DIR)
        self.assertTrue(HexGrid.objects.exists())
        self.assertTrue(HexGrid.objects.filter(size=250000).exists())


class DwCAManagerTestCase(TestCase):
    """
    To be inherited for following test class
    """

    def setUp(self):
        self.dwca = DwCAReader('data_manager/tests/test_data/test-dwca-manager.zip')
        self.dataset = import_eml(self.dwca.source_metadata)
        self.core_row = self.dwca.get_corerow_by_position(0)
        # "day" and "decimalLatitude" fields for this record is intentionally made empty
        self.row_with_empty_value = self.dwca.get_corerow_by_position(1)
        self.verbatim_row = get_extension_data_from_core_row(
            self.core_row, extension_uri='http://rs.tdwg.org/dwc/terms/Occurrence')
        return self

    def tearDown(self):
        self.dwca.close()


class GBIFDwCAManagerTestCase(DwCAManagerTestCase):
    """
    Tests for data_manager.manager.GBIFOccurrenceManager class methods which do not use database.
    """

    def test_get_uri_field_name(self):
        """
        Ensure get_uri_field_name() returns a dict with key = uri if help_text of the model is a uri,
        value = field name
        """
        returned_uri_field_name_dict = GBIFOccurrence.objects.get_uri_field_name()
        uri_field_name_dict = {'http://purl.org/dc/terms/type': '_type', 'http://purl.org/dc/terms/license': 'license',
                               'http://purl.org/dc/terms/rightsHolder': 'rightsHolder',
                               'http://purl.org/dc/terms/accessRights': 'accessRights',
                               'http://purl.org/dc/terms/bibliographicCitation': 'bibliographicCitation',
                               'http://purl.org/dc/terms/references': 'references',
                               'http://rs.tdwg.org/dwc/terms/datasetID': 'datasetID',
                               'http://rs.tdwg.org/dwc/terms/institutionCode': 'institutionCode',
                               'http://rs.tdwg.org/dwc/terms/collectionID': 'collectionID',
                               'http://rs.tdwg.org/dwc/terms/collectionCode': 'collectionCode',
                               'http://rs.tdwg.org/dwc/terms/institutionID': 'institutionID',
                               'http://rs.tdwg.org/dwc/terms/datasetName': 'datasetName',
                               'http://rs.tdwg.org/dwc/terms/dynamicProperties': 'dynamicProperties',
                               'http://rs.tdwg.org/dwc/terms/occurrenceID': 'occurrenceID',
                               'http://rs.tdwg.org/dwc/terms/catalogNumber': 'catalogNumber',
                               'http://rs.tdwg.org/dwc/terms/recordedBy': 'recordedBy',
                               'http://rs.tdwg.org/dwc/terms/individualCount': 'individualCount',
                               'http://rs.tdwg.org/dwc/terms/organismQuantity': 'organismQuantity',
                               'http://rs.tdwg.org/dwc/terms/organismQuantityType': 'organismQuantityType',
                               'http://rs.tdwg.org/dwc/terms/sex': 'sex',
                               'http://rs.tdwg.org/dwc/terms/lifeStage': 'lifeStage',
                               'http://rs.tdwg.org/dwc/terms/reproductiveCondition': 'reproductiveCondition',
                               'http://rs.tdwg.org/dwc/terms/behavior': 'behavior',
                               'http://rs.tdwg.org/dwc/terms/occurrenceStatus': 'occurrenceStatus',
                               'http://rs.tdwg.org/dwc/terms/occurrenceRemarks': 'occurrenceRemarks',
                               'http://rs.tdwg.org/dwc/terms/associatedReferences': 'associatedReferences',
                               'http://rs.tdwg.org/dwc/terms/associatedSequences': 'associatedSequences',
                               'http://rs.tdwg.org/dwc/terms/materialSampleID': 'materialSampleID',
                               'http://rs.tdwg.org/dwc/terms/eventID': 'eventID',
                               'http://rs.tdwg.org/dwc/terms/parentEventID': 'parentEventID',
                               'http://rs.tdwg.org/dwc/terms/fieldNumber': 'fieldNumber',
                               'http://rs.tdwg.org/dwc/terms/eventDate': 'eventDate',
                               'http://rs.tdwg.org/dwc/terms/eventTime': 'eventTime',
                               'http://rs.tdwg.org/dwc/terms/verbatimEventDate': 'verbatimEventDate',
                               'http://rs.tdwg.org/dwc/terms/samplingProtocol': 'samplingProtocol',
                               'http://rs.tdwg.org/dwc/terms/sampleSizeValue': 'sampleSizeValue',
                               'http://rs.tdwg.org/dwc/terms/sampleSizeUnit': 'sampleSizeUnit',
                               'http://rs.tdwg.org/dwc/terms/samplingEffort': 'samplingEffort',
                               'http://rs.tdwg.org/dwc/terms/fieldNotes': 'fieldNotes',
                               'http://rs.tdwg.org/dwc/terms/eventRemarks': 'eventRemarks',
                               'http://rs.tdwg.org/dwc/terms/locationID': 'locationID',
                               'http://rs.tdwg.org/dwc/terms/continent': 'continent',
                               'http://rs.tdwg.org/dwc/terms/waterBody': 'waterBody',
                               'http://rs.tdwg.org/dwc/terms/countryCode': 'countryCode',
                               'http://rs.tdwg.org/dwc/terms/locality': 'locality',
                               'http://rs.tdwg.org/dwc/terms/verbatimLocality': 'verbatimLocality',
                               'http://rs.tdwg.org/dwc/terms/verbatimDepth': 'verbatimDepth',
                               'http://rs.tdwg.org/dwc/terms/minimumDistanceAboveSurfaceInMeters': 'minimumDistanceAboveSurfaceInMeters',
                               'http://rs.tdwg.org/dwc/terms/maximumDistanceAboveSurfaceInMeters': 'maximumDistanceAboveSurfaceInMeters',
                               'http://rs.tdwg.org/dwc/terms/locationAccordingTo': 'locationAccordingTo',
                               'http://rs.tdwg.org/dwc/terms/locationRemarks': 'locationRemarks',
                               'http://rs.tdwg.org/dwc/terms/geodeticDatum': 'geodeticDatum',
                               'http://rs.tdwg.org/dwc/terms/footprintWKT': 'footprintWKT',
                               'http://rs.tdwg.org/dwc/terms/footprintSRS': 'footprintSRS',
                               'http://rs.tdwg.org/dwc/terms/verbatimSRS': 'verbatimSRS',
                               'http://rs.tdwg.org/dwc/terms/verbatimCoordinateSystem': 'verbatimCoordinateSystem',
                               'http://rs.tdwg.org/dwc/terms/identificationQualifier': 'identificationQualifier',
                               'http://rs.tdwg.org/dwc/terms/taxonID': 'taxonID',
                               'http://rs.tdwg.org/dwc/terms/scientificNameID': 'scientificNameID',
                               'http://rs.tdwg.org/dwc/terms/scientificName': 'scientificName',
                               'http://rs.tdwg.org/dwc/terms/kingdom': 'kingdom',
                               'http://rs.tdwg.org/dwc/terms/phylum': 'phylum',
                               'http://rs.tdwg.org/dwc/terms/class': '_class',
                               'http://rs.tdwg.org/dwc/terms/order': 'order',
                               'http://rs.tdwg.org/dwc/terms/family': 'family',
                               'http://rs.tdwg.org/dwc/terms/genus': 'genus',
                               'http://rs.tdwg.org/dwc/terms/subgenus': 'subgenus',
                               'http://rs.tdwg.org/dwc/terms/specificEpithet': 'specificEpithet',
                               'http://rs.tdwg.org/dwc/terms/infraspecificEpithet': 'infraspecificEpithet',
                               'http://rs.tdwg.org/dwc/terms/taxonRank': 'taxonRank',
                               'http://rs.tdwg.org/dwc/terms/verbatimTaxonRank': 'verbatimTaxonRank',
                               'http://rs.tdwg.org/dwc/terms/scientificNameAuthorship': 'scientificNameAuthorship',
                               'http://rs.tdwg.org/dwc/terms/taxonRemarks': 'taxonRemarks',
                               'http://rs.gbif.org/terms/1.0/gbifID': 'gbifID',
                               'http://rs.tdwg.org/dwc/terms/basisOfRecord': 'basisOfRecord',
                               'http://rs.gbif.org/terms/1.0/datasetKey': 'datasetKey',
                               'http://rs.gbif.org/terms/1.0/elevation': 'elevation',
                               'http://rs.gbif.org/terms/1.0/distanceAboveSurface': 'distanceAboveSurface',
                               'http://rs.gbif.org/terms/1.0/issue': 'issue',
                               'http://rs.gbif.org/terms/1.0/mediaType': 'mediaType',
                               'http://purl.org/dc/terms/date': 'date',
                               'http://rs.gbif.org/terms/1.0/taxonKey': 'taxonKey',
                               'http://rs.gbif.org/terms/1.0/kingdomKey': 'kingdomKey',
                               'http://rs.gbif.org/terms/1.0/phylumKey': 'phylumKey',
                               'http://rs.gbif.org/terms/1.0/classKey': 'classKey',
                               'http://rs.gbif.org/terms/1.0/orderKey': 'orderKey',
                               'http://rs.gbif.org/terms/1.0/familyKey': 'familyKey',
                               'http://rs.gbif.org/terms/1.0/genusKey': 'genusKey',
                               'http://rs.gbif.org/terms/1.0/subgenusKey': 'subgenusKey',
                               'http://rs.gbif.org/terms/1.0/speciesKey': 'speciesKey',
                               'http://rs.tdwg.org/dwc/terms/decimalLatitude': 'decimalLatitude',
                               'http://rs.tdwg.org/dwc/terms/decimalLongitude': 'decimalLongitude',
                               'http://rs.tdwg.org/dwc/terms/coordinateUncertaintyInMeters': 'coordinateUncertaintyInMeters',
                               'http://rs.tdwg.org/dwc/terms/coordinatePrecision': 'coordinatePrecision',
                               'http://purl.org/dc/terms/modified': 'modified',
                               'http://rs.tdwg.org/dwc/terms/year': 'year',
                               'http://rs.tdwg.org/dwc/terms/month': 'month', 'http://rs.tdwg.org/dwc/terms/day': 'day',
                               'http://rs.gbif.org/terms/1.0/depth': 'depth'}
        self.assertEqual(returned_uri_field_name_dict, uri_field_name_dict)

    def test_string_to_float(self):
        """
        Ensure that string_to_float() returns a dict with key = field name of a float field and converted the string
        to float.
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_float(self.core_row.data, occ_row_dict=dict())
        self.assertEqual(self.core_row.data.get('http://rs.tdwg.org/dwc/terms/decimalLatitude'),
                         '50.83567')  # raw value
        self.assertEqual(returned_row_dict.get('decimalLatitude'), 50.83567)  # converted value

    def test_empty_string_to_float(self):
        """
        Ensure that string_to_float() returns a dict with key = field name of a float field and value = None if the
        value of that field is ''.
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_float(self.row_with_empty_value.data, occ_row_dict=dict())
        # this row does not have value for coordinatePrecision
        self.assertEqual(self.row_with_empty_value.data.get('http://rs.tdwg.org/dwc/terms/coordinatePrecision'), '')
        self.assertIsNone(returned_row_dict.get('coordinatePrecision'))  # converted value

    def test_string_to_int(self):
        """
        Ensure that string_to_int() returns a dict with key = field name of an integer field and converted the string
        to int.
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_int(self.core_row.data, occ_row_dict=dict())
        self.assertEqual(self.core_row.data.get('http://rs.tdwg.org/dwc/terms/day'), '2')  # raw value
        self.assertEqual(returned_row_dict.get('day'), 2)  # converted value

    def test_empty_string_to_int(self):
        """
        Ensure that string_to_int() returns a dict with key = field name of an integer field and value = None if the
        value of that field is ''.
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_int(self.row_with_empty_value.data,
                                                                 occ_row_dict=dict())
        self.assertEqual(self.row_with_empty_value.data.get('http://rs.tdwg.org/dwc/terms/day'), '')  # raw value
        self.assertIsNone(returned_row_dict.get('day'))  # converted value

    def test_string_to_point(self):
        """
        Ensure that string_to_point() returns a dict with key = 'geopoint' and
        value = a django.contrib.gis.geos.point.Point object.
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_point(self.core_row.data, occ_row_dict=dict())
        self.assertEqual(self.core_row.data.get('http://rs.tdwg.org/dwc/terms/decimalLongitude'),
                         '4.84022')  # raw value
        self.assertEqual(self.core_row.data.get('http://rs.tdwg.org/dwc/terms/decimalLatitude'),
                         '50.83567')  # raw value
        self.assertEqual(returned_row_dict.get('geopoint').wkt, 'POINT (4.84022 50.83567)')  # converted value

    def test_empty_string_to_point(self):
        """
        Ensure that string_to_point() returns a dict with key = 'geopoint' and
        value = None if one of the field (decimalLatitude or decimalLongitude) is empty
        """
        returned_row_dict = GBIFOccurrence.objects.string_to_point(self.row_with_empty_value.data,
                                                                   occ_row_dict=dict())
        self.assertEqual(self.row_with_empty_value.data.get('http://rs.tdwg.org/dwc/terms/decimalLongitude'), '')
        self.assertEqual(self.row_with_empty_value.data.get('http://rs.tdwg.org/dwc/terms/decimalLatitude'), '50.83567')
        self.assertIsNone(returned_row_dict.get('geopoint'))  # converted value


class InstantiateDwCATestCase(DwCAManagerTestCase):
    """
    GBIFOccurrence manager test case, requires access to database
    """

    def test_instantiate(self):
        """
        Ensure that manager instantiate GBIFOccurrence objects correctly
        """
        occ = GBIFOccurrence.objects.instantiate(self.core_row.data, dataset_object=self.dataset)
        # FK, int, float, full text search field
        self.assertEqual(occ.dataset, self.dataset)
        self.assertEqual(occ.basis_of_record, BasisOfRecord.objects.get(basis_of_record='HUMAN_OBSERVATION'))
        self.assertEqual(occ.geopoint.wkt, 'POINT (4.84022 50.83567)')
        self.assertEqual(occ.decimalLongitude, 4.84022)
        self.assertEqual(occ.decimalLatitude, 50.83567)
        self.assertEqual(occ.year, 2004)
        self.assertEqual(occ.month, 7)
        self.assertEqual(occ.day, 2)
        self.assertEqual(occ.row_json_text,
                         ['Event', 'CC0_1_0', 'INBO', 'http://www.inbo.be/en/norms-for-data-use', '', '',
                          'http://dataset.inbo.be/inboveg-niche-vlaanderen-events', 'INBO', '', '', '',
                          '"InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium"',
                          '', 'INBO:INBOVEG:OCC:00407292', '', 'Els De Bie', '', 'p1', 'londo Scale (1976)', '', '', '',
                          '', 'present', '', '', '', '', 'INBO:INBOVEG:0IV2013102211361614', '', '',
                          '2004-07-02T00:00:00Z', '', '2004-07-02/2004-07-02',
                          'vegetation plot with Londo scale (1976): mosses identified', '9', 'm²', '', '', '',
                          'SNOP027X', 'EUROPE', '', 'BE', '', 'Snoekengracht', '', '', '', 'MILKLIM-areas', '', None,
                          '', '', 'Belgium Datum 1972', 'Belgian Lambert 72', '', 'INBSYS0000010112', '',
                          'Cerastium fontanum subsp. vulgare (Hartm.) Greuter & Burdet', 'Plantae', 'Tracheophyta',
                          'Magnoliopsida', 'Caryophyllales', 'Caryophyllaceae', 'Cerastium', '', 'fontanum', 'vulgare',
                          'SUBSPECIES', '', None, '', '1316184895', 'HUMAN_OBSERVATION',
                          '3d1231e8-2554-45e6-b354-e590c56ce9a8', '', '', '', '', '', '3811517', '6', '7707728', '220',
                          '422', '2518', '2873815', '', '3085458', 50.83567, 4.84022, 30.0, None, '', 2004, 7, 2, None])


class GBIFVerbatimDwCAManagerTestCase(DwCAManagerTestCase):

    def test_verbatim_dict_from_row(self):
        """
        Ensure that verbatim dict is returned as expected
        """
        returned_verbatim_dict = GBIFVerbatimOccurrence.objects.verbatim_dict_from_row_data(self.core_row.data)
        expected_verbatim_dict = {'_type': 'Event', 'license': 'CC0_1_0', 'rightsHolder': 'INBO',
                                  'accessRights': 'http://www.inbo.be/en/norms-for-data-use',
                                  'bibliographicCitation': '', 'references': '',
                                  'datasetID': 'http://dataset.inbo.be/inboveg-niche-vlaanderen-events',
                                  'institutionCode': 'INBO', 'collectionID': '', 'collectionCode': '',
                                  'institutionID': '',
                                  'datasetName': '"InboVeg - NICHE-Vlaanderen groundwater related vegetation relevés for Flanders, Belgium"',
                                  'dynamicProperties': '', 'occurrenceID': 'INBO:INBOVEG:OCC:00407292',
                                  'catalogNumber': '', 'recordedBy': 'Els De Bie', 'individualCount': '',
                                  'organismQuantity': 'p1', 'organismQuantityType': 'londo Scale (1976)', 'sex': '',
                                  'lifeStage': '', 'reproductiveCondition': '', 'behavior': '',
                                  'occurrenceStatus': 'present', 'occurrenceRemarks': '', 'associatedReferences': '',
                                  'associatedSequences': '', 'materialSampleID': '',
                                  'eventID': 'INBO:INBOVEG:0IV2013102211361614', 'parentEventID': '', 'fieldNumber': '',
                                  'eventDate': '2004-07-02T00:00:00Z', 'eventTime': '',
                                  'verbatimEventDate': '2004-07-02/2004-07-02',
                                  'samplingProtocol': 'vegetation plot with Londo scale (1976): mosses identified',
                                  'sampleSizeValue': '9', 'sampleSizeUnit': 'm²', 'samplingEffort': '',
                                  'fieldNotes': '', 'eventRemarks': '', 'locationID': 'SNOP027X', 'continent': 'EUROPE',
                                  'waterBody': '', 'countryCode': 'BE', 'locality': '',
                                  'verbatimLocality': 'Snoekengracht', 'verbatimDepth': '',
                                  'minimumDistanceAboveSurfaceInMeters': '', 'maximumDistanceAboveSurfaceInMeters': '',
                                  'locationAccordingTo': 'MILKLIM-areas', 'locationRemarks': '', 'geodeticDatum': None,
                                  'footprintWKT': '', 'footprintSRS': '', 'verbatimSRS': 'Belgium Datum 1972',
                                  'verbatimCoordinateSystem': 'Belgian Lambert 72', 'identificationQualifier': '',
                                  'taxonID': 'INBSYS0000010112', 'scientificNameID': '',
                                  'scientificName': 'Cerastium fontanum subsp. vulgare (Hartm.) Greuter & Burdet',
                                  'kingdom': 'Plantae', 'phylum': 'Tracheophyta', '_class': 'Magnoliopsida',
                                  'order': 'Caryophyllales', 'family': 'Caryophyllaceae', 'genus': 'Cerastium',
                                  'subgenus': '', 'specificEpithet': 'fontanum', 'infraspecificEpithet': 'vulgare',
                                  'taxonRank': 'SUBSPECIES', 'verbatimTaxonRank': '', 'scientificNameAuthorship': None,
                                  'taxonRemarks': '', 'gbifID': '1316184895', 'basisOfRecord': 'HUMAN_OBSERVATION',
                                  'country': None, 'decimalLatitude': '50.83567', 'decimalLongitude': '4.84022',
                                  'coordinateUncertaintyInMeters': '30', 'coordinatePrecision': '', 'modified': '',
                                  'year': '2004', 'month': '7', 'day': '2', 'minimumElevationInMeters': None,
                                  'maximumElevationInMeters': None, 'verbatimElevation': '',
                                  'minimumDepthInMeters': None, 'maximumDepthInMeters': None}
        self.assertEqual(returned_verbatim_dict, expected_verbatim_dict)
        self.assertEqual(self.core_row.data.get('http://rs.gbif.org/terms/1.0/gbifID'),
                         returned_verbatim_dict.get('gbifID'))

    def test_create_in_bulk(self):
        """
        Ensure that GBIFVerbatimOccurrence is created as expected
        """
        occ = GBIFOccurrence.objects.instantiate(self.core_row.data, self.dataset)
        occ.save()
        list_of_verbatim = [GBIFVerbatimOccurrence.objects.verbatim_dict_from_row_data(self.core_row.data)]  #todo:should be verbatim row
        list_of_gbif_ids = [self.core_row.data.get('http://rs.gbif.org/terms/1.0/gbifID')]
        verbatim_objects = GBIFVerbatimOccurrence.objects.create_in_bulk(list_of_verbatim, list_of_gbif_ids)
        verbatim_object = verbatim_objects[0]  # only one verbatim object
        occurrence_object = GBIFOccurrence.objects.get(gbifID=list_of_gbif_ids[0])  # ensure occurrence is created
        self.assertEqual(verbatim_object.occurrence, occurrence_object)
        self.assertEqual(verbatim_object.decimalLongitude, '4.84022')
