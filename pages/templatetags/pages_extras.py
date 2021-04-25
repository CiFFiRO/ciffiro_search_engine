from django import template

register = template.Library()


@register.filter
def diff(value, arg):
    return value - arg
