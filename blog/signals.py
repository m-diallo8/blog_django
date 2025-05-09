from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Article

# @receiver(post_save, sender=Article)
# def newsletter_on_new_article(sender, instance, created, **kwargs):
#     # N'envoyer la newsletter que pour les nouveaux articles publiés
#     if created and instance.is_published:
#         send_newsletter(instance)
