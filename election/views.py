import collections
import json
import random

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from endorsements.forms import EndorsementForm, SourceForm, \
                               EndorsementFormWithoutPosition, \
                               PersonalTagForm, EndorserForm, \
                               OrganizationTagForm, \
                               TagFilterForm
from endorsements.models import Account, Endorser, Candidate, Source, Quote, \
                                Tag, Endorsement, Category, Position
from endorsements.templatetags.endorsement_extras import shorten
from wikipedia.models import BulkImport, ImportedEndorsement, NEWSPAPER_SLUG, \
                             ImportedNewspaper, ImportedResult, \
                             ImportedRepresentative, ElectoralVotes


def search_endorsers(request):
    query = request.GET.get('q')
    endorsers = []
    endorser_pks = set()
    if query:
        # First find the endorsers whose names start with this query.
        results = Endorser.objects.filter(name__istartswith=query)
        for endorser in results[:5]:
            endorser_pks.add(endorser.pk)
            endorsers.append(endorser)

        if results.count() < 5:
            results = Endorser.objects.filter(name__icontains=query)
            for endorser in results:
                if endorser.pk in endorser_pks:
                    continue

                endorsers.append(endorser)
                if len(endorsers) == 5:
                    break

    return JsonResponse({
        'endorsers': [{'pk': e.pk, 'name': e.name} for e in endorsers],
    })


def get_endorsers(filter_params, sort_params):
    filters = {}
    mode = filter_params.get('mode')
    if mode == 'personal':
        filters['is_personal'] = True
    elif mode == 'organization':
        filters['is_personal'] = False

    candidate = filter_params.get('candidate')
    show_extra_positions = False
    if candidate:
        try:
            position = Position.objects.get(slug=candidate)
            filters['current_position'] = position
            # If this position is one of the extra positions, make sure those
            # are visible on page load.
            show_extra_positions = not position.show_on_load
        except Position.DoesNotExist:
            pass

    if filters:
        endorser_query = Endorser.objects.filter(**filters)
    else:
        endorser_query = Endorser.objects.all()

    # Tags can't be placed in the filters dictionary because we may have to do
    # multiple filters.
    tags = filter_params.get('tags')
    if type(tags) == list and tags:
        for tag_pk in tags:
            endorser_query = endorser_query.filter(tags=tag_pk)

    sort_value = sort_params.get('value')
    sort_key = None
    if sort_value == 'most':
        sort_key = '-max_followers'
    elif sort_value == 'least':
        sort_key = 'max_followers'
    elif sort_value == 'newest':
        sort_key = 'endorsement'
    elif sort_value == 'oldest':
        sort_key = '-endorsement'
    elif sort_value == 'az':
        sort_key = 'name'
    elif sort_value == 'za':
        sort_key = '-name'

    if sort_key:
        endorser_query = endorser_query.order_by(sort_key).distinct()

    category_names = {}
    for tag in Tag.objects.all().prefetch_related('category'):
        category_names[tag.pk] = tag.category.name

    positions = {}

    # Figure out which endorsers are also candidates.
    candidate_endorser_pks = set()
    for candidate in Candidate.objects.values('endorser_link'):
        candidate_endorser_pks.add(candidate['endorser_link'])

    endorser_query = endorser_query.prefetch_related(
        'tags'
    ).prefetch_related(
        'endorsement_set__position'
    ).prefetch_related(
        'endorsement_set__quote'
    ).prefetch_related(
        'endorsement_set__quote__source'
    ).prefetch_related(
        'endorsement_set__quote__event'
    ).prefetch_related(
        'account_set'
    )
    endorsers = []
    stats = collections.defaultdict(collections.Counter)
    position_totals = collections.Counter()
    for i, endorser in enumerate(endorser_query):
        stats['count']['endorsers'] += 1
        tags = []
        for tag in endorser.tags.all():
            tags.append((tag.name, tag.pk))
            tag_name = '{category} - {name}'.format(
                category=tag.category.name,
                name=tag.name
            )
            stats['tags'][tag_name] += 1

        endorsements = []
        previous_position = None
        position_pks = set()
        for i, endorsement in enumerate(endorser.endorsement_set.all()):
            # Ignore a position if it's the same as the previous one.
            position = endorsement.position
            if i == 0:
                display = position.get_present_display()
                stats['positions'][display + ' (currently)'] += 1
                stats['count']['endorsements'] += 1
            else:
                display = position.get_past_display()
                if position != previous_position:
                    stats['positions'][display] += 1
                    stats['count']['endorsements'] += 1

            quote = endorsement.quote
            source = quote.source
            event = quote.event
            if event:
                if event.start_date == event.end_date:
                    event_dates = event.start_date.strftime('%b %d, %Y')
                else:
                    event_dates = '{start} to {end}'.format(
                        start=event.start_date.strftime('%b %d, %Y'),
                        end=event.end_date.strftime('%b %d, %Y')
                    )
            else:
                event_dates = None

            endorsements.append({
                'c': endorsement.position.colour,
                'di': display,
                'q': quote.text,
                'cx': quote.context,
                'ecx': quote.get_event_context(),
                'e': event.name if event else '',
                'ed': event_dates,
                'da': quote.get_date_display(),
                'su': source.url,
                'sd': source.get_date_display(),
                'sn': source.name,
            })

        position_totals['all'] += 1
        if endorser.current_position:
            position = endorser.current_position
        else:
            endorsement = endorser.get_current_endorsement()
            if endorsement:
                position = endorsement.position
            else:
                position = None

        if position:
            position_totals[position.pk] += 1

        accounts = []
        max_followers = 0
        for account in endorser.account_set.all():
            if account.followers_count > max_followers:
                max_followers = account.followers_count

            accounts.append({
                'u': account.screen_name,
                'n': shorten(account.followers_count),
            })

        if max_followers > 0:
            stats['followers']['total'] += max_followers
            stats['followers']['count'] += 1

        # Don't bother checking if it's a candidate unless there are no
        # endorsements.
        is_candidate = False
        if not endorsements and endorser.pk in candidate_endorser_pks:
            is_candidate = True

        description = endorser.description
        if description:
            if len(description) > 80:
                description = description[:80] + '...'
        else:
            description = 'No description'

        endorsers.append({
            'p': endorser.pk,
            'n': endorser.name,
            'u': endorser.url,
            'd': description,
            't': tags,
            'e': endorsements,
            'a': accounts,
            'c': is_candidate,
            'i': 'missing' if endorser.missing_image else endorser.pk,
        })

    if not stats['followers']:
        stats['followers']['total'] = 0
        stats['followers']['count'] = 0

    positions = [
        {
            'name': 'All',
            'slug': 'all',
            'colour': 'grey',
            'count': position_totals['all'],
        }
    ]
    extra_positions = []
    position_query = Position.objects.annotate(count=Count('endorser'))
    for position in position_query.order_by('-count'):
        if position.show_on_load:
            to_append_to = positions
        else:
            to_append_to = extra_positions

        if position.present_tense_prefix == 'Endorses':
            name = position.suffix
        else:
            name = position.get_past_display()

        to_append_to.append({
            'name': name,
            'slug': position.slug,
            'colour': position.colour,
            'count': position_totals[position.pk],
        })

    return {
        'endorsers': endorsers,
        'stats': stats,
        'positions': positions,
        'extra_positions': extra_positions,
        'show_extra_positions': show_extra_positions,
    }


