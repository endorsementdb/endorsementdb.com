from __future__ import unicode_literals
import datetime
import re

from django.core.exceptions import MultipleObjectsReturned
from django.db import models

from endorsements.models import Endorser


class BulkImport(models.Model):
    slug = models.SlugField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    def __unicode__(self):
        return str(self.created_at)


class ImportedEndorser(models.Model):
    slug = models.SlugField()


REF_REGEX = re.compile(r'(<ref[^>]*>(?P<ref>.*)</ref>|<ref name="[^"]*" ?/>)')
REF_KEY_REGEX = re.compile('([^=]+)=')
NUMBERS_DATE_FORMAT = re.compile(r'\d{4}-\d{2}-\d{2}$')
SHORT_DATE_FORMAT = re.compile('[A-z][a-z]{2} ')
NAMED_LINKS_REGEX = re.compile(r'\[\[[^|\]]+\|([^\]]+)\]\]')
class ImportedEndorsement(models.Model):
    bulk_import = models.ForeignKey(BulkImport)
    raw_text = models.TextField()
    imported_endorser = models.ForeignKey(
        ImportedEndorser, blank=True, null=True
    )
    confirmed_endorser = models.ForeignKey(Endorser, blank=True, null=True)
    sections = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def parse_text(self):
        citation_name = None
        citation_url = None
        citation_date = None
        endorser_name = None
        endorser_details = None

        text = self.raw_text
        ref_match = REF_REGEX.search(text)

        if ref_match:
            ref = ref_match.group('ref') or ''
            if ref.startswith('http'):
                citation_url = ref
            elif ref.startswith('{{cite '):
                ref_values = {}
                for ref_part in ref.strip('}').split('|'):
                    if '=' not in ref_part:
                        continue

                    ref_part = ref_part.strip()
                    key = REF_KEY_REGEX.match(ref_part).group(1)
                    value = ref_part[len(key) + 1:].strip()
                    if value:
                        ref_values[key] = value

                citation_url = ref_values.get('url')
                citation_name = (
                    ref_values.get('publisher') or ref_values.get('work') or
                    ref_values.get('website')
                )
                citation_date = (
                    ref_values.get('date') or ref_values.get('accessdate')
                )

            full_ref = ref_match.group(0)
            if full_ref:
                remainder = text.rpartition(full_ref)[0]
            else:
                remainder = text

            # Remove [[]]-style links, if they exist.
            if NAMED_LINKS_REGEX.search(remainder):
                remainder = NAMED_LINKS_REGEX.sub(r'\1', remainder)
            remainder = remainder.replace('[', '').replace(']', '')

            # Assume that everything before the comma (if present) is the name.
            comma_parts = remainder.split(',')
            pre_comma = comma_parts[0]
            pre_comma = pre_comma.strip("'")
            endorser_name = pre_comma
            endorser_details = ','.join(comma_parts[1:]).strip()
            # Make sure the first letter is capitalised
            if endorser_details:
                endorser_details = (
                    endorser_details[0].upper() + endorser_details[1:]
                )
        else:
            remainder = text
            ref = None

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

    def get_likely_endorser(self):
        name = self.parse_text()['endorser_name']
        if not name:
            return

        name = name.lower()

        try:
            return Endorser.objects.get(name__iexact=name)
        except Endorser.DoesNotExist:
            pass

        # See if putting "The" in front helps.
        if not name.startswith('the '):
            try:
                return Endorser.objects.get(name__iexact='the ' + name)
            except Endorser.DoesNotExist:
                pass

        # See if the last name and part of the first name match.
        if ' ' in name:
            split_name = name.split(' ')
            first_name_start = split_name[0][:3]
            last_name = split_name[-1]
            if len(last_name) > 2:
                try:
                    return Endorser.objects.get(
                        name__iendswith=last_name,
                        name__istartswith=first_name_start,
                    )
                except (Endorser.DoesNotExist, MultipleObjectsReturned):
                    pass

    def __unicode__(self):
        return self.raw_text
