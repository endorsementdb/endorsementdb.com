from django.core.management.base import BaseCommand, CommandError
import requests

from wikipedia.models import BulkImport, ImportedEndorsement


URL = 'https://en.wikipedia.org/w/api.php?action=parse&page={slug}&prop=wikitext&format=json'
class Command(BaseCommand):
    help = 'Bulk import all the endorsements from a Wikipedia page'

    def add_arguments(self, parser):
        parser.add_argument('slug')

    def handle(self, *args, **options):
        url = URL.format(slug=options['slug'])
        response = requests.get(url)
        data = response.json()
        wikitext = data['parse']['wikitext']['*']

        bulk_import = BulkImport.objects.create(
            slug=options['slug'],
            text=wikitext
        )

        # Skip until the first line that starts with a ==.
        lines = wikitext.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('=='):
                break

        # Now go through the endorsements, keeping note of the section.
        sections = []
        current_endorsement = []
        current_line = []
        current_line_sections = []
        for line in lines[i:]:
            if not line.strip():
                continue


            if line.startswith('* ') or line.startswith('=='):
                # Clear the current line.
                if current_line:
                    raw_text = ''.join(current_line).strip()
                    sections_string = ' > '.join(current_line_sections)
                    if raw_text:
                        try:
                            ImportedEndorsement.objects.get(
                                sections=sections_string,
                                raw_text=raw_text,
                                #bulk_import__slug=options['slug']
                            )
                        except ImportedEndorsement.DoesNotExist:
                            ImportedEndorsement.objects.create(
                                bulk_import=bulk_import,
                                raw_text=raw_text,
                                sections=sections_string,
                            )
                            print raw_text, sections_string
                            print "===================="
                    current_line = []

                if line.startswith('* '):
                    current_line = [line[2:]]
                    current_line_sections = sections
                else:
                    current_line_sections = list(sections)
                    section_name = line.strip('=')

                    # Stop when we get to "See also" or "References".
                    if section_name in ('See also', 'References'):
                        break

                    current_depth = (len(line) - len(section_name)) / 2 - 2

                    # We may need to pop some sections off the stack first.
                    if len(sections) > current_depth:
                        num_to_pop = len(sections) - current_depth
                        for j in xrange(num_to_pop):
                            sections.pop()
                    sections.append(section_name)
                    continue
            elif line:
                if line.startswith('{{'):
                    continue
                if line.startswith('[['):
                    continue

                # Add this to the current line.
                current_line.append(line)
                current_line_sections = list(sections)
