import re

from django.core.management.base import BaseCommand, CommandError
import requests

from wikipedia.models import BulkImport, ImportedEndorsement
from wikipedia.utils import get_ref_definitions, replace_refs, ANY_REF_REGEX, \
                            split_endorsements


COMMENTS_REGEX = re.compile(r'<!--.*?-->')
COLON_SECTION_REGEX = re.compile('([a-zA-Z ]+): ')

URL = 'https://en.wikipedia.org/w/api.php?action=parse&page={slug}&prop=wikitext&format=json'
NAMED_LINKS_REGEX = re.compile(r'\[\[[^|\]]+\|([^\]]+)\]\]')
class Command(BaseCommand):
    help = 'Bulk import all the endorsements from a Wikipedia page'

    def add_arguments(self, parser):
        parser.add_argument('slug')
        parser.add_argument(
            '--create',
            action='store_true',
            dest='create',
            default=False,
            help="Creates everything (otherwise, it's a dry run)",
        )

    def import_endorsement(self, raw_text, sections):
        # Make sure that named references are replaced.
        raw_text = replace_refs(raw_text, self.reference_definitions)
        sections_string = ' > '.join(sections)
        if raw_text:
            try:
                ImportedEndorsement.objects.get(
                    sections=sections_string,
                    raw_text=raw_text,
                    bulk_import__slug=self.slug,
                )
                return False
            except ImportedEndorsement.DoesNotExist:
                if self.create:
                    ImportedEndorsement.objects.create(
                        bulk_import=self.bulk_import,
                        raw_text=raw_text,
                        sections=sections_string,
                    )
                print raw_text, sections_string
                print "------"
                return True

    def handle(self, *args, **options):
        url = URL.format(slug=options['slug'])
        response = requests.get(url)
        data = response.json()
        wikitext = data['parse']['wikitext']['*']

        self.slug = options['slug']
        self.create = options['create']

        if self.create:
            self.bulk_import = BulkImport.objects.create(
                slug=options['slug'],
                text=wikitext
            )

        # Skip until the first line that starts with a ==.
        lines = wikitext.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('=='):
                break

        # Do a first pass to find and replace named references.
        self.reference_definitions = {}
        for line in lines:
            for name, definition in get_ref_definitions(line):
                self.reference_definitions[name] = definition

        num_imported = 0

        # Now go through the endorsements, keeping note of the section.
        sections = []
        current_endorsement = []
        current_line = []
        current_line_sections = []
        for line in lines[i:]:
            if not line.strip():
                continue

            # On the Trump and Hillary pages, '''{{small|[[Header]]}}''' is
            # used instead of =====Header=====.
            if (
                    line.startswith("'''{{small|") and
                    (
                        line.endswith("}}'''") or
                        line.endswith('</ref>') or
                        line.endswith('/>')
                    )
            ):
                section_name = line.partition('|')[2].partition('}')[0]
                line = '=====' + section_name + '====='

            if line.startswith('* ') or line.startswith('=='):
                # Clear the current line.
                if current_line:
                    raw_text = ''.join(current_line).strip()

                    num_imported += self.import_endorsement(
                        raw_text,
                        current_line_sections,
                    )
                    current_line = []

                if line.startswith('* '):
                    line = line[2:]
                    if line == '[[List of Donald Trump presidential campaign primary endorsements, 2016]]':
                        continue

                    # If it's like "Member of the Nevada Assembly: " etc
                    colon_section_match = COLON_SECTION_REGEX.match(line)
                    if colon_section_match:
                        colon_section = colon_section_match.group(1)
                        line_remainder = line.partition(':')[2]
                        for sub_line in split_endorsements(line_remainder):
                            num_imported += self.import_endorsement(
                                sub_line,
                                sections + [colon_section],
                            )
                        continue

                    current_line = [line]
                    current_line_sections = sections
                else:
                    current_line_sections = list(sections)
                    # In case there's a <ref> tag, get rid of it.
                    if '<ref' in line:
                        line = ANY_REF_REGEX.sub('', line)
                    if '<!--' in line:
                        line = COMMENTS_REGEX.sub('', line)

                    if '[[' in line:
                        if NAMED_LINKS_REGEX.search(line):
                            line = NAMED_LINKS_REGEX.sub(r'\1', line)
                        line = line.replace('[', '').replace(']', '')

                    section_name = line.strip('=').strip()

                    # Stop when we get to "See also" or "References".
                    if section_name in ('See also', 'References'):
                        break

                    current_depth = line.count('=') / 2 - 2

                    # We may need to pop some sections off the stack first.
                    if len(sections) > current_depth:
                        num_to_pop = len(sections) - current_depth
                        for j in xrange(num_to_pop):
                            sections.pop()
                    sections.append(section_name)
            elif line:
                if line.startswith('{{'):
                    continue
                if line.startswith('[['):
                    continue
                if line.startswith('}}') and line != '}}</ref>':
                    continue
                if line.startswith('<!-'):
                    continue
                if line.startswith("''Those who indicated"):
                    continue

                # Add this to the current line.
                current_line.append(line)
                current_line_sections = list(sections)

        print "=========================="
        if self.create:
            print "CREATED", num_imported
        else:
            print "Would have created", num_imported
