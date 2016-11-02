import shutil

import boto
from django.core.management.base import BaseCommand, CommandError
import requests

from endorsements.models import Account


class Command(BaseCommand):
    help = 'Save images for all accounts'

    def add_arguments(self, parser):
        parser.add_argument('usernames', nargs='+')

    def handle(self, *args, **options):
        s3_connection = boto.connect_s3()
        bucket = s3_connection.get_bucket('endorsementdb.com')

        usernames = options['usernames']
        for username in usernames:
            account = Account.objects.get_from_username(username)
            endorser = account.endorser

            url = account.get_large_image()
            print url, endorser.name

            response = requests.get(url, stream=True)
            with open('/tmp/profile_image.png', 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
                del response

            key = bucket.new_key('images/endorsers/%d.png' % endorser.pk)
            key.set_contents_from_filename(out_file.name)
            key.make_public()
