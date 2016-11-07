from django.contrib import admin, messages
from django.utils.html import format_html

from wikipedia.models import BulkImport, ImportedEndorsement, ImportedEndorser


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


def confirm_endorsers(modeladmin, request, queryset):
    num_confirmed = 0
    for endorsement in queryset:
        if endorsement.confirmed_endorser is not None:
            continue

        endorser = endorsement.get_likely_endorser()
        endorsement.confirmed_endorser = endorser
        endorsement.save()
        num_confirmed += 1

    modeladmin.message_user(
        request,
        'Confirmed endorsers for {n} endorsements'.format(n=num_confirmed),
        messages.SUCCESS
    )


@admin.register(ImportedEndorsement)
class ImportedEndorsementAdmin(admin.ModelAdmin):
    list_display = ('get_parsed_display', 'show_endorser', 'sections',
                    'get_import_date', 'is_confirmed', 'raw_text')
    list_filter = (ConfirmedEndorserFilter, 'bulk_import__slug')
    actions = [confirm_endorsers]

    def get_import_date(self, obj):
        return obj.bulk_import.created_at

    def get_parsed_display(self, obj):
        parsed_attributes = obj.parse_text()
        return format_html(
            u'<h3>Name: {endorser_name}</h3>'
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
                u'<h3><a href="{url}">{name}</a></h3><p>{description}'.format(
                    name=endorser.name,
                    url=endorser.get_absolute_url(),
                    description=endorser.description
                )
            )


@admin.register(ImportedEndorser)
class ImportedEndorserAdmin(admin.ModelAdmin):
    pass
