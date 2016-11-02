from django.test import TestCase

from endorsements.templatetags.endorsement_extras import shorten


class TestShortenFilter(TestCase):
    expected = {
        12345678: '12M',
        1234567: '1.2M',
        123456: '123K',
        12345: '12K',
        1234: '1K',
        123: '123',
        99999999: '99M'
    }

    def runTest(self):
        for n, expected_output in self.expected.iteritems():
            actual_output = shorten(n)
            self.assertEqual(
                actual_output,
                expected_output,
                "%d should generate %s; instead, got %s" % (
                    n,
                    expected_output,
                    actual_output
                )
            )
