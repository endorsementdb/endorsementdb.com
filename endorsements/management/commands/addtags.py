from django.core.management.base import BaseCommand, CommandError

from endorsements.models import Tag, Endorser


class Command(BaseCommand):
    help = 'Bulk import all the newspaper endorsements'

    def add_arguments(self, parser):
        parser.add_argument('endorser_pk', type=int)
        parser.add_argument('tags', nargs='+')
        parser.add_argument(
            '--remove',
            action='store_true',
            dest='remove',
            default=False,
            help="Remove the specified tags",
        )

    def handle(self, *args, **options):
        endorser = Endorser.objects.get(pk=options['endorser_pk'])
        print "Adding tags for ", endorser.name
        print "Currently has", [t.name for t in endorser.tags.all()]
        for tag_name in options['tags']:
            tag = Tag.objects.get(name=tag_name)
            if options['remove']:
                endorser.tags.remove(tag)
                print "REMOVING ------",
            else:
                endorser.tags.add(tag)
            print tag_name
        print "=========="
        print "Now", [t.name for t in endorser.tags.all()]
