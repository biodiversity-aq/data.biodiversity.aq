from django import template
from collections import OrderedDict
import re


register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get value by key from dictionary
    :param dictionary: a python dictionary
    :param key: a key of dictionary
    :return: value of the key from dictionary
    """
    return dictionary.get(key)