@csrf_exempt
def get_tags(request):
    category_tags = collections.defaultdict(list)
    for tag in Tag.objects.all():
        category_tags[tag.category.pk].append({
            'name': tag.name,
            'pk': tag.pk,
        })

    org_tags = []
    personal_tags = []
    for category_pk in category_tags:
        category = Category.objects.get(pk=category_pk)
        tag = {
            'name': category.name,
            'tags': category_tags[category_pk],
            'exclusive': category.is_exclusive,
        }
        if category.allow_org:
            org_tags.append(tag)
        if category.allow_personal:
            personal_tags.append(tag)

    return JsonResponse({
        'org': org_tags,
        'personal': personal_tags,
    })


@require_POST
@csrf_exempt
def get_endorsements(request):
    params = None
    if request.body:
        try:
            params = json.loads(request.body)
        except ValueError:
            pass

    if params is not None:
        filter_params = params.get('filter')
        if not filter_params or type(filter_params) != dict:
            return JsonResponse({
                'error': True,
                'message': 'Need "filter" key with a dict value',
            })

        sort_params = params.get('sort')
        if not sort_params or type(sort_params) != dict:
            return JsonResponse({
                'error': True,
                'message': 'Need "sort" key with a dict value',
            })
    else:
        filter_params = {}
        sort_params = {}

    params_string = (
        'query_{sort_by}_{sort_value}_{mode}_{candidate}_{tags}'
    ).format(
        sort_by=sort_params.get('by', 'followers'),
        sort_value=sort_params.get('value', 'most'),
        mode=filter_params.get('mode', 'none'),
        candidate=filter_params.get('candidate', 'all'),
        tags=','.join(sorted(map(str, filter_params.get('tags', [])))),
    )

    try:
        skip = int(request.GET.get('skip', 0))
    except ValueError:
        skip = 0

    results = cache.get(params_string)
    if results is None:
        results = get_endorsers(filter_params, sort_params)
        cache.set(params_string, results, 60 * 60)

    # For pagination.
    results['endorsers'] = results['endorsers'][skip:skip + 12]

    return JsonResponse(results)


def browse(request):
    positions = Position.objects.all().annotate(
        num_endorsers=Count('endorsement__endorser')
    )
    counts = {}
    for position in positions:
        if position.slug:
            counts[position.slug] = position.num_endorsers
    counts['total'] = Endorser.objects.count()

    context = {
        'counts': counts,
    }
    return render(request, 'endorsers/browse.html', context)


