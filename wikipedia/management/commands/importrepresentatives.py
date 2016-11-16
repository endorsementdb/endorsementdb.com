from datetime import datetime

from BeautifulSoup import BeautifulSoup as BS
from django.core.management.base import BaseCommand, CommandError
import requests

from endorsements.models import Tag, Candidate
from wikipedia.models import BulkImport, ImportedRepresentative


URL = 'https://en.wikipedia.org/w/api.php?action=parse&page={slug}&prop=text&format=json&section={section}'
SLUG = 'Current_members_of_the_United_States_House_of_Representatives'
SECTION = 7

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

        reps = []

        for i, table_row in enumerate(soup.findAll('tr')):
            if i == 0:
                continue

            table_cells = table_row.findAll('td')
            assert len(table_cells) == 8

            state_string = table_cells[0].find('a').string
            if state_string.endswith(' At Large'):
                state = state_string[:-9]
            else:
                state = state_string.rpartition(' ')[0]

            name = table_cells[1].find('span', {'class': 'fn'}).find('a').string

            party = table_cells[3].string

            reps.append({
                'name': name,
                'party': party,
                'state': state,
            })

        if options['create']:
            bulk_import = BulkImport.objects.create(
                slug=SLUG,
                text=text
            )
            for rep in reps:
                party_tag = Tag.objects.get(name=rep['party'] + ' Party')
                state_tag = Tag.objects.get(name=rep['state'])
                ImportedRepresentative.objects.create(
                    name=rep['name'],
                    party=party_tag,
                    state=state_tag,
                    bulk_import=bulk_import,
                )
                print rep

            print len(reps)
