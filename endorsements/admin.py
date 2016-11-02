from django import forms
from django.contrib import admin, messages

from endorsements.models import Account, Candidate, Endorsement, Endorser, \
                                Source, Quote, Comment, Position, Tag, \
                                Category, Event


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'screen_name', 'name', 'twitter_id', 'get_profile_image',
        'endorser'
    )


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    pass


class EndorsementInline(admin.TabularInline):
    model = Endorsement
    extra = 1


class CommentInline(admin.StackedInline):
    model = Comment
    extra = 1


class EndorserActionForm(admin.helpers.ActionForm):
    tag = forms.ModelChoiceField(Tag.objects.all())


class EndorserAdminForm(forms.ModelForm):
    class Meta:
        model = Endorser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EndorserAdminForm, self).__init__(*args, **kwargs)
        self.fields['tags'].queryset = Tag.objects.filter(
            is_personal=self.instance.is_personal
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
        if tag.is_personal == instance.is_personal:
            instance.tags.add(tag)
        else:
            failures.append(instance.name)

    modeladmin.message_user(
        request,
        "Added tag {tag} for {n} endorsers (failures: {failures})".format(
            tag=tag.name,
            n=queryset.count(),
            failures=', '.join(failures),
        ),
        messages.SUCCESS,
    )


class ExcludedTagsFilter(admin.SimpleListFilter):
    title = 'excluded tags'
    parameter_name = 'excludedtags'

    def lookups(self, request, model_admin):
        return [(tag.pk, tag.name) for tag in Tag.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.exclude(tags=self.value())
        else:
            return queryset


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
            return queryset.exclude(tags__in=tag_pks)
        else:
            return queryset


@admin.register(Endorser)
class EndorserAdmin(admin.ModelAdmin):
    action_form = EndorserActionForm
    actions = [add_tag]
    form = EndorserAdminForm
    list_filter = ('tags', 'is_personal', ExcludedTagsFilter,
                    ExcludedCategoriesFilter)
    list_display = ('name', 'get_image', 'max_followers', 'get_tags',
                    'has_url', 'needs_quotes', 'is_personal')
    inlines = [
        EndorsementInline,
        CommentInline
    ]


class QuoteInline(admin.TabularInline):
    model = Quote
    extra = 1


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('url', 'date', 'name')
    inlines = [
        QuoteInline,
    ]


class QuoteActionForm(admin.helpers.ActionForm):
    event = forms.ModelChoiceField(Event.objects.all())


def change_event(modeladmin, request, queryset):
    event_pk = request.POST['event']
    try:
        event = Event.objects.get(pk=event_pk)
    except Event.DoesNotExist:
        modeladmin.message_user(
            request,
            "Could not find event with pk {event_pk}".format(
                event_pk=event_pk
            ),
            messages.ERROR,
        )
        return

    queryset.update(event=event)

    modeladmin.message_user(
        request,
        "Added event {event} for {n} quotes".format(
            event=event.name,
            n=queryset.count(),
        ),
        messages.SUCCESS,
    )


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    action_form = QuoteActionForm
    actions = [change_event]
    list_display = ('get_display', 'get_source_display',
                    'get_event_context', 'event', 'date')
    list_filter = ('event',)
    inlines = [
        EndorsementInline,
        CommentInline,
    ]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('get_name_display', 'colour')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_personal', 'category')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_exclusive')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')


@admin.register(Endorsement)
class EndorsementAdmin(admin.ModelAdmin):
    list_display = ('endorser', 'position', 'get_truncated_quote', 'get_date')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('get_truncated_quote', 'polarity' , 'endorser', 'candidate')
