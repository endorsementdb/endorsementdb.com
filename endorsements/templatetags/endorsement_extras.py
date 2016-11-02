from django import template


register = template.Library()


@register.filter(name='shorten')
def shorten(n):
    """Takes in an integer (over a thousand) and shortens it by using K or M.
    Examples:
    * 1,234,567 becomes 1.2M
    * 12,345 becomes 12K
    * 99,999,999 becomes 99M
    """
    if n > 10000000:
        return '%dM' % round(n / 1000000)
    elif n > 1000000:
        # It's between 1 and 10 million. Include the decimal point.
        return '%.1fM' % round(n / 1000000., 2)
    elif n > 1000:
        pre_decimal = int(round(n / 1000))
        return "%dK" % pre_decimal
    else:
        return str(n)
