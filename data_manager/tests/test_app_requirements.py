from django.test import TestCase


class AppRequirementTestCase(TestCase):
    """Ensure that dependencies that go to the right requirements file"""

    def test_requirements(self):
        """Ensure django-debug-toolbar, coverage and Pympler not in requirements.txt"""
        with open('requirements.txt', 'r') as file:
            file_content = file.read()
            self.assertNotIn('django-debug-toolbar', file_content)
            self.assertNotIn('coverage', file_content)
            self.assertIn('Django', file_content)

    def test_dev_requirements(self):
        """Ensure django-debug-toolbar, coverage and Pympler in requirements-dev.txt"""
        with open('requirements-dev.txt', 'r') as file:
            file_content = file.read()
            self.assertIn('django-debug-toolbar', file_content)
            self.assertIn('coverage', file_content)
            self.assertNotIn('Django', file_content)
