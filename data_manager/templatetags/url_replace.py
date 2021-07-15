from django import template
from django.utils.html import mark_safe


register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Replace GET variables
    url_param is not yet in the url, it will be added with value. If it is already there,
    it will be replaced by the new value
    refer: https://stackoverflow.com/questions/2047622/how-to-paginate-django-with-other-get-variables
    """
    # GET request is a QueryDict which instances are immutable, use copy() for mutability
    query = context['request'].GET.copy()
    for kwarg in kwargs:
        try:
            query.pop(kwarg)
        except KeyError:
            pass
    query.update(kwargs)
    return mark_safe(query.urlencode())  # Mark_safe was needed due to a double encoding issue
