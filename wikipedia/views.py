import collections

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from endorsements.forms import EndorserForm, EndorsementFormWithoutPosition, \
                               EndorsementForm
from endorsements.models import Account, Endorser, Position, Source, Quote, \
                                Endorsement, Tag, Candidate
from wikipedia.models import BulkImport, ImportedEndorsement, \
                             NEWSPAPER_SLUG, ImportedNewspaper, \
                             ImportedResult


