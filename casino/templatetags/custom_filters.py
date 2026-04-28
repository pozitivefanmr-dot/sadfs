from django import template
from casino.views import displayable_image_url

register = template.Library()


@register.filter
def disp_img(url):
    """Route external images through /img/proxy/ so all viewers see the same image."""
    return displayable_image_url(url)

@register.filter
def get_item(dictionary, key):
    """
    Позволяет получать значение из словаря в шаблоне по ключу.
    Использование: {{ mydict|get_item:key }}
    """
    return dictionary.get(key)