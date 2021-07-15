from django.core.management.base import BaseCommand
from data_manager.helpers import count_occurrence_per_hexgrid


class Command(BaseCommand):
    help = '''
    Bin occurrences. Count the number of occurrences in each hexagon grids.
    '''

    def handle(self, *args, **options):
        count_occurrence_per_hexgrid()