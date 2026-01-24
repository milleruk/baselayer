from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return a list"""
    if value is None:
        return []
    return value.split(delimiter)
