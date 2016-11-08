# encoding: utf-8
from __future__ import unicode_literals
from datetime import date

import unittest

from wikipedia.utils import parse_wiki_text, get_ref_definitions, \
                            replace_refs, split_endorsements


class __TestSplitEndorsements(unittest.TestCase):
    def runTest(self):
        actual = list(split_endorsements(self.line))
        self.assertEqual(
            self.expected,
            actual,
            "Expected {expected} for {input}; got {actual}".format(
                expected=self.expected,
                input=self.line,
                actual=actual
            )
        )


class TestSimpleSplitEndorsements(__TestSplitEndorsements):
    line = """[[Martha Wong]],<ref name="asiatrump"/> [[Wayne Christian]]<ref name="txtrump"/>"""
    expected = [
        '[[Martha Wong]],<ref name="asiatrump"/>',
        '[[Wayne Christian]]<ref name="txtrump"/>',
    ]


class __TestReplaceRefs(unittest.TestCase):
    def runTest(self):
        actual = replace_refs(self.line, self.definitions)
        self.assertEqual(
            self.expected,
            actual,
            "Expected {expected} for {input}; got {actual}".format(
                expected=self.expected,
                input=self.line,
                actual=actual
            )
        )


class TestSimpleReplaceRefs(__TestReplaceRefs):
    line = """Member of the Nevada Assembly: [[Heidi Gansert]]<ref name="nvetrump"/>"""
    definitions = {
        'nvetrump': '<ref>Blah</ref>',
    }
    expected = """Member of the Nevada Assembly: [[Heidi Gansert]]<ref>Blah</ref>"""


class TestComplexNameReplaceRefs(__TestReplaceRefs):
    line = """[[Aimee Winder Newton]], [[Salt Lake County, Utah]] councilwoman<ref name="Endorsements Oct. 19" />"""
    definitions = {
        'Endorsements Oct. 19': '<ref>blah</ref>'
    }
    expected = """[[Aimee Winder Newton]], [[Salt Lake County, Utah]] councilwoman<ref>blah</ref>"""


class TestUnquotedReplaceRefs(__TestReplaceRefs):
    line = "[[Mike Tyson]]<ref name=ATH />"
    definitions = {
        'ATH': '<ref>blah</ref>'
    }

    expected = "[[Mike Tyson]]<ref>blah</ref>"


class __TestGetRefDefinitions(unittest.TestCase):
    def runTest(self):
        actual = list(get_ref_definitions(self.raw_text))
        self.assertEqual(
            self.expected,
            actual,
            "Expected {expected} for {input}; got {actual}".format(
                expected=self.expected,
                input=self.raw_text,
                actual=actual
            )
        )


class TestQuotedRefDefinitions(__TestGetRefDefinitions):
    raw_text = """Michigan State Senators: [[Randy Richardville]],<ref name="cdmich">{{cite news|url=http://www.mlive.com/news/index.ssf/2016/08/trump_campaign_announces_michi.html|title=Trump campaign announces Michigan Congressional district chairs, county co-chairs|work=mlive.com|date=August 26, 2016}}</ref>"""
    expected = [('cdmich', """<ref name="cdmich">{{cite news|url=http://www.mlive.com/news/index.ssf/2016/08/trump_campaign_announces_michi.html|title=Trump campaign announces Michigan Congressional district chairs, county co-chairs|work=mlive.com|date=August 26, 2016}}</ref>""")]


class TestUnquotedRefDefinitions(__TestGetRefDefinitions):
    raw_text = """[[Brian France]], CEO and Chairman of [[NASCAR]]<ref name=ATH>{{cite web|url=https://www.washingtonpost.com/news/early-lead/wp/2016/05/04/a-guide-to-athletes-endorsements-of-2016-presidential-candidates/|title=A guide to sports stars’ endorsements of 2016 presidential candidates|first=Matt|last=Bonesteel|date=May 4, 2016|accessdate=May 4, 2016|work=Washington Post}}</ref>"""
    expected = [('ATH', """<ref name=ATH>{{cite web|url=https://www.washingtonpost.com/news/early-lead/wp/2016/05/04/a-guide-to-athletes-endorsements-of-2016-presidential-candidates/|title=A guide to sports stars’ endorsements of 2016 presidential candidates|first=Matt|last=Bonesteel|date=May 4, 2016|accessdate=May 4, 2016|work=Washington Post}}</ref>""")]


