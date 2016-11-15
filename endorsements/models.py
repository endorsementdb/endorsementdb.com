from __future__ import unicode_literals
import shutil

from django.db import models
from django.urls import reverse
import requests

from endorsements.utils import get_twitter_client


class Event(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __unicode__(self):
        return self.name


class Category(models.Model):
    is_exclusive = models.BooleanField(default=False)
    name = models.CharField(max_length=30)
    allow_personal = models.BooleanField(default=True)
    allow_org = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'categories'


class Tag(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_personal = models.BooleanField(default=True)
    category = models.ForeignKey(Category, null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Endorser(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    is_personal = models.BooleanField(default=True)
    max_followers = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, blank=True)
    missing_image = models.BooleanField(default=True)
    current_position = models.ForeignKey('Position', blank=True, null=True)

    class Meta:
        ordering = ['-max_followers']

    def __unicode__(self):
        return self.name

    def has_url(self):
        return bool(self.url)
    has_url.boolean = True

    def get_tags(self):
        return ' / '.join(tag.name for tag in self.tags.all())

    def get_current_endorsement(self):
        try:
            return self.endorsement_set.latest('quote')
        except Endorsement.DoesNotExist:
            pass

    def get_image(self):
        return '<img src="{url}" width="100" />'.format(
            url=self.get_image_url()
        )
    get_image.allow_tags = True

    def get_image_url(self):
        image_name = 'missing' if self.missing_image else self.pk
        return 'https://s3.amazonaws.com/endorsementdb.com/images/endorsers/%s.png' % image_name

    def needs_quotes(self):
        current_endorsement = self.get_current_endorsement()
        return not current_endorsement.quote.text
    needs_quotes.boolean = True

    def get_absolute_url(self):
        return reverse('view-endorser', args=[self.pk])


class AccountManager(models.Manager):
    def get_from_username(self, username, endorser=None):
        twitter_client = get_twitter_client()
        response = twitter_client.users.lookup(
            screen_name=username
        )

        for user in response:
            twitter_id = user['id_str']

            # Expand the URL to avoid the t.co/ version.
            url = user['url']
            entities = user.get('entities')
            if entities:
                url_data = entities.get('url')
                if url_data:
                    urls = url_data['urls']
                    if urls:
                        url = urls[0]['expanded_url'] or url

            try:
                account = self.get(twitter_id=twitter_id)
                account.url = url
                account.profile_image_url = user['profile_image_url']
                account.followers_count = user['followers_count']

                # If the endorser is set, update it.
                if endorser is not None:
                    account.endorser = endorser

                account.save()
            except Account.DoesNotExist:
                # Create the endorser, if not specified as an argument.
                if endorser is None:
                    endorser = Endorser.objects.create(
                        name=user['name'],
                        description=user['description'],
                        url=url,
                        is_personal=True,
                        max_followers=user['followers_count'],
                        missing_image=False,
                    )
                else:
                    endorser.missing_image = False

                    # We may need to update max_followers for the endorser.
                    if user['followers_count'] > endorser.max_followers:
                        endorser.max_followers = user['followers_count']

                    endorser.save()

                account = self.create(
                    twitter_id=twitter_id,
                    screen_name=user['screen_name'],
                    name=user['name'],
                    description=user['description'],
                    location=user['location'],
                    protected=user['protected'],
                    verified=user['verified'],
                    profile_image_url=user['profile_image_url'],
                    url=url,
                    followers_count=user['followers_count'],
                    friends_count=user['friends_count'],
                    statuses_count=user['statuses_count'],
                    endorser=endorser,
                )

                account.save_image_to_s3()

            return account


class Account(models.Model):
    objects = AccountManager()

    twitter_id = models.CharField(max_length=20, primary_key=True)

    screen_name = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)

    protected = models.BooleanField()
    verified = models.BooleanField()

    profile_image_url = models.URLField(max_length=300, null=True)
    url = models.URLField(max_length=300, blank=True, null=True)

    followers_count = models.PositiveIntegerField()
    friends_count = models.PositiveIntegerField()
    statuses_count = models.PositiveIntegerField()

    last_updated = models.DateTimeField(auto_now=True)

    endorser = models.ForeignKey(Endorser)

    class Meta:
        ordering = ['-followers_count']

    def __unicode__(self):
        return '@{username} ({name})'.format(
            username=self.screen_name,
            name=self.name
        )

    def get_large_image(self):
        return self.profile_image_url.replace('normal', '400x400')

    def get_absolute_url(self):
        return "https://twitter.com/{username}".format(
            username=self.screen_name
        )

    def get_profile_image(self):
        return '<img src="%s" height="100" />' % self.profile_image_url
    get_profile_image.allow_tags = True
    get_profile_image.short_description = 'Profile image'

    def save_image_to_s3(self):
        """TODO"""
        import boto
        s3_connection = boto.connect_s3()
        bucket = s3_connection.get_bucket('endorsementdb.com')

        url = self.get_large_image()

        response = requests.get(url, stream=True)
        with open('/tmp/profile_image.png', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
            del response

        key = bucket.new_key('images/endorsers/%d.png' % self.endorser.pk)
        key.set_contents_from_filename(out_file.name)
        key.make_public()


class Candidate(models.Model):
    endorser_link = models.OneToOneField(Endorser)
    name = models.CharField(max_length=50)
    description = models.TextField()
    color = models.CharField(max_length=6)
    still_running = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name


class Source(models.Model):
    date = models.DateField(null=True, blank=True)
    url = models.URLField(unique=True, blank=True, max_length=300)
    name = models.CharField(max_length=100, default='')

    class Meta:
        ordering = ['url', '-date']

    def get_date_display(self):
        if self.date:
            return self.date.strftime('%b %d, %Y')

    def __unicode__(self):
        return "{url} on {date}".format(
            url=self.url,
            date=self.date,
        )


class Quote(models.Model):
    context = models.TextField(null=True, blank=True)
    text = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Source)
    # Defaults to the date of the source, but can be overridden.
    date = models.DateField(null=True, blank=True)
    event = models.ForeignKey(Event, null=True, blank=True)

    def get_date_display(self):
        if self.date:
            return self.date.strftime('%b %d, %Y')

    def get_source_display(self):
        return '<a href="{url}">{name}</a>'.format(
            url=self.source.url,
            name=self.source.name or self.source.url[:30],
        )
    get_source_display.allow_tags = True

    def __unicode__(self):
        return self.text[:150]

    class Meta:
        ordering = ['date']

    def get_event_context(self):
        event = self.event
        if event:
            if self.date >= event.end_date:
                return 'After'
            elif self.date <= event.start_date:
                return 'Before'
            else:
                return 'During'
    get_event_context.short_description = 'Timing'

    def get_display(self):
        if self.context:
            if len(self.context) > 100:
                context = self.context[:100] + '...<br />'
            else:
                context = self.context + '<br />'
        else:
            context = ''

        if self.text:
            if len(self.text) > 100:
                text = self.text[:100] + '...'
            else:
                text = self.text
        else:
            text = ''

        return context + text
    get_display.short_description = 'Context + text'
    get_display.allow_tags = True


class Comment(models.Model):
    quote = models.ForeignKey(Quote)
    candidate = models.ForeignKey(Candidate)
    polarity = models.CharField(
        max_length=1,
        choices=(
            ('+', 'Positive'),
            ('-', 'Negative'),
            ('?', 'Unclear or neutral'),
        )
    )
    endorser = models.ForeignKey(Endorser, null=True, blank=True)

    def get_truncated_quote(self):
        if len(self.quote.text) > 100:
            return self.quote.text[:100] + '...'
        else:
            return self.quote.text


class Position(models.Model):
    colour = models.CharField(max_length=20, blank=True)
    past_tense_prefix = models.CharField(max_length=10, blank=True)
    present_tense_prefix = models.CharField(max_length=10, blank=True)
    suffix = models.CharField(max_length=30)
    slug = models.SlugField()
    show_on_load = models.BooleanField(default=False)

    def __unicode__(self):
        return self.get_name_display()

    def get_name_display(self):
        if self.present_tense_prefix:
            return "{present} {suffix}".format(
                present=self.present_tense_prefix,
                suffix=self.suffix
            )
        else:
            return self.suffix

    def get_present_display(self):
        if self.present_tense_prefix:
            return self.present_tense_prefix + ' ' + self.suffix
        else:
            return self.suffix

    def get_past_display(self):
        if self.past_tense_prefix:
            return self.past_tense_prefix + ' ' + self.suffix
        else:
            return self.suffix


class Endorsement(models.Model):
    endorser = models.ForeignKey(Endorser, null=True, blank=True)
    quote = models.ForeignKey(Quote)
    position = models.ForeignKey(Position)
    confirmed = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-quote']

    def get_date(self):
        return self.quote.date

    def __unicode__(self):
        return unicode(self.position)

    def get_truncated_quote(self):
        if len(self.quote.text) > 100:
            return self.quote.text[:100] + '...'
        else:
            return self.quote.text
