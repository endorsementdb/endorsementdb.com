# encoding: utf-8
from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from endorsements.models import Category, Tag
from wikipedia.models import BulkImport, ImportedEndorsement, \
                             ImportedEndorser, ImportedNewspaper, \
                             ImportedResult, ImportedRepresentative


@admin.register(BulkImport)
class BulkImportAdmin(admin.ModelAdmin):
    list_display = ('slug', 'created_at')
    list_filter = ('slug',)


class ConfirmedEndorserFilter(admin.SimpleListFilter):
    title = 'Confirmed endorser'
    parameter_name = 'is_confirmed'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no',  'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(confirmed_endorser__isnull=False)
        if self.value() == 'no':
            return queryset.filter(confirmed_endorser__isnull=True)


class HasTagsFilter(admin.SimpleListFilter):
    title = 'Endorser has tags'
    parameter_name = 'has_tags'

    def lookups(self, request, model_admin):
        return (
            ('no',  'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(confirmed_endorser__tags=None)


def confirm_endorsers(modeladmin, request, queryset):
    num_confirmed = 0
    for endorsement in queryset:
        if endorsement.confirmed_endorser is not None:
            continue

        endorser = endorsement.get_likely_endorser()
        endorsement.confirmed_endorser = endorser
        endorsement.save()
        if endorser is not None:
            num_confirmed += 1

    modeladmin.message_user(
        request,
        'Confirmed endorsers for {n} endorsements'.format(n=num_confirmed),
        messages.SUCCESS
    )


def make_personal(modeladmin, request, queryset):
    for instance in queryset:
        endorser = instance.confirmed_endorser
        if endorser:
            endorser.is_personal = True
            endorser.save()


def make_org(modeladmin, request, queryset):
    for instance in queryset:
        endorser = instance.confirmed_endorser
        if endorser:
            endorser.is_personal = False
            endorser.save()


def remove_tag(modeladmin, request, queryset):
    tag_pk = request.POST['tag']
    try:
        tag = Tag.objects.get(pk=tag_pk)
    except Tag.DoesNotExist:
        modeladmin.message_user(
            request,
            "Could not find tag with pk {tag_pk}".format(
                tag_pk=tag_pk
            ),
            messages.ERROR,
        )
        return

    for instance in queryset:
        endorser = instance.confirmed_endorser
        if endorser:
            endorser.tags.remove(tag)

    modeladmin.message_user(
        request,
        "Removed tag {tag} for {n} endorsers".format(
            tag=tag.name,
            n=queryset.count(),
        ),
        messages.SUCCESS,
    )


def add_tag(modeladmin, request, queryset):
    tag_pk = request.POST['tag']
    try:
        tag = Tag.objects.get(pk=tag_pk)
    except Tag.DoesNotExist:
        modeladmin.message_user(
            request,
            "Could not find tag with pk {tag_pk}".format(
                tag_pk=tag_pk
            ),
            messages.ERROR,
        )
        return

    failures = []
    for instance in queryset:
        endorser = instance.confirmed_endorser
        if endorser:
            name = 'blah' #endorser.name
            if endorser.is_personal:
                if tag.category.allow_personal:
                    endorser.tags.add(tag)
                    continue
            else:
                if tag.category.allow_org:
                    endorser.tags.add(tag)
                    continue
        else:
            name = u'%s' % instance
            name = 'blah'

        failures.append(name)

    modeladmin.message_user(
        request,
        "Added tag {tag} for {n} endorsers (failures: {failures})".format(
            tag=tag.name,
            n=queryset.count(),
            failures=u', '.join(failures),
        ),
        messages.SUCCESS,
    )


class EndorserActionForm(admin.helpers.ActionForm):
    tag = forms.ModelChoiceField(Tag.objects.all())


class ExcludedCategoriesFilter(admin.SimpleListFilter):
    title = 'excluded categories'
    parameter_name = 'excludedcategories'

    def lookups(self, request, model_admin):
        return [
            (category.pk, category.name)
            for category in Category.objects.all()
        ]

    def queryset(self, request, queryset):
        if self.value():
            tag_pks = [
                tag.pk
                for tag in Tag.objects.filter(category=self.value())
            ]
            return queryset.exclude(confirmed_endorser__tags__in=tag_pks)
        else:
            return queryset


@admin.register(ImportedEndorsement)
class ImportedEndorsementAdmin(admin.ModelAdmin):
    list_display = ('get_parsed_display', 'show_endorser', 'sections',
                    'get_import_date', 'is_confirmed', 'raw_text')
    list_filter = (ConfirmedEndorserFilter, HasTagsFilter,
                   ExcludedCategoriesFilter,
                  'bulk_import__slug', 'sections')
    action_form = EndorserActionForm
    actions = [add_tag, confirm_endorsers, make_personal]

    def get_import_date(self, obj):
        return obj.bulk_import.created_at

    def get_parsed_display(self, obj):
        parsed_attributes = obj.parse_text()
        if obj.confirmed_endorser:
            parsed_attributes['pk'] = obj.confirmed_endorser.pk
        else:
            parsed_attributes['pk'] = '--'
        return format_html(
            u'<h3>Name: {endorser_name}({pk})</h3>'
            u'<p>Source: <a href="{citation_url}">{citation_url}</a> '
            'on {citation_date} ({citation_name})</p>'
            u'<p>Details: {endorser_details}</p>'
            ''.format(**parsed_attributes)
        )

    def is_confirmed(self, obj):
        return obj.confirmed_endorser is not None
    is_confirmed.boolean = True

    def get_endorser(self, obj):
        return obj.confirmed_endorser or obj.get_likely_endorser()

    def show_endorser(self, obj):
        endorser = self.get_endorser(obj)
        if endorser:
            return format_html(
                u'<h3><a href="{url}">{name}</a> ({type})</h3>'
                u'<p>{description}'.format(
                    type='personal' if endorser.is_personal else 'org',
                    name=endorser.name,
                    url=endorser.get_absolute_url(),
                    description=endorser.description
                )
            )


@admin.register(ImportedResult)
class ImportedResultAdmin(admin.ModelAdmin):
    list_display = ('tag', 'candidate', 'count')


@admin.register(ImportedEndorser)
class ImportedEndorserAdmin(admin.ModelAdmin):
    pass


@admin.register(ImportedNewspaper)
class ImportedNewspaperAdmin(admin.ModelAdmin):
    list_display = ('name', 'show_endorser', 'get_section_display',
                    'city', 'state')
    actions = [confirm_endorsers]
    list_filter = (ConfirmedEndorserFilter, 'section')

    def get_endorser(self, obj):
        return obj.confirmed_endorser or obj.get_likely_endorser()

    def show_endorser(self, obj):
        endorser = self.get_endorser(obj)
        if endorser:
            return format_html(
                u'<h3><a href="{url}">{name}</a></h3><p>{description}'.format(
                    name=endorser.name,
                    url=endorser.get_absolute_url(),
                    description=endorser.description
                )
            )


class HasEndorsementsFilter(admin.SimpleListFilter):
    title = 'Has endorsements'
    parameter_name = 'has_endorsements'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no',  'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(confirmed_endorser__current_position__isnull=False)
        if self.value() == 'no':
            return queryset.filter(confirmed_endorser__current_position=None)


@admin.register(ImportedRepresentative)
class ImportedRepresentativeAdmin(admin.ModelAdmin):
    list_display = ('get_display', 'get_image', 'show_endorser', 'is_confirmed')
    list_filter = [HasEndorsementsFilter, 'party', 'state']
    action_form = EndorserActionForm
    actions = [add_tag, remove_tag, confirm_endorsers, make_personal, make_org]

    def is_confirmed(self, obj):
        return obj.confirmed_endorser is not None
    is_confirmed.boolean = True

    def get_display(self, obj):
        return format_html(
            u'<h3>{name}</h3><p>{party} - {state}'.format(
                name=obj.name,
                party=obj.party,
                state=obj.state
            )
        )

    def get_image(self, obj):
        endorser = obj.confirmed_endorser or obj.get_likely_endorser()
        if endorser:
            return endorser.get_image()
    get_image.allow_tags = True

    def show_endorser(self, obj):
        endorser = obj.confirmed_endorser or obj.get_likely_endorser()
        if endorser:
            return format_html(
                u'<h3><a href="{url}">{name}</a> ({pk})</h3>'
                u'<p>{description} - {type}</p>'
                u'<p>{tags}</p>'.format(
                    url=endorser.get_absolute_url(),
                    name=endorser.name,
                    pk=endorser.pk,
                    description=endorser.description,
                    type='personal' if endorser.is_personal else 'org',
                    tags=' / '.join(tag.name for tag in endorser.tags.all()),
                )
            )
