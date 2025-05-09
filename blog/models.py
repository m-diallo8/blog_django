from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags, escape
from bleach import clean
import bleach
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.urls import reverse
from django.db.models import Q

# Indexation de recherche
from whoosh.index import create_in
from whoosh.fields import *
from whoosh.qparser import QueryParser

# Importer les modules de validation
from .validators import validate_no_spam, validate_content_length

User = get_user_model()

# Créer un index de recherche
def create_search_index():
    schema = Schema(
        id=ID(stored=True, unique=True),
        title=TEXT(stored=True),
        content=TEXT(stored=True),
        author=TEXT(stored=True),
        category=TEXT(stored=True),
        tags=KEYWORD(stored=True, commas=True),
        published_at=DATETIME(stored=True)
    )
    
    import os
    from whoosh.index import create_in
    
    index_dir = os.path.join(os.path.dirname(__file__), 'search_index')
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    
    create_in(index_dir, schema)

# Méthode de recherche avancée
def advanced_search(query, category=None, tags=None, start_date=None, end_date=None):
    from whoosh.index import open_dir
    from whoosh.qparser import MultifieldParser
    
    index_dir = os.path.join(os.path.dirname(__file__), 'search_index')

# Modèle pour suivre les vues des articles
class ArticleView(models.Model):
    """
    Modèle pour suivre les vues des articles
    """
    article = models.ForeignKey(
        'Article', 
        on_delete=models.CASCADE, 
        related_name='views'
    )
    viewer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='article_views'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Vue d\'article'
        verbose_name_plural = 'Vues d\'articles'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['article', 'timestamp']),
            models.Index(fields=['viewer', 'timestamp'])
        ]
    
    def __str__(self):
        return f"Vue de l'article {self.article.title} par {self.viewer or 'Anonyme'} à {self.timestamp}"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles')
    content = models.TextField()
    image = models.ImageField(upload_to='articles/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('detail_article', kwargs={'slug': self.slug})
    
    def get_share_text(self):
        # Texte de partage personnalisé
        return f"Je recommande l'article '{self.title}' sur mon blog !"
    
    def get_share_hashtags(self):
        # Générer des hashtags à partir des tags
        return [f"#{tag.name.replace(' ', '')}" for tag in self.tags.all()]
    
    def calculate_engagement_score(self):
        # Score d'engagement basé sur les vues, likes et commentaires
        views_weight = 0.3
        likes_weight = 0.4
        comments_weight = 0.3
        
        views_score = min(self.views_count / 100, 1)  # Normaliser les vues
        likes_score = min(self.likes_count / 50, 1)  # Normaliser les likes
        comments_score = min(self.comments.count() / 10, 1)  # Normaliser les commentaires
        
        return round((views_weight * views_score + 
                      likes_weight * likes_score + 
                      comments_weight * comments_score) * 100, 2)
    
    def get_performance_suggestions(self):
        suggestions = []
        engagement_score = self.calculate_engagement_score()
        
        if self.views_count < 50:
            suggestions.append("Augmentez la visibilité de l'article en le partageant sur les réseaux sociaux")
        
        if self.likes_count < 10:
            suggestions.append("Améliorez le contenu pour encourager plus d'interactions")
        
        if self.comments.count() < 3:
            suggestions.append("Encouragez les lecteurs à laisser des commentaires")
        
        if engagement_score < 30:
            suggestions.append("L'article a besoin d'améliorations significatives")
        elif engagement_score < 50:
            suggestions.append("Il y a de la place pour améliorer l'engagement")
        
        return suggestions
    
    def is_draft(self):
        # Vérifier si l'article est un brouillon
        return not self.is_published
    
    def can_edit(self, user):
        # Vérifier si l'utilisateur peut éditer l'article
        return self.author == user or user.is_staff
    
    def get_draft_url(self):
        # URL pour éditer un brouillon
        return reverse('edit_draft', kwargs={'article_id': self.id})

    def __str__(self):
        return self.title

class ArticleView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vue d'article"
        verbose_name_plural = "Vues d'articles"
        ordering = ['-viewed_at']
        unique_together = ['article', 'viewer', 'ip_address', 'viewed_at']
    
    def __str__(self):
        return f"Vue de {self.article.title} par {self.viewer or self.ip_address}"

class ReadingPreference(models.Model):
    FONT_SIZES = [
        ('small', 'Petit'),
        ('medium', 'Moyen'),
        ('large', 'Grand'),
        ('extra-large', 'Très Grand')
    ]
    
    CONTRAST_MODES = [
        ('default', 'Défaut'),
        ('high-contrast', 'Contraste Élevé'),
        ('dark-mode', 'Mode Sombre'),
        ('sepia', 'Sépia')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reading_preference')
    font_size = models.CharField(
        max_length=20, 
        choices=FONT_SIZES, 
        default='medium'
    )
    contrast_mode = models.CharField(
        max_length=20, 
        choices=CONTRAST_MODES, 
        default='default'
    )
    line_height = models.FloatField(default=1.5)
    reading_width = models.IntegerField(default=70)  # Largeur en pourcentage
    
    def get_reading_class(self):
        # Générer une classe CSS personnalisée
        classes = [
            f'font-size-{self.font_size}',
            f'contrast-{self.contrast_mode}',
            f'line-height-{int(self.line_height * 100)}'
        ]
        return ' '.join(classes)
    
    def __str__(self):
        return f"Préférences de lecture de {self.user.username}"
    def get_related_articles(self, limit=3):
        # Recommander des articles basés sur les tags et la catégorie
        from django.db.models import Q, Count

class Badge(models.Model):
    BADGE_TYPES = [
        ('bronze', 'Bronze'),
        ('silver', 'Argent'),
        ('gold', 'Or'),
        ('platinum', 'Platine')
    ]
    
    CATEGORIES = [
        ('author', 'Auteur'),
        ('reader', 'Lecteur'),
        ('engagement', 'Engagement'),
        ('contribution', 'Contribution')
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES, default='bronze')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='reader')
    icon = models.ImageField(upload_to='badges/', null=True, blank=True)
    points_required = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class UserPoints(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points')
    total_points = models.IntegerField(default=0)
    
    def add_points(self, points, reason=None):
        self.total_points += points
        self.save()
        
        # Vérifier et attribuer des badges
        self.check_and_award_badges()
        
        # Optionnel : enregistrer l'historique des points
        if reason:
            PointsHistory.objects.create(
                user=self.user,
                points=points,
                reason=reason
            )
    
    def check_and_award_badges(self):
        # Rechercher les badges non encore obtenus
        unearned_badges = Badge.objects.exclude(
            id__in=self.user.user_badges.values_list('badge_id', flat=True)
        ).filter(points_required__lte=self.total_points)
        
        for badge in unearned_badges:
            UserBadge.objects.create(user=self.user, badge=badge)
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"

class PointsHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_history')
    points = models.IntegerField()
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.points} points ({self.reason})"

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.email
        
        # Trouver des articles avec des tags communs
        related_by_tags = Article.objects.filter(
            Q(tags__in=self.tags.all()) & ~Q(id=self.id)
        ).annotate(
            tag_count=Count('tags')
        ).order_by('-tag_count')[:limit]
        
        # Si pas assez d'articles par tags, compléter avec des articles de la même catégorie
        if related_by_tags.count() < limit:
            related_by_category = Article.objects.filter(
                Q(category=self.category) & ~Q(id=self.id) & ~Q(id__in=related_by_tags)
            )[:limit - related_by_tags.count()]

            # Combiner les résultats
            related_articles = list(related_by_tags) + list(related_by_category)
        else:
            related_articles = list(related_by_tags)

        return related_articles[:limit]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True, verbose_name='Biographie')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Photo de profil')
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    website = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    is_public = models.BooleanField(default=True)
    newsletter = models.BooleanField(default=False)
    notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

