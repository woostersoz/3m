from django.contrib.humanize.templatetags.humanize import intcomma
from django import template
import locale

locale.setlocale(locale.LC_ALL, 'en_US.utf8')
register = template.Library()


@register.filter(name='currency') 
def currency(amount):
    return locale.currency(amount, grouping=True)
    #amount = round(float(amount), 2)
    #return "$ %s%s" % (intcomma(int(amount)), ("0.2%f" % amount)[-3:])