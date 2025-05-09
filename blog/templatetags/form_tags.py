from django import template
from django.utils.safestring import SafeString

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={**field.field.widget.attrs, 'class': css})
    return field  # déjà rendu

@register.filter(name='attr')
def attr(field, attr_str):
    if hasattr(field, 'as_widget'):
        key, val = attr_str.split(':', 1)
        return field.as_widget(attrs={**field.field.widget.attrs, key: val})
    return field  # déjà rendu