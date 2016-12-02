# [EndorsementDB.com]

![A database icon with red and white coloring][logo]

_Follow us on Twitter at [@endorsementdb]_

A non-partisan attempt to keep track of endorsements in the 2016 presidential
race in a way that is structured, searchable, and visual.

Imagine the contents of these Wikipedia pages, stored in a format that allows
you to filter and sort arbitrarily:

*   [Newspaper endorsements in the United States presidential election, 2016](https://en.wikipedia.org/wiki/Newspaper_endorsements_in_the_United_States_presidential_election,_2016)
*   [List of Jill Stein presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Jill_Stein_presidential_campaign_endorsements,_2016)
*   [List of Gary Johnson presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Gary_Johnson_presidential_campaign_endorsements,_2016)
*   [List of Hillary Clinton presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Hillary_Clinton_presidential_campaign_endorsements,_2016)
*   [List of Donald Trump presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Donald_Trump_presidential_campaign_endorsements,_2016)
*   [List of Evan McMullin presidential campaign endorsements, 2016](https://en.wikipedia.org/wiki/List_of_Evan_McMullin_presidential_campaign_endorsements,_2016)

We're up-to-date on endorsements added before election day. You can track our
progress at <https://endorsementdb.com/progress/wikipedia>

## Features

* Can browse endorsements from over 8000 entities (celebrities, politicians,
  newspapers, etc), including:
  * Who the endorser is, with some tags
  * Number of followers on Twitter (if any)
  * Who they endorsed or opposed (there are a number of "endorsements" that
    were more about opposing a particular candidate than endorsing any other)
  * When the endorsement was made
  * The historical context around the endorsement (e.g., right after someone
    dropped out of the race, or during a particular debate, or after a
    particular scandal)
  * A short quote indicating the flavour of the endorsement
* Can filter by:
  * Tags:
    * Orgs: publication / political org / corporation / etc
    * People: gender, party affilitation, race, occupation, govt positions
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
   endorsement-related data (it's a very large file so it might take a while)
6. Run `django manage.py loaddata wikipedia.json` to load all the data
   related to importing from Wikipedia
6. Run `python manage.py runserver` and navigate to http://localhost:8000

(I may be missing steps here -- feel free to correct this.)

### data.world

If you just want access to the raw data without having to run the app locally,
you can find CSV files containing pretty much all the endorsement data here:
<https://data.world/dellsystem/us-election-endorsements-16>

## Get involved

This is a pretty monumental undertaking, and I could use all the help I can
get. Tweet me [@endorsementdb] or send me an email at admin@endorsementdb.com
if you want to get involved in any way! Alternatively, feel free to open an
issue or send a pull request.

## About

I originally created this as a resource for voters and journalists during the
2016 election season. I envisioned a centralized way of tracking endorsements
in a structured, searchable format, complete with the context behind each
endorsement. The only things I found that even came close were the Wikipedia
pages for candidate-specific endorsements, which, while an impressive feat of
collaboration, were sorely lacking in terms of structure and context. Since I
love projects that involve classifying and structuring data, I gave the problem
a bit of thought, sketched out a schema, and built it myself.

In hindsight, it's clear that my efforts were too little, too late. I only came
up with the idea in October, and didn't get to an MVP until less than a week
before election day. What's more, by the time election day rolled around, I
hadn't even imported half of all the endorsements listed in the Wikipedia
articles. I still shared it with friends and reached out to political
journalists, but I knew I had a lot of work to do to to achieve my original
goals, and there just wasn't enough time before the election.

Election day came and went. Like many other observers, I was absolutely floored
by the results. In fact, I was probably more surprised than the average
observer -- during the preceding weeks, I had voluntarily submerged myself in
a sea of endorsements, one whose overall tint was definitively blue. I
believed that the overwhelming volume of endorsements for Hillary Clinton,
combined with the lackluster conviction of many of the endorsements for Donald
Trump, meant that there was only one possible outcome for the election.

Well -- spoiler alert -- I was wrong. I joined the ranks of many journalists,
pundits, and politically-engaged observers who looked at the data and concluded
that Hillary Clinton would win in a landslide. What did we all miss? I'll spare
you my personal feelings about the election (though I'm sure you can infer them
from my [tweets][@dellsystem]), but in the aftermath, I coped the only way I
knew how: I went back to the data. I continued importing endorsements and
exploring new ways of understanding them. Despite my hypothesis being shattered,
I still believed there was _some_ value in endorsements. I just needed to
figure out what.

So now what? Since the election is over, the purpose of this project is less
about providing a resource for voters, and more about providing an open
platform for post-election analysis. I've already started investigating some
open-ended questions, like the [correlation between endorsements and votes in
each state][stats_states] and the [breakdown of endorsements by race and
gender for each candidate][stats_tags] (which I will be writing about in more
detail soon). And there are so many other things I want to look into but
haven't had a chance to start working on yet:

* How do newspaper endorsements for the two major candidates differ in tone,
  style, mood, content? What are the common misgivings and positives expressed
  for each candidate? (This would require doing analysis on the text of all the
  editorials.)
* What about the same analysis as above, but applied to what _people_ have said
  about each candidates? Clearly the data here will be more pithy and less
  edited, especially since many endorsements were sourced purely from Twitter
  or Instagram, but there might be some interesting trends.
* Did endorsing, opposing, or un-endorsing Trump (or Clinton) hurt anyone's
  chances of winning a seat in the House or Senate? I read an article about
  how certain Republican Senators who had un-endorsed Trump were subsequently
  "punished" by their electorate, resulting in them losing their re-election
  campaigns. How salient is this trend, and can it be applied to the House as
  well? (This would require data on the results of the House and Senate races.)
* Why did some Republicans decide to support Trump while others either declined
  to do so or later retracted their endorsement? Are there trends by gender,
  race, employment history, age, veteran status? (This may require hunting down
  a list of those who _didn't_ endorse Trump, as those aren't usually found on
  the relevant Wikipedia page and thus are sometimes missing from the database.)
* The general impact of endorsements on voters: this one is the most
  open-ended, and I'm not even sure how I'd measure it, but it's something
  I think about a lot.

If any of these questions are intriguing to you -- or if you have other ideas
that can be explored using endorsement data -- please, get in touch with me at
<admin@endorsementdb.com>! Of course, you can always use the website or clone
this repository on your own, but if you have an endorsement-related hypothesis to
test, I'd be more than happy to help you however I can.

In the future, I'd love for this project to be a sort of public record for
endorsements, with a crowd-sourcing component so I don't have to add every
endorsement on my own. I also have some grandiose ideas about transparency and
accountability when it comes to political endorsements, especially when it
comes to elected officials, but that's for another day.

Thanks for reading. If you have feedback, I'm all ears:
<admin@endorsementdb.com>

## Credits

Built by [@dellsystem], with contributions from [@tlornewr]. Released under
the MIT license.

Hosting and development sponsored by [Macromeasures]. (We're a startup focused
on extracting meaning out of social data, with applications in politics and
beyond.)

[logo]: https://s3.amazonaws.com/endorsementdb.com/images/endorsementdb.png "Please excuse the cheesiness of this logo"
[EndorsementDB.com]: http://endorsementdb.com
[@endorsementdb]: https://twitter.com/endorsementdb
[Macromeasures]: https://macromeasures.com
[@dellsystem]: https://twitter.com/dellsystem
[@tlornewr]: https://twitter.com/tlornewr
[SECRET_KEY]: https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-SECRET_KEY
[use sqlite]: https://docs.djangoproject.com/en/1.10/ref/settings/#databases
[stats_states]: http://endorsementdb.com/stats/states
[stats_tags]: http://endorsementdb.com/stats/tags