@require_POST
def add_endorser(request):
    username = request.POST.get('username')

    account = Account.objects.get_from_username(username)
    if account is None:
        messages.add_message(
            request,
            messages.ERROR,
            u'Could not get user for {username}'.format(
                username=username
            )
        )

    # Redirect to the page for editing the endorser object.
    return redirect('view-endorser', pk=account.endorser.pk)


@never_cache
def view_endorser(request, pk):
    endorser = get_object_or_404(Endorser, pk=pk)
    endorsement_form = EndorsementForm()

    imported_endorsements = ImportedEndorsement.objects.filter(
        confirmed_endorser=endorser
    )
    imported_representatives = ImportedRepresentative.objects.filter(
        confirmed_endorser=endorser
    )

    context = {
        'endorser': endorser,
        'endorsement_form': endorsement_form,
        'imported_endorsements': imported_endorsements,
        'imported_representatives': imported_representatives,
    }

    return render(request, 'endorsers/view.html', context)


@staff_member_required
@require_POST
def add_account(request, pk):
    endorser = get_object_or_404(Endorser, pk=pk)
    username = request.POST.get('username')
    account = Account.objects.get_from_username(username, endorser=endorser)
    if account:
        messages.add_message(
            request,
            messages.SUCCESS,
            u'Added the account @{username}'.format(
                username=username
            )
        )

    return redirect('view-endorser', pk=pk)


@require_POST
def add_endorsement(request, pk):
    endorser = get_object_or_404(Endorser, pk=pk)

    form = EndorsementForm(request.POST)
    if not form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            u'Not valid form'
        )
        return redirect('view-endorser', pk=pk)

    # First, create the source, or get it if it already exists.
    source_url = form.cleaned_data['source_url']
    source_date = form.cleaned_data['date']
    source_name = form.cleaned_data['source_name']
    try:
        source = Source.objects.get(url=source_url)
    except Source.DoesNotExist:
        source = Source.objects.create(
            date=source_date,
            url=source_url,
            name=source_name
        )

    quote_text = form.cleaned_data['quote']
    quote_context = form.cleaned_data['context']
    quote_event = form.cleaned_data['event']
    try:
        quote = Quote.objects.get(
            source=source,
            text=quote_text,
        )
    except Quote.DoesNotExist:
        quote = Quote.objects.create(
            source=source,
            text=quote_text,
            context=quote_context,
            date=source_date,
            event=quote_event,
        )

    position = form.cleaned_data['position']
    endorsement = Endorsement.objects.create(
        position=position,
        endorser=endorser,
        quote=quote,
        confirmed=request.user.is_staff,
    )

    messages.add_message(
        request,
        messages.SUCCESS,
        u'Added endorsement',
    )

    return redirect('view-endorser', pk=pk)


def random_endorser(request):
    endorser_count = Endorser.objects.count()
    random_endorser_index = random.randint(0, endorser_count - 1)
    random_endorser = Endorser.objects.all()[random_endorser_index]

    context = {
        'endorser': random_endorser,
    }
    return render(request, 'endorsers/random.html', context)


# category name: is personal
CATEGORY_NAMES = {
    'Gender': True,
    'Race/ethnicity': True,
    'Organizations': False,
}
def stats_tags(request):
    candidates = list(
        Candidate.objects.filter(still_running=True).order_by('pk')
    )
    positions = [
        candidate.position.pk for candidate in candidates
    ]

    categories = []
    for category_name, is_personal in CATEGORY_NAMES.iteritems():
        category = Category.objects.get(name=category_name)
        category_candidates = []
        for candidate in candidates:
            position = candidate.position
            endorsers = Endorser.objects.filter(
                is_personal=is_personal,
                current_position=position
            )
            category_endorsers = endorsers.filter(
                tags__category=category
            ).distinct()

            percent_reporting = (
                category_endorsers.count() / float(endorsers.count()) * 100
            )
            category_candidates.append({
                'num_tagged': category_endorsers.count(),
                'percent_reporting': percent_reporting
            })

        # The Other column.
        endorsers = Endorser.objects.exclude(current_position__in=positions)
        category_endorsers = endorsers.filter(
            is_personal=is_personal,
            tags__category=category
        )

        percent_reporting = (
            category_endorsers.count() / float(endorsers.count()) * 100
        )
        category_candidates.append({
            'num_tagged': category_endorsers.count(),
            'percent_reporting': percent_reporting
        })

        # Now get the tag-specific stats
        category_tags = []
        for tag in category.tag_set.all():
            tag_candidates = []
            for candidate in candidates:
                position = candidate.position
                endorsers = Endorser.objects.filter(
                    current_position=position,
                    is_personal=is_personal,
                )
                tag_endorsers = endorsers.filter(tags=tag)
                num_tagged = tag_endorsers.count()
                tag_candidates.append({
                    'num_tagged': num_tagged,
                })

            # The Other column.
            endorsers = Endorser.objects.exclude(current_position__in=positions)
            tag_endorsers = endorsers.filter(
                tags=tag,
                current_position=position,
            )

            tag_candidates.append({
                'num_tagged': tag_endorsers.count(),
            })

            category_tags.append({
                'name': tag.name,
                'candidates': tag_candidates,
            })

        num_endorsers = Endorser.objects.count()
        category_endorsers = Endorser.objects.filter(tags__category=category)
        num_tagged = category_endorsers.count()
        percent_reporting = num_tagged / float(num_endorsers) * 100

        categories.append({
            'name': category.name,
            'candidates': category_candidates,
            'tags': category_tags,
            'num_tagged': num_tagged,
            'percent_reporting': percent_reporting,
        })

    context = {
        'candidates': candidates,
        'categories': categories,
    }

    return render(request, 'stats/tags.html', context)


