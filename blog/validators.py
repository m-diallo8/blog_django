from django.core.exceptions import ValidationError
import re

def validate_no_spam(value):
    """
    Valide le contenu pour éviter le spam
    """
    spam_keywords = ['acheter', 'vendre', 'promotion', 'publicité']
    
    # Convertir en minuscules pour une comparaison insensible à la casse
    lowercase_value = value.lower()
    
    # Vérifier la présence de mots-clés de spam
    for keyword in spam_keywords:
        if keyword in lowercase_value:
            raise ValidationError(f'Le contenu contient des mots-clés de spam : {keyword}')
    
    return value

def validate_content_length(value):
    """
    Valide la longueur du contenu
    """
    min_length = 50  # Longueur minimale en caractères
    max_length = 10000  # Longueur maximale en caractères
    
    if len(value) < min_length:
        raise ValidationError(f'Le contenu doit contenir au moins {min_length} caractères.')
    
    if len(value) > max_length:
        raise ValidationError(f'Le contenu ne doit pas dépasser {max_length} caractères.')
    
    return value

def validate_no_html(value):
    """
    Vérifie l'absence de balises HTML
    """
    if re.search(r'<[^>]+>', value):
        raise ValidationError('Les balises HTML ne sont pas autorisées.')
    
    return value
