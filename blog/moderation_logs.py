import logging
from django.utils import timezone
from django.conf import settings
import os

# Configurer le logging
LOG_DIR = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configuration du logger de modération
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'moderation.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('moderation')

def log_moderation_action(user, comment, action):
    """
    Enregistre les actions de modération détaillées
    
    Args:
        user (User): Utilisateur effectuant l'action
        comment (Comment): Commentaire modéré
        action (str): Action effectuée (validate, reject, report)
    """
    log_entry = {
        'timestamp': timezone.now().isoformat(),
        'moderator': user.username,
        'moderator_email': user.email,
        'comment_id': comment.id,
        'article_title': comment.article.title,
        'article_slug': comment.article.slug,
        'action': action,
        'comment_content': comment.content[:200],
        'is_spam': comment.is_spam,
        'is_offensive': comment.is_offensive
    }
    
    # Log différent selon l'action
    if action == 'validate':
        logger.info(f"Comment Validated: {log_entry}")
    elif action == 'reject':
        logger.warning(f"Comment Rejected: {log_entry}")
    elif action == 'report':
        logger.error(f"Comment Reported: {log_entry}")
    
    return log_entry

def get_moderation_logs(days=30, action=None):
    """
    Récupère les logs de modération des derniers jours
    
    Args:
        days (int): Nombre de jours à remonter
        action (str, optional): Filtrer par type d'action
    
    Returns:
        list: Liste des entrées de log
    """
    # Note: Dans un vrai projet, on utiliserait une base de données pour stocker les logs
    from datetime import timedelta
    
    try:
        with open(os.path.join(LOG_DIR, 'moderation.log'), 'r') as log_file:
            logs = log_file.readlines()
        
        # Filtrer les logs récents et par action
        recent_logs = []
        cutoff_date = timezone.now() - timedelta(days=days)
        
        for log_line in logs:
            # Logique de filtrage basique (à améliorer)
            if action is None or action in log_line:
                recent_logs.append(log_line.strip())
        
        return recent_logs
    except Exception as e:
        logger.error(f"Erreur lors de la lecture des logs : {e}")
        return []
