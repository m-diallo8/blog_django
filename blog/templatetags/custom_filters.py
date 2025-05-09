from django import template
from django.forms.boundfield import BoundField
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Ajoute une classe CSS à un champ de formulaire
    Usage: {{ form.field|add_class:"ma-classe" }}
    """
    if hasattr(value, 'field'):
        existing_class = value.field.widget.attrs.get('class', '')
        new_classes = f"{existing_class} {arg}".strip()
        value.field.widget.attrs['class'] = new_classes
        return value
    return value

@register.filter(name='attr')
def attr(value, arg):
    """
    Ajoute un attribut à un champ de formulaire
    Usage: {{ form.field|attr:"placeholder:Mon texte" }}
    """
    if hasattr(value, 'field'):
        key, val = arg.split(':', 1)
        value.field.widget.attrs[key] = val
        return value
    return value