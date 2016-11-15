from __future__ import unicode_literals

from django.db import models

from endorsements.models import Endorser, Tag, Candidate
from wikipedia import utils


class BulkImport(models.Model):
    slug = models.SlugField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    def __unicode__(self):
        return str(self.created_at)


class ImportedResult(models.Model):
    bulk_import = models.ForeignKey(BulkImport)
    tag = models.ForeignKey(Tag)
    candidate = models.ForeignKey(Candidate)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('tag', 'candidate')


# TODO: Delete
class ImportedEndorser(models.Model):
    slug = models.SlugField()


NEWSPAPER_SECTIONS = (
    (3, 'Daily newspapers'),
    (7, 'Weekly newspapers'),
    #(11, 'Magazines'),
    #(15, 'College and university newspapers'),
    #(19, 'Foreign publications'),
)
NEWSPAPER_SLUG = 'Newspaper_endorsements_in_the_United_States_presidential_election,_2016'
class ImportedNewspaper(models.Model):
    bulk_import = models.ForeignKey(BulkImport)
    confirmed_endorser = models.ForeignKey(Endorser, blank=True, null=True)
    section = models.PositiveSmallIntegerField(choices=NEWSPAPER_SECTIONS)
    name = models.CharField(max_length=100)
    endorsement_2016 = models.CharField(max_length=15)
    endorsement_2012 = models.CharField(max_length=15, blank=True, null=True)
    circulation = models.PositiveIntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=20, blank=True, null=True)
    url = models.URLField(blank=True, null=True, max_length=255)

    def __unicode__(self):
        return self.name

    def get_likely_endorser(self):
        name = self.name.lower()

        query = Endorser.objects.filter(
            name__iexact=name,
        )
        if query.exists():
            return query.first()

        # See if putting "The" in front (or removing it) helps.
        if name.startswith('the '):
            query = Endorser.objects.filter(
                name__iexact=name[4:],
            )
            if query.exists():
                return query.first()
        else:
            query = Endorser.objects.filter(
                name__iexact='the ' + name,
            )
            if query.exists():
                return query.first()


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
        return utils.parse_wiki_text(self.raw_text)

    def get_likely_endorser(self):
        name = self.parse_text()['endorser_name']
        if not name:
            return

        name = name.lower()

        query = Endorser.objects.filter(
            name__iexact=name,
        )
        if query.exists():
            return query.latest('pk')

        # See if putting "The" in front (or removing it) helps.
        if name.startswith('the '):
            query = Endorser.objects.filter(
                name__iexact=name[4:],
            )
            if query.exists():
                return query.first()
        else:
            query = Endorser.objects.filter(
                name__iexact='the ' + name,
            )
            if query.exists():
                return query.first()

        # See if the last name and part of the first name match.
        if ' ' in name:
            split_name = name.split(' ')
            first_name_start = split_name[0][:3]
            last_name = split_name[-1]
            if len(last_name) > 3:
                query = Endorser.objects.filter(
                    name__iendswith=last_name,
                    name__istartswith=first_name_start,
                )
                if query.exists():
                    return query.first()

    def __unicode__(self):
        return self.raw_text
