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
            if i < 5 or i > 55:
                continue

            table_cells = table_row.findAll('td')
            assert len(table_cells) == 18

            state = table_cells[0].find('a').string

            counts = {
                'Hillary Clinton': int(
                    (table_cells[2].string or '0').replace(',', '')
                ),
                'Donald Trump': int(
                    (table_cells[5].string or '0').replace(',', '')
                ),
                'Gary Johnson': int(
                    (table_cells[8].string or '0').replace(',', '')
                ),
                'Jill Stein': int(
                    (table_cells[11].string or '0').replace(',', '')
                ),
                'Evan McMullin': int(
                    (table_cells[14].string or '0').replace(',', '')
                ),
            }

            results[state] = counts

        if options['create']:
            print "About to create", len(results)
            bulk_import = BulkImport.objects.create(
                slug=SLUG,
                text=text
            )
            for state, counts in results.iteritems():
                for candidate, count in counts.iteritems():
                    ImportedResult.objects.create(
                        bulk_import=bulk_import,
                        tag=Tag.objects.get(name=state),
                        candidate=Candidate.objects.get(name=candidate),
                        count=count,
                    )
        else:
            print "Would have created", len(results)
            print results