class TestMultipleRefDefinitions(__TestGetRefDefinitions):
    raw_text = """''[[St. Joseph News-Press]] '', St Joseph Missouri<ref name="mediaite.com"/><ref>{{cite news | url = http://www.newspressnow.com/opinion/editorials/trump-and-gop-offer-best-hope-to-lead-america/article_a19fa87b-fe91-5c33-b2a4-5cb21e72aeb5.html | title = Trump and GOP offer best hope to lead America | date = October 15, 2016 | work = [[St. Joseph News-Press]] | location = St. Joseph, Missouri | publisher = News-Press & Gazette Company | accessdate = October 25, 2016 }}</ref>"""
    expected = []



class __TestParseWikiText(unittest.TestCase):
    raw_text = ''
    expected = {}

    def runTest(self):
        actual = parse_wiki_text(self.raw_text)
        self.assertEqual(
            self.expected,
            actual,
            "Expected {expected} for {input}; got {actual}".format(
                expected=self.expected,
                input=self.raw_text,
                actual=actual
            )
        )


class TestCommaAddedLater(__TestParseWikiText):
    raw_text = (
        '[[Paul Teutul Sr.]], Co. founder of [[Orange County Choppers]]'
        '<ref>{{cite web|url=http://thehill.com/blogs/in-the-know/in-'
        'the-know/270278-american-chopper-star-endorses-trump'
        "|title='American Chopper' star endorses Trump |publisher="
        'TheHill |date= |accessdate=February 25, 2016}}</ref>'
    )
    expected = {
        'citation_url': 'http://thehill.com/blogs/in-the-know/in-the-know/270278-american-chopper-star-endorses-trump',
        'citation_date': date(2016, 2, 25),
        'citation_name': 'TheHill',
        'endorser_name': 'Paul Teutul Sr.',
        'endorser_details': 'Co. founder of Orange County Choppers',
    }


class TestMelaniaTrump(__TestParseWikiText):
    raw_text = (
        '[[Melania Trump]]<ref>{{cite news| url = '
        'http://www.cnn.com/2016/02/20/politics/melania-trump-south-'
        'carolina-trump/index.html| title = Melania speaks at Donald '
        'Trump South Carolina victory speech| website = CNN| access-date '
        '= February 29, 2016}}</ref>'
    )
    expected = {
        'citation_url': 'http://www.cnn.com/2016/02/20/politics/melania-trump-south-carolina-trump/index.html',
        'citation_date': date(2016, 2, 29),
        'citation_name': 'CNN',
        'endorser_name': 'Melania Trump',
        'endorser_details': '',
    }


class TestGeneKeady(__TestParseWikiText):
    """Multiple references."""
    raw_text = """[[Gene Keady]]<ref name=ATH /><ref name="dc-twomore">{{cite news | url = http://dailycaller.com/2016/05/03/two-more-college-basketball-legends-endorse-trump/ | title = Two More College Basketball Legends Endorse Trump | first = Christian | last = Datoc | date = 2016-05-03 | work = [[The Daily Caller]] | location = Washington, D.C. | accessdate = 2016-10-24 | quote = Former Notre Dame and Purdue men's basketball coaches Digger Phelps and Gene Keady both introduced the Republican front-runner before a Monday campaign rally in South Bend. ... "Indiana and Notre Dame and Perdue used to fight hard against each other," added Keady. "But we all now want to be united and be under the same type of safe situation in the United States and Mr. Trump is the answer to that."}}</ref>"""
    expected = {
        'endorser_name': 'Gene Keady',
        'endorser_details': '',
        'citation_url': 'http://dailycaller.com/2016/05/03/two-more-college-basketball-legends-endorse-trump/',
        'citation_date': date(2016, 5, 3),
        'citation_name': 'The Daily Caller',
    }