def charts(request):
    context = {}
    return render(request, 'stats/charts.html', context)


SLUG_MAPPING = {
    'List_of_Gary_Johnson_presidential_campaign_endorsements,_2016': 'johnson',
    'List_of_Jill_Stein_presidential_campaign_endorsements,_2016': 'stein',
    'List_of_Evan_McMullin_presidential_campaign_endorsements,_2016': 'mcmullin',
    'List_of_Donald_Trump_presidential_campaign_endorsements,_2016': 'trump',
    'List_of_Hillary_Clinton_presidential_campaign_endorsements,_2016': 'clinton',
}
@never_cache
def progress_wikipedia(request):
    slug_counts = collections.defaultdict(collections.Counter)
    for e in ImportedEndorsement.objects.all().prefetch_related('bulk_import'):
        slug = e.bulk_import.slug
        if e.confirmed_endorser_id:
            slug_counts[slug]['confirmed'] += 1
        else:
            if e.notes:
                slug_counts[slug]['unverifiable'] += 1
            else:
                slug_counts[slug]['unconfirmed'] += 1
        slug_counts[slug]['imported'] += 1

    positions = []
    for slug in slug_counts:
        position_slug = SLUG_MAPPING.get(slug)
        if position_slug:
            position = Position.objects.get(slug=position_slug)
            name = position.get_present_display()
            endorsers = Endorser.objects.filter(endorsement__position=position)
            missing_endorsers = endorsers.filter(importedendorsement=None)
            num_endorsers = endorsers.count()
            num_missing = missing_endorsers.count()
        else:
            position = None
            name = '--'
            num_endorsers = 0
            num_missing = 0

        num_unconfirmed = slug_counts[slug]['unconfirmed']
        num_imported = slug_counts[slug]['imported']
        if num_unconfirmed > 0:
            progress = int(
                (num_imported - num_unconfirmed) / float(num_imported) * 100
            )
        else:
            progress = 100

        last_import = BulkImport.objects.filter(slug=slug).latest('created_at')

        positions.append({
            'name': name,
            'last_checked': last_import.created_at,
            'slug': slug,
            'num_confirmed': slug_counts[slug]['confirmed'],
            'num_unconfirmed': num_unconfirmed,
            'num_unverifiable': slug_counts[slug]['unverifiable'],
            'num_imported': num_imported,
            'num_missing': num_missing,
            'num_endorsements': num_endorsers,
            'progress': progress,
        })

    num_newspapers = ImportedNewspaper.objects.count()
    num_confirmed = ImportedNewspaper.objects.filter(
        confirmed_endorser__isnull=False
    ).count()
    last_newspaper_import = BulkImport.objects.filter(
        importednewspaper__isnull=False
    ).latest('pk')

    num_missing = Endorser.objects.filter(
        importednewspaper=None,
        tags=Tag.objects.get(name='Publication')
    ).count()

    progress = num_confirmed / float(num_newspapers) * 100
    positions.append({
        'name': 'Newspaper endorsements',
        'last_checked': last_newspaper_import.created_at,
        'slug': last_newspaper_import.slug,
        'num_imported': num_newspapers,
        'num_confirmed': num_confirmed,
        'num_unconfirmed': num_newspapers - num_confirmed,
        'num_unverifiable': 0,
        'num_missing': num_missing,
        'progress': progress,
    })

    context = {
        'positions': positions,
    }
    return render(request, 'progress/wikipedia.html', context)


def progress_wikipedia_missing(request, slug):
    if slug == NEWSPAPER_SLUG:
        endorsements = Endorsement.objects.filter(
            endorser__importednewspaper=None,
            endorser__tags=Tag.objects.get(name='Publication')
        )
    else:
        position = Position.objects.get(slug=SLUG_MAPPING[slug])
        endorsements = Endorsement.objects.filter(
            position=position,
            endorser__importedendorsement=None
        )

    context = {
        'slug': slug,
        'endorsements': endorsements,
    }
    return render(request, 'progress/wikipedia_missing.html', context)


