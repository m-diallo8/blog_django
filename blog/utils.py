import re
import bleach
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def detect_spam_or_offensive_content(comment_text: str) -> Dict[str, bool]:
    """
    Détecte le spam et le contenu offensant avec des règles avancées
    
    Args:
        comment_text (str): Le texte du commentaire à analyser
    
    Returns:
        Dict[str, bool]: Un dictionnaire indiquant si le contenu est du spam ou offensant
    """
    try:
        # Normalisation du texte
        comment_text = comment_text.lower().strip()
        
        # Règles de détection de spam
        spam_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
            r'\b(viagra|cialis|bitcoin|earn money|get rich)\b',  # Mots-clés de spam
            r'\d{3,}-\d{3,}-\d{3,}',  # Numéros suspects
        ]
        
        # Règles de détection de contenu offensant
        offensive_patterns = [
            r'\b(fuck|shit|putain|con|merde|salope)\b',  # Mots offensants
            r'va te faire foutre',  # Expressions offensantes
            r'tu es un(e)? (con|idiote?|imbécile|débile)',  # Insultes
        ]
        
        # Vérification des URLs
        url_count = len(re.findall(r'http[s]?://', comment_text))
        
        # Vérification des mots-clés de spam
        is_spam = (
            any(re.search(pattern, comment_text, re.IGNORECASE) for pattern in spam_patterns) or
            url_count > 2 or  # Plus de 2 URLs
            len(comment_text.split()) < 3  # Commentaires très courts
        )
        
        # Vérification du contenu offensant
        is_offensive = any(
            re.search(pattern, comment_text, re.IGNORECASE) 
            for pattern in offensive_patterns
        )
        
        # Journalisation des résultats
        if is_spam or is_offensive:
            logger.info(f'Spam détecté: {is_spam}, Contenu offensant: {is_offensive}')
        
        return {
            'is_spam': is_spam,
            'is_offensive': is_offensive
        }
    
    except Exception as e:
        logger.error(f'Erreur lors de la détection : {e}')
        return {'is_spam': False, 'is_offensive': False}