class ProfileField(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='custom_fields')
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    name = models.CharField(max_length=80)
    email = models.EmailField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    validated = models.BooleanField(default=False)
    is_spam = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    # Champs pour les likes et dislikes
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    dislikes = models.ManyToManyField(User, related_name='disliked_comments', blank=True)
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def dislike_count(self):
        return self.dislikes.count()

    # Champs pour le signalement
    reported_by = models.ManyToManyField(User, related_name='reported_comments', blank=True)
    report_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de signalements")
    report_reason = models.TextField(blank=True, null=True, verbose_name="Raison du signalement")
    is_offensive = models.BooleanField(default=False, verbose_name="Commentaire offensant")
    moderation_reason = models.TextField(blank=True, null=True, verbose_name="Raison de la modération")
    moderated_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de modération")
    
    def save(self, *args, **kwargs):
        # Mettre à jour les compteurs de likes et dislikes
        # self.like_count = self.likes.count()
        # self.dislike_count = self.dislikes.count()
        
        # Mettre à jour le nombre de signalements
        self.report_count = self.reported_by.count()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commentaire de {self.name} sur {self.article.title}"
    
    def is_moderatable(self):
        """Vérifie si le commentaire est modérable"""
        return not (self.is_approved or self.is_spam or self.is_offensive)

    image = models.ImageField(
        upload_to='comments/', 
        null=True, 
        blank=True, 
        max_length=500,
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp']),
        ],
        help_text='Image optionnelle pour le commentaire (max 5 Mo)'
    )

    def clean_html_content(self):
        """Nettoie et sécurise le contenu HTML"""
        allowed_tags = ['p', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 
                        'ul', 'ol', 'li', 'a', 'br', 'blockquote']
        allowed_attributes = {
            'a': ['href', 'title'],
            'p': ['class'],
        }
        return bleach.clean(
            self.content, 
            tags=allowed_tags, 
            attributes=allowed_attributes, 
            strip=True
        )

    def clean_image(self):
        """Validation personnalisée pour l'image du commentaire"""
        if self.image:
            # Limite de taille (5 Mo)
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError('La taille de l\'image ne doit pas dépasser 5 Mo.')
        return self.image  # Retourne l'image si tout est OK

    def save(self, *args, **kwargs):
        # Nettoyer le contenu HTML avant sauvegarde
        self.content = self.clean_html_content()
        
        # Valider l'image
        if self.image:
            self.clean_image()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commentaire de {self.name} sur {self.article.title}"