def progress_wikipedia_list(request, slug, mode):
    if slug == NEWSPAPER_SLUG:
        query = ImportedNewspaper.objects.all()
        is_newspapers = True
    else:
        is_newspapers = False
        query = ImportedEndorsement.objects.filter(
            bulk_import__slug=slug,
        )
        position = get_object_or_404(Position, slug=SLUG_MAPPING.get(slug))

    imported = []
    if mode == 'already':
        title = 'Already imported'
        query = query.filter(confirmed_endorser__isnull=False)
        query = query.prefetch_related('confirmed_endorser__endorsement_set')
        for obj in query.order_by('-confirmed_endorser_id'):
            endorser = obj.confirmed_endorser
            if is_newspapers:
                endorsements = endorser.endorsement_set.all()
                attributes = {
                    'endorser_name': obj.name,
                    'endorser_details': "{city}, {state}".format(
                        city=obj.city,
                        state=obj.state
                    ),
                    'citation_url': obj.url,
                    'citation_date': obj.date,
                    'citation_name': obj.name,
                }
                raw_text = obj.endorsement_2016
                sections = obj.get_section_display()
                notes = None
                url_name = 'admin:wikipedia_importednewspaper_change'
            else:
                endorsements = endorser.endorsement_set.filter(
                    position=position
                )
                attributes = obj.parse_text()
                raw_text = obj.raw_text
                sections = obj.sections
                notes = obj.notes
                url_name = 'admin:wikipedia_importedendorsement_change'

            imported.append({
                'endorsements': endorsements,
                'confirmed': True,
                'endorser': endorser,
                'attributes': attributes,
                'raw_text': raw_text,
                'sections': sections,
                'notes': notes,
                'pk': obj.pk,
                'url_name': url_name,
            })
    elif mode == 'notyet':
        # TODO: Handle newspapers here.
        title = 'Not yet imported'
        query = query.filter(confirmed_endorser__isnull=True)
        for obj in query:
            endorser = obj.get_likely_endorser()
            url_name = 'admin:wikipedia_importedendorsement_change'
            imported.append({
                'endorsements': [],
                'confirmed': False,
                'endorser': endorser,
                'attributes': obj.parse_text(),
                'raw_text': obj.raw_text,
                'sections': obj.sections,
                'notes': obj.notes,
                'pk': obj.pk,
                'url_name': url_name,
            })
    else:
        raise Http404

    context = {
        'slug': slug,
        'title': title,
        'imported': imported,
    }
    return render(request, 'progress/wikipedia_list.html', context)


@staff_member_required
@require_POST
def confirm_endorsement(request, pk):
    imported_endorsement = ImportedEndorsement.objects.get(pk=pk)
    slug = imported_endorsement.bulk_import.slug
    position = Position.objects.get(slug=SLUG_MAPPING[slug])

    endorser_form = EndorserForm(request.POST)
    endorsement_form = EndorsementFormWithoutPosition(request.POST)

    likely_endorser = imported_endorsement.get_likely_endorser()
    if likely_endorser:
        endorser = likely_endorser
        if endorser.endorsement_set.filter(position=position).exists():
            num_remaining = ImportedEndorsement.objects.filter(
                confirmed_endorser=None,
                notes=None,
            ).count()
            imported_endorsement.confirmed_endorser = endorser
            imported_endorsement.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                'Confirmed endorser with pk {pk}; {n} left'.format(
                    pk=endorser.pk,
                    n=num_remaining,
                ),
            )
            return redirect('confirm-endorsements')
    else:
        if not endorser_form.is_valid():
            messages.add_message(
                request,
                messages.ERROR,
                'Invalid endorser form: {}'.format(endorser_form.errors),
            )
            return redirect('confirm-endorsements')

        endorser = Endorser.objects.create(
            name=endorser_form.cleaned_data['name'],
            description=endorser_form.cleaned_data['description'],
            url=endorser_form.cleaned_data['url'],
            is_personal=endorser_form.cleaned_data['is_personal'],
            max_followers=0,
        )
        for tag in endorser_form.cleaned_data['tags']:
            endorser.tags.add(tag)

        username_1 = endorser_form.cleaned_data['twitter_username_1']
        if username_1:
            account = Account.objects.get_from_username(
                username_1,
                endorser=endorser
            )

        username_2 = endorser_form.cleaned_data['twitter_username_2']
        if username_2:
            account = Account.objects.get_from_username(
                username_2,
                endorser=endorser
            )

    if not endorsement_form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            'Invalid endorseMENT form: {}'.format(endorsement_form.errors),
        )
        return redirect('confirm-endorsements')

    try:
        source = Source.objects.get(
            url=endorsement_form.cleaned_data['source_url']
        )
    except Source.DoesNotExist:
        source = Source.objects.create(
            date=endorsement_form.cleaned_data['date'] or None,
            url=endorsement_form.cleaned_data['source_url'],
            name=endorsement_form.cleaned_data['source_name']
        )

    quote = Quote.objects.create(
        context=endorsement_form.cleaned_data['context'],
        text=endorsement_form.cleaned_data['quote'],
        source=source,
        date=endorsement_form.cleaned_data['date'] or None,
        event=endorsement_form.cleaned_data['event']
    )
    endorsement = endorser.endorsement_set.create(
        quote=quote,
        position=position,
        confirmed=True
    )
    imported_endorsement.confirmed_endorser = endorser
    imported_endorsement.save()

    num_remaining = ImportedEndorsement.objects.filter(
        confirmed_endorser=None,
        notes=None,
    ).count()

    messages.add_message(
        request,
        messages.SUCCESS,
        'Added endorser with pk {pk}; {n} left'.format(
            pk=endorser.pk,
            n=num_remaining,
        ),
    )

    return redirect('confirm-endorsements')


