import os

import twitter


def get_twitter_client():
    return twitter.Twitter(
        auth=twitter.OAuth(
            os.environ.get('ACCESS_TOKEN'),
            os.environ.get('ACCESS_TOKEN_SECRET'),
            os.environ.get('CONSUMER_KEY'),
            os.environ.get('CONSUMER_SECRET'),
        )
    )
