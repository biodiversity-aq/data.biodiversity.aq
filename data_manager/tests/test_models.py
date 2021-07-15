from data_manager.models import Download
from django.test import TestCase
from django.http import QueryDict
from json.decoder import JSONDecodeError


class DownloadClassMethodTestCase(TestCase):

    def test_get_query_dict(self):
        """
        Ensure QueryDict is generated correctly.
        """
        download = Download.objects.create(
            task_id='test-1', query='{"basisOfRecord": 1, "occurrenceStatus": ["presence", "absence"]}')
        query_dict = QueryDict('', mutable=True)
        query_dict.appendlist("basisOfRecord", 1)
        query_dict.appendlist("occurrenceStatus", "presence")
        query_dict.appendlist("occurrenceStatus", "absence")
        query_dict_generated = download.get_query_dict()
        self.assertEqual(query_dict_generated, query_dict)

    def test_raise_JSONDecodeError(self):
        """
        Ensure JSONDecodeError is raised in get_query_dict() when query is malformed
        """
        download = Download.objects.create(
            task_id='test-1', query='{"basisOfRecord": 1')  # lacks }
        with self.assertRaises(JSONDecodeError):
            download.get_query_dict()