@never_cache
@staff_member_required
def confirm_endorsements(request):
    # Find the next imported endorsement to confirm.
    query = ImportedEndorsement.objects.filter(
        confirmed_endorser__isnull=True,
        notes=None
    )
    if not query.count():
        messages.add_message(
            request,
            messages.ERROR,
            'No more imported endorsements to confirm',
        )
        return redirect('progress-wikipedia')

    endorsement = query.latest('pk')
    attributes = endorsement.parse_text()

    source_url = attributes['citation_url']
    if source_url:
        twitter_username = source_url.partition('twitter.com/')[2]
        twitter_username = twitter_username.partition('/')[0]
    else:
        twitter_username = None

    endorser_form = EndorserForm(initial={
        'name': attributes['endorser_name'],
        'description': attributes['endorser_details'],
        'is_personal': True,
        'twitter_username_1': twitter_username,
    })

    endorsement_form = EndorsementFormWithoutPosition(initial={
        'date': attributes['citation_date'],
        'source_url': source_url,
        'source_name': attributes['citation_name'],
    })

    slug = endorsement.bulk_import.slug
    position = Position.objects.get(slug=SLUG_MAPPING[slug])

    name = attributes['endorser_name']

    likely_endorser = endorsement.get_likely_endorser()
    context = {
        'endorsement': endorsement,
        'endorser_form': endorser_form,
        'endorsement_form': endorsement_form,
        'name': name,
        'source_url': attributes['citation_url'],
        'position': position,
        'likely_endorser': likely_endorser,
        'has_endorsement': likely_endorser and likely_endorser.endorsement_set.filter(
            position=position
        ).exists(),
    }

    return render(request, 'confirm/endorsement.html', context)


@never_cache
@staff_member_required
def confirm_newspapers(request):
    # Find the next imported endorsement to confirm.
    query = ImportedNewspaper.objects.filter(
        confirmed_endorser=None
    )
    if not query.count():
        messages.add_message(
            request,
            messages.ERROR,
            'No more imported newspapers to confirm',
        )
        return redirect('progress-wikipedia')

    newspaper = query.latest('pk')

    source_url = newspaper.url
    if source_url:
        twitter_username = source_url.partition('twitter.com/')[2]
        twitter_username = twitter_username.partition('/')[0]
        # Guess the newspaper's URL based on the source URL.
        i = source_url[8:].index('/')
        endorser_url = source_url[:i + 8]
    else:
        twitter_username = None
        endorser_url = None

    description = "{type} for {city}, {state}".format(
        type=newspaper.get_section_display()[:-1],
        city=newspaper.city,
        state=newspaper.state
    )
    endorser_form = EndorserForm(initial={
        'name': newspaper.name,
        'description': description,
        'twitter_username_1': twitter_username,
        'url': endorser_url,
    })

    slug = (newspaper.endorsement_2016 or '').lower()
    try:
        position = Position.objects.get(slug=slug)
    except Position.DoesNotExist:
        position = None
    endorsement_form = EndorsementForm(initial={
        'date': newspaper.date,
        'source_url': source_url,
        'source_name': newspaper.name,
        'context': 'In an editorial endorsement',
        'position': position,
    })

    context = {
        'newspaper': newspaper,
        'endorser_form': endorser_form,
        'endorsement_form': endorsement_form,
        'name': newspaper.name,
        'source_url': source_url,
    }

    return render(request, 'confirm/newspaper.html', context)


