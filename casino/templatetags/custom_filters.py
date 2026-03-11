from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Позволяет получать значение из словаря в шаблоне по ключу.
    Использование: {{ mydict|get_item:key }}
    """
    return dictionary.get(key)