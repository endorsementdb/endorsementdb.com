from datetime import datetime

from BeautifulSoup import BeautifulSoup as BS
from django.core.management.base import BaseCommand, CommandError
import requests

from wikipedia.models import BulkImport, ImportedNewspaper, NEWSPAPER_SECTIONS


URL = 'https://en.wikipedia.org/w/api.php?action=parse&page={slug}&prop=text&format=json&section={section}'
SLUG = 'Newspaper_endorsements_in_the_United_States_presidential_election,_2016'

class Command(BaseCommand):
    help = 'Bulk import all the newspaper endorsements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            dest='create',
            default=False,
            help="Creates everything (otherwise, it's a dry run)",
        )

    def handle(self, *args, **options):
        for section, section_name in NEWSPAPER_SECTIONS:
            url = URL.format(slug=SLUG, section=section)
            response = requests.get(url)
            data = response.json()
            text = data['parse']['text']['*']
            soup = BS(text)
            rows = []
            for table_row in soup.findAll('tr'):
                if not table_row.findAll('td'):
                    # It's just the table header.
                    continue

                table_cells = table_row.findAll('td')
                assert len(table_cells) == 8

                first_cell = table_cells[0]
                i_tag = first_cell.findAll('i')[0]
                name = i_tag.string
                if not name:
                    a_tag = i_tag.findAll('a')[0]
                    name = a_tag.string
                name = name.replace('&amp;', '&')

                # There should be a reference as well.
                ref_id = first_cell.findAll('sup')[0]['id']

                endorsement_2016 = table_cells[1]['data-sort-value']

                cell_text = table_cells[2].find(text=True)
                circulation = None
                if cell_text:
                    cell_text = cell_text.replace(',', '')
                    if cell_text.isdigit():
                        circulation = int(cell_text)

                cell_value = table_cells[3]['data-sort-value']
                date = datetime.strptime(cell_value, '%Y-%m-%d').date()

                a_tags = table_cells[4].findAll('a')
                if not a_tags:
                    # National.
                    city = None
                else:
                    city = a_tags[0].string

                state = table_cells[5].find(text=True)
                if state == 'National':
                    state = None

                endorsement_2012 = table_cells[6].get('data-sort-value')

                row = {
                    'name': name,
                    '2016': endorsement_2016,
                    'circulation': circulation,
                    'date': date,
                    'city': city,
                    'state': state,
                    '2012': endorsement_2012,
                    'ref_id': ref_id,
                }
                if ImportedNewspaper.objects.filter(
                    name=name,
                    circulation=circulation,
                    city=city,
                    state=state
                ).exists():
                    continue

                print row
                rows.append(row)

            # Now get all the references.
            references = {}
            for li in soup.findAll('li'):
                ref_id = li['id'].replace('_note-', '_ref-')
                cite = li.find('cite')
                if cite:
                    url = cite.find('a')['href']
                    references[ref_id] = url

            if not options['create']:
                print "would have created", len(rows)
                continue

            print "ABOUT TO CREATE =========", len(rows)
            bulk_import = BulkImport.objects.create(
                slug=SLUG,
                text=text,
            )
            for row in rows:
                url = references.get(row['ref_id'])

                ImportedNewspaper.objects.create(
                    bulk_import=bulk_import,
                    confirmed_endorser=None,
                    section=section,
                    name=row['name'],
                    endorsement_2016=row['2016'],
                    endorsement_2012=row['2012'],
                    circulation=row['circulation'],
                    date=row['date'],
                    city=row['city'],
                    state=row['state'],
                    url=url,
                )