@staff_member_required
@require_POST
def confirm_newspaper(request, pk):
    newspaper = ImportedNewspaper.objects.get(pk=pk)

    endorser_form = EndorserForm(request.POST)
    endorsement_form = EndorsementForm(request.POST)

    if not endorser_form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            'Invalid endorser form: {}'.format(endorser_form.errors),
        )
        return redirect('newspaper-next')

    if not endorsement_form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            'Invalid endorseMENT form: {}'.format(endorsement_form.errors),
        )
        return redirect('newspaper-next')

    endorser = Endorser.objects.create(
        name=endorser_form.cleaned_data['name'],
        description=endorser_form.cleaned_data['description'],
        url=endorser_form.cleaned_data['url'],
        is_personal=False,
        max_followers=0,
    )
    endorser.tags.add(Tag.objects.get(name='Publication'))

    username_1 = endorser_form.cleaned_data['twitter_username_1']
    if username_1:
        account = Account.objects.get_from_username(
            username_1,
            endorser=endorser
        )

    username_2 = endorser_form.cleaned_data['twitter_username_2']
    if username_2:
        account = Account.objects.get_from_username(
            username_2,
            endorser=endorser
        )

    try:
        source = Source.objects.get(
            url=endorsement_form.cleaned_data['source_url']
        )
    except Source.DoesNotExist:
        source = Source.objects.create(
            date=endorsement_form.cleaned_data['date'] or None,
            url=endorsement_form.cleaned_data['source_url'],
            name=endorsement_form.cleaned_data['source_name']
        )

    quote = Quote.objects.create(
        context=endorsement_form.cleaned_data['context'],
        text=endorsement_form.cleaned_data['quote'],
        source=source,
        date=endorsement_form.cleaned_data['date'] or None,
        event=endorsement_form.cleaned_data['event']
    )
    endorsement = endorser.endorsement_set.create(
        quote=quote,
        position=endorsement_form.cleaned_data['position'],
        confirmed=True
    )
    newspaper.confirmed_endorser = endorser
    newspaper.save()

    num_remaining = ImportedNewspaper.objects.filter(
        confirmed_endorser=None,
    ).count()

    messages.add_message(
        request,
        messages.SUCCESS,
        'Added newspaper with pk {pk}; {n} left'.format(
            pk=endorser.pk,
            n=num_remaining,
        ),
    )

    return redirect('confirm-newspapers')


@never_cache
def stats_states(request):
    candidates = list(
        Candidate.objects.filter(still_running=True).order_by('pk')
    )
    positions = [
        candidate.position.pk for candidate in candidates
    ]

    cache_key = 'stats_states'
    cached_values = cache.get(cache_key)
    if cached_values is None:
        candidate_counts = collections.defaultdict(collections.Counter)
        states = []

        tags = {
            'newspapers': Tag.objects.get(name='Publication'),
            'politicians': Tag.objects.get(name='Politician'),
            'senators': Tag.objects.get(name='Current Senator'),
            'representatives': Tag.objects.get(name='Current U.S. Representative'),
            'Republicans': Tag.objects.get(name='Republican Party'),
        }

        max_counts = collections.defaultdict(dict)
        for state_tag in Tag.objects.filter(category_id=8).order_by('name'):
            results = ImportedResult.objects.filter(
                tag=state_tag,
            ).prefetch_related('candidate')
            if not results.count():
                continue

            votes = {}
            for result in results:
                votes[result.candidate.pk] = result.count

            candidate_values = []
            for candidate in candidates:
                endorsements = Endorser.objects.filter(
                    current_position=candidate.position,
                    tags=state_tag,
                ).distinct()
                num_endorsements = endorsements.count()

                counts = collections.OrderedDict()
                counts['endorsements'] = num_endorsements
                counts['newspapers'] = endorsements.filter(
                    tags=tags['newspapers']
                ).count()
                counts['politicians'] = endorsements.filter(
                    tags=tags['politicians']
                ).count()
                counts['senators'] = endorsements.filter(
                    tags=tags['senators']
                ).count()
                counts['representatives'] = endorsements.filter(
                    tags=tags['representatives']
                ).count()
                counts['Republicans'] = endorsements.filter(
                    tags=tags['Republicans']
                ).count()

                for key, value in counts.iteritems():
                    if key in max_counts[candidate.pk]:
                        max_counts[candidate.pk][key] = max(
                            value, max_counts[candidate.pk][key]
                        )
                    else:
                        max_counts[candidate.pk][key] = value

                candidate_counts[candidate.pk].update(counts)
                candidate_counts[candidate.pk]['votes'] += votes[candidate.pk]
                if 'votes' in max_counts[candidate.pk]:
                    max_counts[candidate.pk]['votes'] = max(
                        max_counts[candidate.pk]['votes'], votes[candidate.pk]
                    )
                else:
                    max_counts[candidate.pk]['votes'] = votes[candidate.pk]

                candidate_values.append({
                    'votes': votes[candidate.pk],
                    'counts': [
                        (key, value, tags.get(key))
                        for key, value in counts.iteritems()
                    ],
                    'rgb': candidate.rgb,
                })

            # Figure out the opacity level for each cell in this row.
            total_votes = sum(votes.values())
            max_votes = max(votes.values())
            winning_color = None
            for candidate_value in candidate_values:
                ratio = candidate_value['votes'] / float(total_votes)
                percent = ratio * 100
                candidate_value['percent'] = percent
                candidate_value['ratio'] = '{:2.2f}'.format(ratio)
                candidate_won = candidate_value['votes'] == max_votes
                candidate_value['won'] = candidate_won
                if candidate_won:
                    winning_color = candidate_value['rgb']

            other_endorsements = Endorser.objects.filter(
                tags=state_tag,
            ).exclude(
                current_position__pk__in=positions,
            ).prefetch_related('current_position')
            position_counter = collections.Counter()
            for endorser in other_endorsements:
                position = endorser.current_position
                if position:
                    position_counter[position.pk] += 1

            other_positions = []
            for position in Position.objects.exclude(pk__in=positions):
                count = position_counter[position.pk]
                if count > 0:
                    other_positions.append({
                        'name': position.get_present_display(),
                        'count': count,
                        'slug': position.slug,
                    })

            state_counts = collections.OrderedDict()
            endorsements = Endorser.objects.filter(
                tags=state_tag,
            ).distinct()

            state_counts['endorsements'] = endorsements.count()
            state_counts['newspapers'] = endorsements.filter(
                tags=tags['newspapers']
            ).count()
            state_counts['politicians'] = endorsements.filter(
                tags=tags['politicians']
            ).count()
            state_counts['senators'] = endorsements.filter(
                tags=tags['senators']
            ).count()
            state_counts['representatives'] = endorsements.filter(
                tags=tags['representatives']
            ).count()
            state_counts['Republicans'] = endorsements.filter(
                tags=tags['Republicans']
            ).count()

            states.append({
                'pk': state_tag.pk,
                'name': state_tag.name,
                'candidates': candidate_values,
                'counts': [
                    (key, value, tags.get(key))
                    for key, value in state_counts.iteritems()
                ],
                'votes': total_votes,
                'winning_color': winning_color,
                'other_positions': other_positions,
                'num_other_positions': sum(position_counter.values())
            })

        cached_values = {
            'states': states,
            'candidate_counts': [
                (c, dict(candidate_counts[c.pk]), max_counts[c.pk])
                for c in candidates
            ],
        }
        cache.set(cache_key, cached_values)

    context = {
        'states': cached_values['states'],
        'candidates': candidates,
        'candidate_counts': cached_values['candidate_counts'],
    }
    return render(request, 'stats/states.html', context)


