from datetime import datetime

from BeautifulSoup import BeautifulSoup as BS
from django.core.management.base import BaseCommand, CommandError
import requests

from endorsements.models import Tag, Candidate
from wikipedia.models import BulkImport, ImportedResult


URL = 'https://en.wikipedia.org/w/api.php?action=parse&page={slug}&prop=text&format=json&section={section}'
SLUG = 'United_States_presidential_election,_2016'
SECTION = 36

class Command(BaseCommand):
    help = 'Bulk import all the election results by state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            dest='create',
            default=False,
            help="Creates everything (otherwise, it's a dry run)",
        )

    def handle(self, *args, **options):
        url = URL.format(slug=SLUG, section=SECTION)
        response = requests.get(url)
        data = response.json()
        text = data['parse']['text']['*']
        soup = BS(text)

        results = {}
        for i, table_row in enumerate(soup.findAll('tr')):
            if i < 5 or i > 60:
                continue

            table_cells = table_row.findAll('td')
            assert len(table_cells) == 18

            state = table_cells[0].find('a').string
            if state == 'Washington, D.C.':
                state = 'D.C.'
            elif ',' in state:
                # It's one of the districts. ignore.
                continue
            elif '(' in state:
                state = state.partition('(')[0]

            print state

            stats = {
                'Hillary Clinton': {
                    'count': int(
                        (table_cells[2].string or '0').replace(',', '')
                    ),
                    'percent': float(
                        (table_cells[3].string or '0').strip('%')
                    ),
                },
                'Donald Trump': {
                    'count': int(
                        (table_cells[5].string or '0').replace(',', '')
                    ),
                    'percent': float(
                        (table_cells[6].string or '0').strip('%')
                    ),
                },
                'Gary Johnson': {
                    'count': int(
                        (table_cells[8].string or '0').replace(',', '')
                    ),
                    'percent': float(
                        (table_cells[9].string or '0').strip('%')
                    ),
                },
                'Jill Stein': {
                    'count': int(
                        (table_cells[11].string or '0').replace(',', '')
                    ),
                    'percent': float(
                        (table_cells[12].string or '0').strip('%')
                    ),
                },
                'Evan McMullin': {
                    'count': int(
                        (table_cells[14].string or '0').replace(',', '')
                    ),
                    'percent': float(
                        (table_cells[15].string or '0').strip('%')
                    ),
                }
            }

            results[state] = stats

        if options['create']:
            print "About to create", len(results)
            bulk_import = BulkImport.objects.create(
                slug=SLUG,
                text=text
            )
            for state, stats in results.iteritems():
                for candidate, candidate_stats in stats.iteritems():
                    print state
                    ImportedResult.objects.create(
                        bulk_import=bulk_import,
                        tag=Tag.objects.get(name=state),
                        candidate=Candidate.objects.get(name=candidate),
                        count=candidate_stats['count'],
                        percent=candidate_stats['percent'],
                    )
        else:
            print "Would have created", len(results)
            print results