class TestBenStein(__TestParseWikiText):
    raw_text = """[[Ben Stein]], actor and political commentator; speechwriter for [[Richard Nixon]] and [[Gerald Ford]]<ref>{{cite news|title=Ben Stein: Trump must go|url=http://www.cbsnews.com/news/ben-stein-trump-must-go/ |access-date=October 9, 2016|work=CBS News}}</ref> (''retracted October 9, 2016'')"""
    expected = {
        'endorser_name': 'Ben Stein',
        'endorser_details': "Actor and political commentator; speechwriter for Richard Nixon and Gerald Ford (''retracted October 9, 2016'')",
        'citation_url': 'http://www.cbsnews.com/news/ben-stein-trump-must-go/',
        'citation_date': date(2016, 10, 9),
        'citation_name': 'CBS News',
    }


class TestTheDailyHerald(__TestParseWikiText):
    raw_text = """''[[Daily Herald (Utah)|Daily Herald]]'' <ref>{{Cite news|url=http://www.heraldextra.com/news/opinion/herald-editorials/herald-editorial-a-vote-for-mcmullin-is-a-vote-for/article_d5f3ca37-01ec-510c-9b02-7b71593fd0ce.html|title=Herald editorial: A vote for McMullin is a vote for change|newspaper=Daily Herald|access-date=2016-10-31}}</ref>"""
    expected = {
        'endorser_name': 'Daily Herald',
        'endorser_details': '',
        'citation_url': 'http://www.heraldextra.com/news/opinion/herald-editorials/herald-editorial-a-vote-for-mcmullin-is-a-vote-for/article_d5f3ca37-01ec-510c-9b02-7b71593fd0ce.html',
        'citation_date': date(2016, 10, 31),
        'citation_name': 'Daily Herald',
    }


class TestFloridaIndependenceParty(__TestParseWikiText):
    raw_text = """Florida Independent Party<ref>{{Cite web |url=http://ballot-access.org/2016/09/14/florida-independent-party-nominated-evan-mcmullin-for-president-but-florida-wont-accept-his-filing/ |title=Florida Independent Party Nominated Evan McMullin for President, but Florida Won’t Put Him on Ballot |work=Ballot Access News |access-date=2016-09-25}}</ref>"""
    expected = {
        'endorser_name': 'Florida Independent Party',
        'endorser_details': '',
        'citation_url': 'http://ballot-access.org/2016/09/14/florida-independent-party-nominated-evan-mcmullin-for-president-but-florida-wont-accept-his-filing/',
        'citation_name': 'Ballot Access News',
        'citation_date': date(2016, 9, 25),
    }


class TestJDVance(__TestParseWikiText):
    raw_text = """J.D. Vance, author of ''[[Hillbilly Elegy]]''<ref>https://twitter.com/JDVance1/status/790313275338526720</ref>"""
    expected = {
        'endorser_name': 'J.D. Vance',
        'endorser_details': "Author of ''Hillbilly Elegy''",
        'citation_url': 'https://twitter.com/JDVance1/status/790313275338526720',
        'citation_name': None,
        'citation_date': None,
    }


class TestWilliamFBOReilly(__TestParseWikiText):
    raw_text = """[[William F. B. O'Reilly]], The publisher of the conservative newsblog the "Blackberry Alarm Clock".<ref>[http://www.newsday.com/opinion/columnists/and-the-write-in-presidential-candidates-are-1.12561703 Newsday, Updated November 5, 2016 12:03 PM]</ref>"""
    expected = {
        'endorser_name': "William F. B. O'Reilly",
        'endorser_details': 'The publisher of the conservative newsblog the "Blackberry Alarm Clock".',
        'citation_url': 'http://www.newsday.com/opinion/columnists/and-the-write-in-presidential-candidates-are-1.12561703',
        'citation_name': None,
        'citation_date': None,
    }


