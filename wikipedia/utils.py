import datetime

import re


NAMED_REF_REGEX = re.compile(
    r'<ref name=("(?P<name1>[^"]+?)"|(?P<name2>[^ /"]+?))>[^<]+</ref>'
)
def get_ref_definitions(line):
    for ref_match in NAMED_REF_REGEX.finditer(line):
        yield (
            ref_match.group('name1') or ref_match.group('name2'),
            ref_match.group()
        )


REF_BY_NAME_REGEX = re.compile(
    r'<ref name=("(?P<name1>[^"]+)?"|(?P<name2>[^ ]+?)) ?/>'
)
def replace_refs(line, definitions):
    for ref_match in REF_BY_NAME_REGEX.finditer(line):
        name = ref_match.group('name1') or ref_match.group('name2')
        definition = definitions.get(name)
        if definition:
            line = line.replace(ref_match.group(0), definition)

    return line


SPLIT_REGEX = re.compile(
    '('
    r'(\[\[[^\]]{5,}\]\]|[A-Za-z .])'
    r'(, ?| and |)'
    r'(<ref name="[^"]+" ?/>|<ref[^<]+?</ref>)'
    ')'
)
def split_endorsements(line):
    for match in SPLIT_REGEX.finditer(line):
        yield match.group(0)


BRACES_REGEX = re.compile(r'{{[^}]+}}')
USEFUL_REF_REGEX = re.compile(r'<ref( [^>/]*|)(?!/)>(?P<ref>.*?)</ref>')
ANY_REF_REGEX = re.compile(r'(<ref[^>]*(?!/)>.*?</ref>|<ref[^/]*?/>)')
NUMBERS_DATE_FORMAT = re.compile(r'\d{4}-\d{2}-\d{2}$')
SHORT_DATE_FORMAT = re.compile('[A-z][a-z]{2} ')
NAMED_LINKS_REGEX = re.compile(r'\[\[[^|\]]+\|([^\]]+)\]\]')
def parse_wiki_text(text):
    citation_name = None
    citation_url = None
    citation_date = None
    endorser_name = None
    endorser_details = None

    useful_ref_matches = USEFUL_REF_REGEX.finditer(text)
    for ref_match in useful_ref_matches:
        ref = ref_match.group('ref') or ''
        if ref.lower().startswith('{{cite '):
            ref_values = {}
            for ref_part in ref.strip('}').split('|'):
                if ref_part.count('=') != 1:
                    continue

                ref_part = ref_part.strip()
                key, value = ref_part.split('=')
                key = key.lower().strip()
                value = value.strip()
                if value:
                    ref_values[key] = value

            citation_url = ref_values.get('url')
            citation_name = (
                ref_values.get('publisher') or ref_values.get('work') or
                ref_values.get('website') or ref_values.get('newspaper')
            )
            citation_date = (
                ref_values.get('date') or ref_values.get('accessdate') or
                ref_values.get('access-date')
            )
        elif ref.startswith('http') and not citation_url:
            citation_url = ref
        elif '[http' in ref and ']' in ref and not citation_url:
            # Strip away anything before or after the p[.
            ref_remainder = ref[ref.index('[')+1:ref.index(']')]

            # The first space splits up the URL and the rest of the ref.
            citation_url = ref_remainder.partition(' ')[0]
        else:
            continue

    remainder = ANY_REF_REGEX.sub('', text)

    # Remove [[]]-style links, if they exist.
    if NAMED_LINKS_REGEX.search(remainder):
        remainder = NAMED_LINKS_REGEX.sub(r'\1', remainder)
    remainder = remainder.replace('[', '').replace(']', '')
    remainder = BRACES_REGEX.sub('', remainder)

    # Assume that everything before the comma (if present) is the name.
    comma_parts = remainder.split(',')
    pre_comma = comma_parts[0]
    pre_comma = pre_comma.strip(" '")
    endorser_name = pre_comma
    endorser_details = ','.join(comma_parts[1:]).strip()
    # Make sure the first letter is capitalised
    if endorser_details:
        endorser_details = (
            endorser_details[0].upper() + endorser_details[1:]
        )

    # Remove [[]] from around the publisher name, if used.
    if citation_name:
        citation_name = citation_name.strip('[]')

    # Convert the date into an actual date object.
    if citation_date:
        # If there are only numbers, it's probably YYYY-MM-DD.
        if NUMBERS_DATE_FORMAT.match(citation_date):
            date_format = '%Y-%m-%d'
        elif SHORT_DATE_FORMAT.match(citation_date):
            date_format = '%b %d, %Y'
        elif ',' not in citation_date:
            if (
                    citation_date.count(' ') == 2 and
                    len(citation_date.split(' ')[1]) == 3
            ):
                date_format = '%d %b %Y'
            else:
                date_format = '%d %B %Y'
        else:
            # Otherwise, assume it's like July 16, 2016.
            date_format = '%B %d, %Y'

        citation_date = datetime.datetime.strptime(
            citation_date,
            date_format
        ).date()

    return {
        'citation_url': citation_url,
        'citation_date': citation_date,
        'citation_name': citation_name,
        'endorser_name': endorser_name,
        'endorser_details': endorser_details,
    }
