import collections

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from endorsements.forms import EndorserForm, EndorsementFormWithoutPosition, \
                               EndorsementForm
from endorsements.models import Account, Endorser, Position, Source, Quote, \
                                Endorsement, Tag, Candidate
from wikipedia.models import BulkImport, ImportedEndorsement, \
                             NEWSPAPER_SLUG, ImportedNewspaper, \
                             ImportedResult


SLUG_MAPPING = {
    'List_of_Gary_Johnson_presidential_campaign_endorsements,_2016': 'johnson',
    'List_of_Jill_Stein_presidential_campaign_endorsements,_2016': 'stein',
    'List_of_Evan_McMullin_presidential_campaign_endorsements,_2016': 'mcmullin',
    'List_of_Donald_Trump_presidential_campaign_endorsements,_2016': 'trump',
    'List_of_Hillary_Clinton_presidential_campaign_endorsements,_2016': 'clinton',
}
@never_cache
def progress_index(request):
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
    return render(request, 'progress_index.html', context)


def progress_missing(request, slug):
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
    return render(request, 'progress_missing.html', context)


def progress_list(request, slug, mode):
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
    return render(request, 'progress_list.html', context)


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
            return redirect('confirm-next')
    else:
        if not endorser_form.is_valid():
            messages.add_message(
                request,
                messages.ERROR,
                'Invalid endorser form: {}'.format(endorser_form.errors),
            )
            return redirect('confirm-next')

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
        return redirect('confirm-next')

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

    return redirect('confirm-next')


@never_cache
@staff_member_required
def confirm_next(request):
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
        return redirect('progress-index')

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

    return render(request, 'confirm_next.html', context)


@never_cache
@staff_member_required
def newspaper_next(request):
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
        return redirect('progress-index')

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

    return render(request, 'confirm_newspaper.html', context)


@staff_member_required
@require_POST
def newspaper_add(request, pk):
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

    return redirect('newspaper-next')


@never_cache
def results(request):
    candidates = list(
        Candidate.objects.filter(still_running=True).order_by('pk')
    )

    cache_key = 'state_results'
    cached_values = cache.get(cache_key)
    if cached_values is None:
        position_slugs = {}
        for candidate in candidates:
            position_slugs[candidate.pk] = (
                candidate.name.split(' ')[-1].lower()
            )

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
                    current_position__slug=position_slugs[candidate.pk],
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
                current_position__slug__in=position_slugs.values(),
            ).prefetch_related('current_position')
            position_counter = collections.Counter()
            for endorser in other_endorsements:
                position = endorser.current_position
                if position:
                    position_counter[position.pk] += 1

            other_positions = []
            for position in Position.objects.exclude(slug__in=position_slugs.values()):
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
    return render(request, 'results.html', context)
