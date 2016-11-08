import collections

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from endorsements.forms import EndorserForm, EndorsementFormWithoutPosition
from endorsements.models import Account, Endorser, Position, Source, Quote, \
                                Endorsement
from wikipedia.models import BulkImport, ImportedEndorsement


SLUG_MAPPING = {
    'List_of_Gary_Johnson_presidential_campaign_endorsements,_2016': 'johnson',
    'List_of_Jill_Stein_presidential_campaign_endorsements,_2016': 'stein',
    'List_of_Evan_McMullin_presidential_campaign_endorsements,_2016': 'mcmullin',
    'List_of_Donald_Trump_presidential_campaign_endorsements,_2016': 'trump',
    'List_of_Hillary_Clinton_presidential_campaign_endorsements,_2016': 'clinton',
}
def progress_index(request):
    slug_counts = collections.defaultdict(collections.Counter)
    for e in ImportedEndorsement.objects.all().prefetch_related('bulk_import'):
        slug = e.bulk_import.slug
        if e.confirmed_endorser:
            slug_counts[slug]['confirmed'] += 1
        else:
            if e.notes:
                slug_counts[slug]['unverifiable'] += 1
            else:
                slug_counts[slug]['unconfirmed'] += 1
        slug_counts[slug]['imported'] += 1

    positions = []
    for slug in slug_counts:
        position_slug = SLUG_MAPPING[slug]
        position = Position.objects.get(slug=position_slug)
        endorsers = Endorser.objects.filter(endorsement__position=position)
        missing_endorsers = endorsers.filter(importedendorsement=None)

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
            'name': position.get_present_display(),
            'last_checked': last_import.created_at,
            'slug': slug,
            'num_confirmed': slug_counts[slug]['confirmed'],
            'num_unconfirmed': num_unconfirmed,
            'num_unverifiable': slug_counts[slug]['unverifiable'],
            'num_imported': num_imported,
            'num_missing': missing_endorsers.count(),
            'num_endorsements': endorsers.count(),
            'progress': progress,
        })

    context = {
        'positions': positions,
    }
    return render(request, 'progress_index.html', context)


def progress_missing(request, slug):
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
    query = ImportedEndorsement.objects.filter(
        bulk_import__slug=slug,
    )
    position = Position.objects.get(slug=SLUG_MAPPING[slug])

    imported = []
    if mode == 'already':
        title = 'Already imported'
        query = query.filter(confirmed_endorser__isnull=False)
        for obj in query.order_by('-confirmed_endorser_id'):
            endorser = obj.confirmed_endorser
            endorsements = endorser.endorsement_set.filter(
                position=position
            )
            imported.append({
                'endorsements': endorsements,
                'confirmed': True,
                'endorser': endorser,
                'attributes': obj.parse_text(),
                'raw_text': obj.raw_text,
                'sections': obj.sections,
                'notes': obj.notes,
                'pk': obj.pk,
            })
    elif mode == 'notyet':
        title = 'Not yet imported'
        query = query.filter(confirmed_endorser__isnull=True)
        for obj in query:
            endorser = obj.get_likely_endorser()
            imported.append({
                'endorsements': [],
                'confirmed': False,
                'endorser': endorser,
                'attributes': obj.parse_text(),
                'raw_text': obj.raw_text,
                'sections': obj.sections,
                'notes': obj.notes,
                'pk': obj.pk,
            })
    else:
        raise Http404

    context = {
        'slug': slug,
        'title': title,
        'imported': imported,
        'position': position,
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

    if not endorsement_form.is_valid():
        messages.add_message(
            request,
            messages.ERROR,
            'Invalid endorseMENT form: {}'.format(endorsement_form.errors),
        )
        return redirect('confirm-next')

    likely_endorser = imported_endorsement.get_likely_endorser()
    if likely_endorser:
        endorser = likely_endorser
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
    try:
        source = Source.objects.get(
            url=endorsement_form.cleaned_data['source_url']
        )
    except Source.DoesNotExist:
        source = Source.objects.create(
            date=endorsement_form.cleaned_data['date'],
            url=endorsement_form.cleaned_data['source_url'],
            name=endorsement_form.cleaned_data['source_name']
        )

    quote = Quote.objects.create(
        context=endorsement_form.cleaned_data['context'],
        text=endorsement_form.cleaned_data['quote'],
        source=source,
        date=endorsement_form.cleaned_data['date'],
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


@staff_member_required
def confirm_next(request):
    # Find the next imported endorsement to confirm.
    query = ImportedEndorsement.objects.filter(
        confirmed_endorser=None,
        notes=None
    )
    if not query.count():
        messages.add_message(
            request,
            messages.ERROR,
            'No more imported endorsements to confirm',
        )
        return redirect('progress-index')

    endorsement = query.first()
    attributes = endorsement.parse_text()
    endorser_form = EndorserForm(initial={
        'name': attributes['endorser_name'],
        'description': attributes['endorser_details'],
        'is_personal': True,
    })

    endorsement_form = EndorsementFormWithoutPosition(initial={
        'date': attributes['citation_date'],
        'source_url': attributes['citation_url'],
        'source_name': attributes['citation_name'],
    })

    slug = endorsement.bulk_import.slug
    position = Position.objects.get(slug=SLUG_MAPPING[slug])

    name = attributes['endorser_name']

    context = {
        'endorsement': endorsement,
        'endorser_form': endorser_form,
        'endorsement_form': endorsement_form,
        'name': name,
        'source_url': attributes['citation_url'],
        'position': position,
        'likely_endorser': endorsement.get_likely_endorser(),
    }

    return render(request, 'confirm_next.html', context)
