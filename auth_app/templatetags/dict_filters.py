from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Filtre personnalisé pour récupérer une valeur dans un dictionnaire."""
    if dictionary is None:
        return False  # Retourne False si le dictionnaire est None
    return dictionary.get(key, False)
