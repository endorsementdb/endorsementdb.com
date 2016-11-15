from django.core.management.base import BaseCommand, CommandError

from endorsements.models import Endorser


class Command(BaseCommand):
    help = 'Refresh the current_position field for all Endorsers'

    def handle(self, *args, **options):
        n = 0
        for i, e in enumerate(Endorser.objects.all()):
            if i % 100 == 0:
                print i
            endorsement = e.get_current_endorsement()
            if endorsement and e.current_position != endorsement.position:
                e.current_position = endorsement.position
                e.save()
                n += 1

        print "Refreshed", n
