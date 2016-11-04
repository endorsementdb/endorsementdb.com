# [EndorsementDB.com]

![Please excuse the cheesiness of this logo][logo]

_Follow us on Twitter at [@endorsementdb]_

A non-partisan attempt to keep track of endorsements in the 2016 presidential
race in a way that is structured, searchable, and visual.

Imagine the contents of these Wikipedia pages, stored in a format that allows
you to filter and sort arbitrarily:

*   [Newspaper endorsements in the United States presidential election, 2016](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016)
    *   [Daily newspapers](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016#Daily_newspapers) - up to date as of November 3, 11:45PM
    *   [Weekly newspapers](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016#Weekly_newspapers) - in progress
    *   [Magazines](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016#Magazines) - up to date as of November 3, 11:45PM
    *   [College and university newspapers](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016#College_and_university_newspapers) - skipping
    *   [Endorsements by foreign periodicals](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016#Foreign_newspapers_and_magazines) - in progress
*   [List of Jill Stein presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Jill_Stein_presidential_campaign_endorsements,_2016) - up to date as of November 3, 11:45PM
*   [List of Gary Johnson presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Gary_Johnson_presidential_campaign_endorsements,_2016) - in progress
*   [List of Hillary Clinton presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Hillary_Clinton_presidential_campaign_endorsements,_2016) - in progress
*   [List of Donald Trump presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Donald_Trump_presidential_campaign_endorsements,_2016) - in progress

## Features

* Can browse endorsements from over 700 entities (celebrities, politicians,
  newspapers, etc), including:
  * Who the endorser is, with some tags
  * Number of followers on Twitter (if any)
  * Who they endorsed or opposed (there are a number of "endorsements" that
    were more about opposing a particular candidate than endorsing any other)
  * When the endorsement was made
  * The historical context around the endorsement (e.g., right after someone
    dropped out of the race, or during a particular debate)
  * A short quote indicating the flavour of the endorsement
* Can filter by:
  * Tags:
    * Orgs: publication / political org / corporation / etc
    * People: gender, party affilitation, URM, occuptation, govt positions
  * Position (which candidate they support), with hash parameter
    support (e.g., #candidate=trump)

## Setup instructions

1. Clone this repository
2. Set up a virtualenv or otherwise install the requirements with pip (`pip
   install -r requirements.txt`
3. Edit elections/settings.py to set the following variables (or set them as
   environment variables):
   * [`SECRET_KEY`][SECRET_KEY]: a random key used for securing session
   * `DB_USER`, `DB_NAME`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` according to
     your database setup (if you don't already have one, you can just [use
     sqlite]; if you want to use PostgreSQL, you'll need to install `psycopg2`)
4. Run `django manage.py migrate`
5. Run `django manage.py loaddata endorsements.json` to load all the
   endorsement-related data that I have so far
6. Run `python manage.py runserver` and navigate to http://localhost:8000

(I may be missing steps here -- feel free to correct this.)

## Get involved

This is a pretty monumental undertaking, and I could use all the help I can
get. Tweet me [@endorsementdb] or send me an email at admin@endorsementdb.com
if you want to get involved in any way! Alternatively, feel free to open an
issue or send a pull request.

## About

I decided to create this after seeing tons of endorsement-related stories pop
up over the last few weeks. While endorsements of a particular candidate are
usually picked up by that candidate's campaign and tweeted out to supporters,
or compiled into listicles like of the form "Athletes/Musicians/Actors who
support Candidate X", they are often unseen by those who don't already support
that candidate. Which is unfortunate, because in an election like this one --
where a significant number of voters haven't fully made up their mind --
endorsements can have an impact. Even if an individual endorsement doesn't
change anyone's mind, it can still provide context on _why_ people support that
candidate, which may help bridge the empathy gap in this polarized election
year.

I imagined a centralized store of endorsements for _all_ candidates, complete
with context behind each endorsement and endorser, with some sort of Twitter
integration to make it easy to filter by the people you already follow just
so you can start with the endorsements that are relevant to you. There would
have to be a flexible schema to allow people to make complex queries by
arbitrary tags, and each endorser would be associated with an image to make the
experience a little less dry. Since I couldn't find anything like this, and
since I love projects that involve classifying and structuring data, I figured
I'd try to build it myself.

(For the record, I am incredibly grateful to the maintainers of the
aforementioned Wikipedia
pages -- they make my life a lot easier -- but, given the length and format of
those pages, I wouldn't be surprised if I were the only non-maintainer who has
actually read them all the way through. While Wikipedia pages can be great for
documenting things for posterity, they aren't so great for the casual reader
who just wants the CliffNotes version but instead gets hit in the face by a
thousand bullet points and twice as many references.)

## Credits

Built by [@dellsystem], with contributions from [@tlornewr]. Released under
the MIT license.

Hosting and development sponsored by [Macromeasures]. (We're a startup focused
on extracting meaning out of social data, with applications in politics and
beyond.)

[logo]: https://s3.amazonaws.com/endorsementdb.com/images/endorsementdb.png
[EndorsementDB.com]: http://endorsementdb.com
[@endorsementdb]: https://twitter.com/endorsementdb
[Macromeasures]: https://macromeasures.com
[@dellsystem]: https://twitter.com/dellsystem
[@tlornewr]: https://twitter.com/tlornewr
[SECRET_KEY]: https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-SECRET_KEY
[use sqlite]: https://docs.djangoproject.com/en/1.10/ref/settings/#databases
