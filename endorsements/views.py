import collections
import json
import random

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from endorsements.forms import EndorsementForm, SourceForm, \
                               PersonalTagForm, \
                               OrganizationTagForm, \
                               TagFilterForm
from endorsements.models import Account, Endorser, Candidate, Source, Quote, \
                                Tag, Endorsement, Category, Position
from endorsements.templatetags.endorsement_extras import shorten


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
            filters['endorsement__position'] = position
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
            stats['tags'][tag.name] += 1

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
            previous_position = position
            position_pks.add(position.pk)

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

        for position_pk in position_pks:
            position_totals[position_pk] += 1
        position_totals['all'] += 1

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

        endorsers.append({
            'p': endorser.pk,
            'n': endorser.name,
            'u': endorser.url,
            'd': endorser.description,
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
    position_query = Position.objects.annotate(count=Count('endorsement'))
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
    org_tags = []
    for tag in Tag.objects.filter(is_personal=False):
        org_tags.append({
            'name': tag.name,
            'pk': tag.pk,
        })

    category_tags = collections.defaultdict(list)
    for tag in Tag.objects.filter(is_personal=True):
        category_tags[tag.category.pk].append({
            'name': tag.name,
            'pk': tag.pk,
        })

    personal_tags = []
    for category_pk in category_tags:
        category = Category.objects.get(pk=category_pk)
        personal_tags.append({
            'name': category.name,
            'tags': category_tags[category_pk],
            'exclusive': category.is_exclusive,
        })

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

    results = cache.get(params_string)
    if results is None:
        results = get_endorsers(filter_params, sort_params)
        cache.set(params_string, results, 60 * 60)

    return JsonResponse(results)


@cache_page(60 * 15)
def index(request):
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
    return render(request, 'index.html', context)


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


def view_endorser(request, pk):
    endorser = get_object_or_404(Endorser, pk=pk)
    endorsement_form = EndorsementForm()

    context = {
        'endorser': endorser,
        'endorsement_form': endorsement_form,
    }

    return render(request, 'view.html', context)


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
    return render(request, 'random_endorser.html', context)


def charts(request):
    context = {}
    return render(request, 'charts.html', context)
