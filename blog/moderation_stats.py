from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.db.models.functions import TruncMonth
from .models import Comment, Article
import pandas as pd
# Importer matplotlib de manière conditionnelle
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
import os
from django.conf import settings

class ModerationStats:
    @classmethod
    def get_monthly_stats(cls, months=6):
        """
        Génère des statistiques mensuelles de modération
        
        Args:
            months (int): Nombre de mois à remonter
        
        Returns:
            QuerySet: Statistiques mensuelles de modération
        """
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=months*30)
        
        return Comment.objects.filter(created_at__gte=start_date).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_comments=Count('id'),
            spam_comments=Count('id', filter=Q(is_spam=True)),
            reported_comments=Count('id', filter=Q(is_reported=True)),
            offensive_comments=Count('id', filter=Q(is_offensive=True))
        ).order_by('month')

    @classmethod
    def generate_moderation_report(cls, months=6):
        """
        Génère un rapport complet de modération
        
        Args:
            months (int): Nombre de mois à remonter
        
        Returns:
            dict: Rapport détaillé de modération
        """
        monthly_stats = list(cls.get_monthly_stats(months))
        
        return {
            'total_comments': sum(stat['total_comments'] for stat in monthly_stats),
            'total_spam': sum(stat['spam_comments'] for stat in monthly_stats),
            'total_reported': sum(stat['reported_comments'] for stat in monthly_stats),
            'total_offensive': sum(stat['offensive_comments'] for stat in monthly_stats),
            'monthly_breakdown': monthly_stats
        }

    @classmethod
    def generate_moderation_visualization(cls, months=6):
        """
        Génère une visualisation graphique des statistiques de modération
        
        Args:
            months (int): Nombre de mois à remonter
        
        Returns:
            str: Chemin vers le fichier de graphique ou None si matplotlib non disponible
        """
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib non disponible. Impossible de générer le graphique.")
            return None
        
        monthly_stats = cls.get_monthly_stats(months)
        
        # Convertir en DataFrame pour faciliter la manipulation
        df = pd.DataFrame(list(monthly_stats))
        
        # Créer le graphique
        plt.figure(figsize=(12, 6))
        plt.plot(df['month'], df['total_comments'], label='Total Commentaires')
        plt.plot(df['month'], df['spam_comments'], label='Commentaires Spam')
        plt.plot(df['month'], df['reported_comments'], label='Commentaires Signalés')
        plt.plot(df['month'], df['offensive_comments'], label='Commentaires Offensifs')
        
        plt.title('Statistiques de Modération')
        plt.xlabel('Mois')
        plt.ylabel('Nombre de Commentaires')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Sauvegarder le graphique
        reports_dir = os.path.join(settings.BASE_DIR, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        graph_path = os.path.join(reports_dir, 'moderation_stats.png')
        plt.savefig(graph_path)
        plt.close()
        
        return graph_path

    @classmethod
    def export_moderation_report(cls, months=6, format='csv'):
        """
        Exporte le rapport de modération
        
        Args:
            months (int): Nombre de mois à remonter
            format (str): Format d'export (csv ou xlsx)
        
        Returns:
            str: Chemin vers le fichier exporté
        """
        monthly_stats = cls.get_monthly_stats(months)
        df = pd.DataFrame(list(monthly_stats))
        
        reports_dir = os.path.join(settings.BASE_DIR, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        if format == 'csv':
            file_path = os.path.join(reports_dir, 'moderation_report.csv')
            df.to_csv(file_path, index=False)
        else:
            file_path = os.path.join(reports_dir, 'moderation_report.xlsx')
            df.to_excel(file_path, index=False)
        
        return file_path