org_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='Organizations')
)
gender_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='Gender')
)
race_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='Race/ethnicity')
)
occupation_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='Occupation')
)
politician_tag = Tag.objects.get(name='Politician').pk
location_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='States and districts')
)
party_tags = set(
    tag.pk for tag in Tag.objects.filter(category__name='Party affiliation')
)
needs_keys = ['tags', 'org_type', 'gender', 'race', 'occupation', 'location', 'party']
IGNORED_SECTIONS = 'Endorsements > International political figures'
def progress_tagging(request):
    sections_by_page = []

    tag_names = {
        tag['pk']: tag['name'] for tag in Tag.objects.values('name', 'pk')
    }

    admin_url = reverse('admin:wikipedia_importedendorsement_changelist')

    # Keep track of the tags common to each section.
    section_tags = {}
    for slug in SLUG_MAPPING:
        section_counter = collections.defaultdict(collections.Counter)
        imports = ImportedEndorsement.objects.filter(
            bulk_import__slug=slug
        ).exclude(
            sections__startswith=IGNORED_SECTIONS
        ).prefetch_related('confirmed_endorser', 'confirmed_endorser__tags')
        for imported_endorsement in imports:
            section = imported_endorsement.sections
            section_counter[section]['total'] += 1

            endorser = imported_endorsement.confirmed_endorser
            if endorser is None:
                continue

            section_counter[section]['imported'] += 1

            tag_pks = set(tag.pk for tag in endorser.tags.all())
            if section in section_tags:
                section_tags[section] &= tag_pks
            else:
                section_tags[section] = tag_pks

            if not tag_pks:
                section_counter[section]['needs_tags'] += 1

            if endorser.is_personal:
                if not gender_tags & tag_pks:
                    section_counter[section]['needs_gender'] += 1
                if not race_tags & tag_pks:
                    section_counter[section]['needs_race'] += 1
                if not occupation_tags & tag_pks:
                    section_counter[section]['needs_occupation'] += 1
                if politician_tag in tag_pks:
                    if not location_tags & tag_pks:
                        section_counter[section]['needs_location'] += 1
                    if not party_tags & tag_pks:
                        section_counter[section]['needs_party'] += 1
            else:
                if not org_tags & tag_pks:
                    section_counter[section]['needs_org_type'] += 1

        sections = []
        for section, counter in section_counter.iteritems():
            needs = []
            show_section = False
            for needs_key in needs_keys:
                count = counter['needs_' + needs_key]
                if count > 0:
                    show_section = True
                    url = (
                        '{admin_url}?bulk_import__slug={slug}'
                        '&needs={key}'
                        '&sections={section}'
                        '&is_confirmed=yes'.format(
                            admin_url=admin_url,
                            key=needs_key,
                            section=section,
                            slug=slug,
                        )
                    )
                else:
                    url = None

                needs.append({
                    'count': count,
                    'url': url,
                })

            if not show_section:
                continue

            common_tags = [
                tag_names[tag_pk] for tag_pk in section_tags[section]
            ]
            sections.append({
                'name': section,
                'common_tags': common_tags,
                'total': counter['total'],
                'imported': counter['imported'],
                'needs': needs,
            })

        sections_by_page.append({
            'slug': slug,
            'sections': sections,
        })

    context = {
        'sections_by_page': sections_by_page,
    }
    return render(request, 'progress/tagging.html', context)


def progress_twitter(request):
    pass