class TestAmericanFreedomParty(__TestParseWikiText):
    raw_text = """[[American Freedom Party]]<ref>{{cite web | url=http://www.thedailybeast.com/articles/2016/01/11/white-power-party-swears-loyalty-to-president-trump.html | work=TheDailyBeast.com | date=January 1, 2016 | accessdate=July 18, 2016|title=White Power Party Swears Loyalty to ‘President’ Trump|author=Gideon Resnick}}</ref><ref>[http://american3rdposition.com/?p=15932 "Nationalist Pays For Radio Airtime and Robocalls to Promote Donald Trump"], American Freedom Party web page, January 8, 2016.</ref>"""
    expected = {
        'endorser_name': 'American Freedom Party',
        'endorser_details': '',
        'citation_url': 'http://www.thedailybeast.com/articles/2016/01/11/white-power-party-swears-loyalty-to-president-trump.html',
        'citation_date': date(2016, 1, 1),
        'citation_name': 'TheDailyBeast.com',
    }


class TestDiamondAndSilk(__TestParseWikiText):
    raw_text = """[[Diamond and Silk]]<ref>[https://www.youtube.com/watch?v=-piJWc_6Lqc Former Democrats Stump For Trump. Fox Business, Varney and Co.] January 8, 2016</ref>"""
    expected = {
        'endorser_name': 'Diamond and Silk',
        'endorser_details': '',
        'citation_url': 'https://www.youtube.com/watch?v=-piJWc_6Lqc',
        'citation_date': None,
        'citation_name': None,
    }


class TestBobKnight(__TestParseWikiText):
    raw_text = """[[Bob Knight]]<ref name=ATH /><ref>{{cite news | url = https://www.washingtonpost.com/news/early-lead/wp/2016/04/27/bobby-knight-calls-trump-most-prepared-man-in-history-to-run-for-president/ | title = Bobby Knight calls Trump ‘most prepared man in history’ to run for president | first = Des | last = Bieler | date = April 28, 2016 | work = [[The Washington Post]] | edition = online | accessdate = October 23, 2016 }}</ref>"""
    expected = {
        'endorser_name': 'Bob Knight',
        'endorser_details': '',
        'citation_url': 'https://www.washingtonpost.com/news/early-lead/wp/2016/04/27/bobby-knight-calls-trump-most-prepared-man-in-history-to-run-for-president/',
        'citation_date': date(2016, 4, 28),
        'citation_name': 'The Washington Post',
    }


class TestRickMoore(__TestParseWikiText):
    raw_text = """Rick Moore, mayor of [[Payson, Utah]]<ref>Katie England, [http://www.heraldextra.com/news/local/govt-and-politics/elections/evan-mcmullin-presidential-campaign-has-already-achieved-success/article_b0eb47fb-3773-5ad3-b339-74a96910c07a.html Evan McMullin: Presidential campaign has already achieved success], ''Daily Herald'' (October 31, 2016).</ref>"""
    expected = {
        'endorser_name': 'Rick Moore',
        'endorser_details': 'Mayor of Payson, Utah',
        'citation_url': 'http://www.heraldextra.com/news/local/govt-and-politics/elections/evan-mcmullin-presidential-campaign-has-already-achieved-success/article_b0eb47fb-3773-5ad3-b339-74a96910c07a.html',
        'citation_name': None,
        'citation_date': None,
    }


class TestMichaelSavage(__TestParseWikiText):
    raw_text = """[[Michael Savage]]{{efn|name=a}}<ref>{{cite web |last1=Unruh |first1=Bob |title=Trump Earns Michael Savage's Acclaim: 'Yes, I would absolutely support him' |url=http://www.wnd.com/2015/07/trump-earns-michael-savages-acclaim/ |website=WDN |accessdate=July 12, 2015 |date=July 10, 2015}}</ref>"""
    expected = {
        'endorser_name': 'Michael Savage',
        'endorser_details': '',
        'citation_url': 'http://www.wnd.com/2015/07/trump-earns-michael-savages-acclaim/',
        'citation_date': date(2015, 7, 10),
        'citation_name': 'WDN',
    }
