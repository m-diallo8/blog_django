from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def notify_moderators(subject, message, comment=None):
    """
    Envoie une notification par email à tous les modérateurs
    
    Args:
        subject (str): Sujet de l'email
        message (str): Corps du message
        comment (Comment, optional): Commentaire associé à la notification
    """
    # Récupérer tous les utilisateurs staff (modérateurs)
    moderators = User.objects.filter(is_staff=True)
    
    # Emails des modérateurs
    moderator_emails = [user.email for user in moderators if user.email]
    
    if moderator_emails:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                moderator_emails,
                fail_silently=False
            )
        except Exception as e:
            # Journalisation de l'erreur d'envoi
            print(f"Erreur lors de l'envoi de la notification : {e}")

def comment_reported_notification(comment):
    """
    Notification spécifique pour un commentaire signalé
    
    Args:
        comment (Comment): Le commentaire signalé
    """
    subject = f"Commentaire signalé sur l'article {comment.article.title}"
    message = f"""
    Un nouveau commentaire a été signalé :
    
    Auteur : {comment.name}
    Article : {comment.article.title}
    Contenu : {comment.content[:200]}...
    
    Actions possibles :
    - Modérer le commentaire
    - Vérifier le contexte
    
    Connectez-vous à l'interface de modération pour plus de détails.
    """
    
    notify_moderators(subject, message, comment)

def comment_moderation_action_notification(comment, action):
    """
    Notification pour une action de modération
    
    Args:
        comment (Comment): Le commentaire modéré
        action (str): Action effectuée ('validate' ou 'reject')
    """
    action_labels = {
        'validate': 'Validé',
        'reject': 'Rejeté'
    }
    
    subject = f"Commentaire {action_labels.get(action, 'Modéré')} - {comment.article.title}"
    message = f"""
    Un commentaire a été {action_labels.get(action, 'modéré')} :
    
    Auteur : {comment.name}
    Article : {comment.article.title}
    Contenu : {comment.content[:200]}...
    
    Action : {action_labels.get(action, 'Modération')}
    
    Connectez-vous à l'interface de modération pour plus de détails.
    """
    
    notify_moderators(subject, message, comment)
