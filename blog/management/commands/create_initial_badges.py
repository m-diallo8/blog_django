from django.core.management.base import BaseCommand
from blog.models import Badge

class Command(BaseCommand):
    help = 'Créer les badges initiaux pour le système de récompenses'

    def handle(self, *args, **kwargs):
        badges_data = [
            # Badges Lecteur
            {
                'name': 'Lecteur Débutant',
                'description': 'Premier pas dans le monde de la lecture',
                'badge_type': 'bronze',
                'category': 'reader',
                'points_required': 50
            },
            {
                'name': 'Lecteur Assidu',
                'description': 'Lu plus de 10 articles',
                'badge_type': 'silver',
                'category': 'reader',
                'points_required': 200
            },
            {
                'name': 'Bibliophile',
                'description': 'Lu plus de 50 articles',
                'badge_type': 'gold',
                'category': 'reader',
                'points_required': 500
            },
            
            # Badges Auteur
            {
                'name': 'Première Publication',
                'description': 'A publié son premier article',
                'badge_type': 'bronze',
                'category': 'author',
                'points_required': 50
            },
            {
                'name': 'Auteur Confirmé',
                'description': 'A publié 5 articles',
                'badge_type': 'silver',
                'category': 'author',
                'points_required': 250
            },
            {
                'name': 'Blogueur Émérite',
                'description': 'A publié plus de 20 articles',
                'badge_type': 'gold',
                'category': 'author',
                'points_required': 1000
            },
            
            # Badges Engagement
            {
                'name': 'Premier Commentaire',
                'description': 'A posté son premier commentaire',
                'badge_type': 'bronze',
                'category': 'engagement',
                'points_required': 20
            },
            {
                'name': 'Contributeur Actif',
                'description': 'A posté plus de 10 commentaires',
                'badge_type': 'silver',
                'category': 'engagement',
                'points_required': 100
            },
            {
                'name': 'Mentor Communautaire',
                'description': 'A posté plus de 50 commentaires',
                'badge_type': 'gold',
                'category': 'engagement',
                'points_required': 500
            }
        ]
        
        for badge_info in badges_data:
            Badge.objects.get_or_create(
                name=badge_info['name'],
                defaults=badge_info
            )
        
        self.stdout.write(self.style.SUCCESS('Badges initiaux créés avec succès !'))
