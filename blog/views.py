# Imports Django
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone

# Imports de l'application
from .models import (
    Article, Category, Comment, Profile, 
    ProfileField, NewsletterSubscriber, 
    ReadingPreference, Tag, UserBadge, 
    PointsHistory, ArticleView
)
from .forms import (
    DraftArticleForm, AdvancedSearchForm, 
    NewsletterSubscriptionForm, ReadingPreferenceForm
)
from .ai_services import (
    generate_summary, suggest_tags, 
    grammar_check, detect_language_complexity
)
from .moderation_logs import log_moderation_action
from .moderation_policy import ModerationPolicy
from .notifications import (
    comment_reported_notification,
    comment_moderation_action_notification
)

# Fonctions utilitaires pour la modération
def log_moderation_action(moderator, comment, action, reason=''):
    """
    Journalise une action de modération.
    
    :param moderator: Utilisateur qui effectue la modération
    :param comment: Commentaire modéré
    :param action: Action effectuée (approved, rejected, deleted)
    :param reason: Raison de la modération
    """
    from .models import ModerationLog
    
    try:
        log_entry = ModerationLog.objects.create(
            moderator=moderator,
            comment=comment,
            article=comment.article,
            action=action,
            reason=reason
        )
        return log_entry
    except Exception as e:
        # Gestion d'une erreur potentielle lors de la journalisation
        print(f"Erreur lors de la journalisation de la modération : {e}")
        return None

def log_moderation_error(moderator, comment, error_message):
    """
    Journalise une erreur de modération.
    
    :param moderator: Utilisateur qui a tenté la modération
    :param comment: Commentaire concerné
    :param error_message: Message d'erreur
    """
    from .models import ModerationErrorLog
    
    try:
        error_log = ModerationErrorLog.objects.create(
            moderator=moderator,
            comment=comment,
            article=comment.article,
            error_message=error_message
        )
        return error_log
    except Exception as e:
        # Gestion d'une erreur potentielle lors de la journalisation de l'erreur
        print(f"Erreur lors de la journalisation de l'erreur de modération : {e}")
        return None

# Politique de modération
from .moderation_policy import ModerationPolicy

try:
    from .moderation_stats import ModerationStats
    MODERATION_STATS_AVAILABLE = True
except ImportError:
    ModerationStats = None
    MODERATION_STATS_AVAILABLE = False
from django.core.paginator import Paginator
from django import forms
from django.conf import settings
from django.db import models
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.core.cache import cache
User = get_user_model()

# Vues pour la modération des commentaires
@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def moderation(request):
    """
    Vue pour afficher la liste des commentaires à modérer
    """
    comments_to_moderate = Comment.objects.filter(is_approved=False, is_rejected=False)
    context = {
        'comments': comments_to_moderate
    }
    return render(request, 'blog/moderation.html', context)

@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def validate_comment(request, comment_id):
    """
    Vue pour valider un commentaire
    """
    comment = get_object_or_404(Comment, id=comment_id)
    comment.is_approved = True
    comment.is_rejected = False
    comment.save()
    
    # Notification à l'auteur
    comment_moderation_action_notification(comment, 'validated')
    
    # Journalisation
    log_moderation_action(request.user, comment, 'approved')
    
    messages.success(request, 'Commentaire validé avec succès.')
    return redirect('moderation')

@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def reject_comment(request, comment_id):
    """
    Vue pour rejeter un commentaire
    """
    comment = get_object_or_404(Comment, id=comment_id)
    comment.is_approved = False
    comment.is_rejected = True
    comment.save()
    
    # Notification à l'auteur
    comment_moderation_action_notification(comment, 'rejected')
    
    # Journalisation
    log_moderation_action(request.user, comment, 'rejected')
    
    messages.warning(request, 'Commentaire rejeté.')
    return redirect('moderation')

# Vues pour la newsletter
def subscribe_newsletter(request):
    """
    Vue pour l'inscription à la newsletter
    """
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            subscriber = form.save()
            messages.success(request, 'Inscription à la newsletter réussie.')
            return redirect('newsletter_success')
    else:
        form = NewsletterSubscriptionForm()
    
    return render(request, 'blog/newsletter_subscribe.html', {'form': form})

def unsubscribe_newsletter(request, email):
    """
    Vue pour la désinscription de la newsletter
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email)
        subscriber.is_active = False
        subscriber.save()
        messages.success(request, 'Vous avez été désinscrit de la newsletter.')
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Email non trouvé.')
    
    return redirect('home')

def newsletter_success(request):
    """
    Page de confirmation d'inscription à la newsletter
    """
    return render(request, 'blog/newsletter_success.html')

# Vues pour le tableau de bord auteur
@login_required
def author_dashboard(request):
    """
    Tableau de bord pour les auteurs
    """
    articles = Article.objects.filter(author=request.user)
    total_views = ArticleView.objects.filter(article__author=request.user).count()
    avg_reading_time = articles.aggregate(Avg('reading_time'))['reading_time__avg'] or 0
    total_likes = articles.aggregate(Sum('likes'))['likes__sum'] or 0

    context = {
        'articles': articles,
        'total_views': total_views,
        'avg_reading_time': round(avg_reading_time, 2),
        'total_likes': total_likes
    }
    return render(request, 'blog/author_dashboard.html', context)

@login_required
def article_performance_detail(request, article_id):
    """
    Détails de performance pour un article spécifique
    """
    article = get_object_or_404(Article, id=article_id, author=request.user)
    views = ArticleView.objects.filter(article=article)
    comments = Comment.objects.filter(article=article)

    context = {
        'article': article,
        'views': views,
        'comments': comments,
        'total_views': views.count(),
        'total_comments': comments.count()
    }
    return render(request, 'blog/article_performance.html', context)

# Vues pour la gestion des brouillons
@login_required
def drafts_list(request):
    """
    Liste des brouillons de l'utilisateur
    """
    drafts = Article.objects.filter(author=request.user, is_published=False)
    return render(request, 'blog/drafts_list.html', {'drafts': drafts})

@login_required
def create_draft(request):
    """
    Création d'un nouveau brouillon
    """
    if request.method == 'POST':
        form = DraftArticleForm(request.POST, request.FILES)
        if form.is_valid():
            draft = form.save(commit=False)
            draft.author = request.user
            draft.is_published = False
            draft.save()
            messages.success(request, 'Brouillon créé avec succès.')
            return redirect('edit_draft', article_id=draft.id)
    else:
        form = DraftArticleForm()
    return render(request, 'blog/create_draft.html', {'form': form})

@login_required
def edit_draft(request, article_id):
    """
    Édition d'un brouillon existant
    """
    draft = get_object_or_404(Article, id=article_id, author=request.user, is_published=False)
    if request.method == 'POST':
        form = DraftArticleForm(request.POST, request.FILES, instance=draft)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brouillon mis à jour avec succès.')
            return redirect('drafts_list')
    else:
        form = DraftArticleForm(instance=draft)
    return render(request, 'blog/edit_draft.html', {'form': form, 'draft': draft})

@login_required
def publish_draft(request, article_id):
    """
    Publication d'un brouillon
    """
    draft = get_object_or_404(Article, id=article_id, author=request.user, is_published=False)
    draft.is_published = True
    draft.publication_date = timezone.now()
    draft.save()
    messages.success(request, 'Brouillon publié avec succès.')
    return redirect('drafts_list')

@login_required
def delete_draft(request, article_id):
    """
    Suppression d'un brouillon
    """
    draft = get_object_or_404(Article, id=article_id, author=request.user, is_published=False)
    draft.delete()
    messages.success(request, 'Brouillon supprimé avec succès.')
    return redirect('drafts_list')

# Vue pour la recherche avancée
def search_articles(request):
    """
    Recherche avancée d'articles
    """
    form = AdvancedSearchForm(request.GET)
    articles = Article.objects.filter(is_published=True)

    if form.is_valid():
        query = form.cleaned_data.get('query')
        categories = form.cleaned_data.get('categories')
        tags = form.cleaned_data.get('tags')
        min_reading_time = form.cleaned_data.get('min_reading_time')
        max_reading_time = form.cleaned_data.get('max_reading_time')

        if query:
            articles = articles.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query)
            )
        if categories:
            articles = articles.filter(category__in=categories)
        if tags:
            articles = articles.filter(tags__in=tags)
        if min_reading_time:
            articles = articles.filter(reading_time__gte=min_reading_time)
        if max_reading_time:
            articles = articles.filter(reading_time__lte=max_reading_time)

    context = {
        'form': form,
        'articles': articles
    }
    return render(request, 'blog/advanced_search.html', context)

# Vues pour le mode lecture
@login_required
def reading_preferences(request):
    """
    Gestion des préférences de lecture
    """
    if request.method == 'POST':
        form = ReadingPreferenceForm(request.POST)
        if form.is_valid():
            preference, created = ReadingPreference.objects.get_or_create(user=request.user)
            preference.font_size = form.cleaned_data['font_size']
            preference.color_scheme = form.cleaned_data['color_scheme']
            preference.save()
            messages.success(request, 'Préférences de lecture mises à jour.')
            return redirect('reading_preferences')
    else:
        preference = ReadingPreference.objects.filter(user=request.user).first()
        form = ReadingPreferenceForm(initial={
            'font_size': preference.font_size if preference else None,
            'color_scheme': preference.color_scheme if preference else None
        })
    return render(request, 'blog/reading_preferences.html', {'form': form})

@login_required
def reading_mode(request, article_id):
    """
    Mode lecture pour un article
    """
    article = get_object_or_404(Article, id=article_id)
    preference = ReadingPreference.objects.filter(user=request.user).first()
    context = {
        'article': article,
        'preference': preference
    }
    return render(request, 'blog/reading_mode.html', context)

# Vues pour les badges et points
@login_required
def user_badges(request):
    """
    Affichage des badges de l'utilisateur
    """
    user_badges = UserBadge.objects.filter(user=request.user)
    context = {
        'user_badges': user_badges
    }
    return render(request, 'blog/user_badges.html', context)

@login_required
def points_history(request):
    """
    Historique des points de l'utilisateur
    """
    points_history = PointsHistory.objects.filter(user=request.user).order_by('-created_at')
    total_points = points_history.aggregate(Sum('points'))['points__sum'] or 0
    context = {
        'points_history': points_history,
        'total_points': total_points
    }
    return render(request, 'blog/points_history.html', context)

# Vues pour la modération des commentaires
@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def moderate_comment(request, comment_id):
    """
    Vue pour la modération détaillée d'un commentaire
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Vérifier les permissions de modération
    if not request.user.has_perm('blog.can_moderate_comments'):
        messages.error(request, 'Vous n\'avez pas la permission de modérer des commentaires.')
        return redirect('home')
    
    # Contexte pour le template de modération
    context = {
        'comment': comment,
        'article': comment.article,
        'moderation_reasons': [
            'Contenu inapproprié',
            'Spam',
            'Langage offensant',
            'Hors-sujet',
            'Autre'
        ]
    }
    
    return render(request, 'blog/moderate_comment.html', context)

@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def moderation(request):
    """
    Vue pour afficher la liste des commentaires à modérer
    """
    # Filtrer les commentaires non approuvés et non rejetés
    comments_to_moderate = Comment.objects.filter(
        is_approved=False, 
        is_rejected=False
    ).select_related('article', 'author')
    
    # Pagination
    paginator = Paginator(comments_to_moderate, 20)  # 20 commentaires par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'comments': page_obj,
        'paginator': paginator
    }
    
    return render(request, 'blog/moderation_list.html', context)

@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def validate_comment(request, comment_id):
    """
    Vue pour valider un commentaire
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        # Valider le commentaire
        comment.is_approved = True
        comment.is_rejected = False
        comment.moderation_status = 'approved'
        comment.moderator = request.user
        comment.save()
        
        # Journalisation de l'action
        log_moderation_action(
            moderator=request.user, 
            comment=comment, 
            action='approved'
        )
        
        # Notification à l'auteur
        comment_moderation_action_notification(comment, 'validated')
        
        messages.success(request, 'Commentaire validé avec succès.')
    except Exception as e:
        # Gestion des erreurs
        messages.error(request, f'Erreur lors de la validation : {str(e)}')
        log_moderation_error(request.user, comment, str(e))
    
    return redirect('moderation')

@login_required
@permission_required('blog.can_moderate_comments', raise_exception=True)
def reject_comment(request, comment_id):
    """
    Vue pour rejeter un commentaire
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        # Rejeter le commentaire
        comment.is_approved = False
        comment.is_rejected = True
        comment.moderation_status = 'rejected'
        comment.moderator = request.user
        comment.save()
        
        # Journalisation de l'action
        log_moderation_action(
            moderator=request.user, 
            comment=comment, 
            action='rejected'
        )
        
        # Notification à l'auteur
        comment_moderation_action_notification(comment, 'rejected')
        
        messages.warning(request, 'Commentaire rejeté.')
    except Exception as e:
        # Gestion des erreurs
        messages.error(request, f'Erreur lors du rejet : {str(e)}')
        log_moderation_error(request.user, comment, str(e))
    
    return redirect('moderation')

# Vues pour la newsletter
def subscribe_newsletter(request):
    """
    Vue pour l'inscription à la newsletter
    """
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            try:
                # Vérifier si l'email existe déjà
                existing_subscriber = NewsletterSubscriber.objects.filter(email=form.cleaned_data['email']).first()
                
                if existing_subscriber:
                    if not existing_subscriber.is_active:
                        # Réactiver un abonné précédemment désinscrit
                        existing_subscriber.is_active = True
                        existing_subscriber.save()
                        messages.info(request, 'Vous êtes à nouveau abonné à la newsletter.')
                    else:
                        messages.warning(request, 'Vous êtes déjà abonné à la newsletter.')
                else:
                    # Créer un nouvel abonné
                    subscriber = form.save(commit=False)
                    subscriber.is_active = True
                    subscriber.save()
                    
                    # Envoyer un email de confirmation
                    send_newsletter_confirmation_email(subscriber.email)
                    
                    messages.success(request, 'Inscription à la newsletter réussie.')
                    return redirect('newsletter_success')
            
            except Exception as e:
                messages.error(request, f'Erreur lors de l\'inscription : {str(e)}')
        else:
            messages.error(request, 'Veuillez corriger les erreurs du formulaire.')
    else:
        form = NewsletterSubscriptionForm()
    
    return render(request, 'blog/newsletter_subscribe.html', {'form': form})

def unsubscribe_newsletter(request, email):
    """
    Vue pour la désinscription de la newsletter
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
        subscriber.is_active = False
        subscriber.unsubscribe_date = timezone.now()
        subscriber.save()
        
        # Journalisation de la désinscription
        log_newsletter_unsubscribe(subscriber)
        
        # Envoyer un email de confirmation de désinscription
        send_unsubscribe_confirmation_email(email)
        
        messages.success(request, 'Vous avez été désinscrit de la newsletter.')
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Email non trouvé ou déjà désinscrit.')
    except Exception as e:
        messages.error(request, f'Erreur lors de la désinscription : {str(e)}')
    
    return redirect('home')

def newsletter_success(request):
    """
    Page de confirmation d'inscription à la newsletter
    """
    return render(request, 'blog/newsletter_success.html')

# Fonctions utilitaires pour la newsletter
def send_newsletter_confirmation_email(email):
    """
    Envoie un email de confirmation d'inscription à la newsletter
    """
    try:
        subject = 'Confirmation d\'inscription à la newsletter'
        message = render_to_string('emails/newsletter_confirmation.html', {
            'email': email
        })
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=message
        )
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de confirmation : {e}")

def send_unsubscribe_confirmation_email(email):
    """
    Envoie un email de confirmation de désinscription de la newsletter
    """
    try:
        subject = 'Confirmation de désinscription de la newsletter'
        message = render_to_string('emails/newsletter_unsubscribe.html', {
            'email': email
        })
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=message
        )
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de désinscription : {e}")

def log_newsletter_unsubscribe(subscriber):
    """
    Journalise la désinscription d'un utilisateur à la newsletter
    """
    try:
        from .models import NewsletterUnsubscribeLog
        
        log_entry = NewsletterUnsubscribeLog.objects.create(
            subscriber=subscriber,
            email=subscriber.email
        )
        return log_entry
    except Exception as e:
        print(f"Erreur lors de la journalisation de la désinscription : {e}")
        return None


@login_required
def ai_article_analysis(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    
    # Vérifier les permissions
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas accès à cette analyse.")
        return redirect('article_detail', slug=article.slug)
    
    # Générer un résumé
    summary = article.generate_ai_summary()
    
    # Suggestions de tags
    suggested_tags = article.suggest_ai_tags()
    
    # Vérification grammaticale
    grammar_corrections = article.ai_grammar_check()
    
    # Détection de langue et complexité
    language = article.detect_language()
    complexity = article.calculate_complexity()
    
    context = {
        'article': article,
        'ai_summary': summary,
        'suggested_tags': suggested_tags,
        'grammar_corrections': grammar_corrections,
        'language': language,
        'complexity_score': complexity
    }
    
    return render(request, 'ai_article_analysis.html', context)

@login_required
def apply_ai_suggestions(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    
    # Vérifier les permissions
    if request.user != article.author and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas accès à ces suggestions.")
        return redirect('article_detail', slug=article.slug)
    
    if request.method == 'POST':
        # Appliquer les suggestions de tags
        if request.POST.get('apply_tags') and article.ai_suggested_tags:
            new_tags = [tag.strip() for tag in article.ai_suggested_tags.split(',')]
            for tag_name in new_tags:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                article.tags.add(tag)
        
        # Appliquer les corrections grammaticales
        if request.POST.get('apply_corrections') and article.ai_grammar_corrections:
            corrected_content = article.content
            for correction in article.ai_grammar_corrections:
                corrected_content = corrected_content.replace(
                    correction['original'], 
                    correction['correction']
                )
            article.content = corrected_content
        
        article.save()
        messages.success(request, "Les suggestions de l'IA ont été appliquées.")
        return redirect('article_detail', slug=article.slug)
    
    return redirect('ai_article_analysis', article_id=article.id)
try:
    from .moderation_stats import ModerationStats
    MODERATION_STATS_AVAILABLE = True
except ImportError:
    ModerationStats = None
    MODERATION_STATS_AVAILABLE = False
from django.core.paginator import Paginator
from django import forms
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.core.cache import cache
User = get_user_model()

def home(request):
    articles_list = Article.objects.select_related('category').order_by('-created_at')
    paginator = Paginator(articles_list, 6)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    categories_nav = Category.objects.order_by('name')
    context = {'articles': articles, 'categories_nav': categories_nav}
    context['now'] = timezone.now()
    messages.debug(request, 'debug message')
    messages.info(request, 'info message')
    messages.success(request, 'success message')
    messages.warning(request, 'warning message')
    messages.error(request, 'error message')
    return render(request, 'home.html', context)

def detail_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    categories_nav = Category.objects.order_by('name')
    comments = article.comments.filter(
        validated=True, 
        is_spam=False, 
        is_offensive=False, 
        parent=None
    ).order_by('-created_at')
    similaires = Article.objects.filter(category=article.category).exclude(id=article.id)[:3]

    # --- Anti-flood (manuel) ---
    def is_flood_limited(user):
        cache_key = f'comment_flood_{user.id}'
        last_comment_time = cache.get(cache_key)
        if last_comment_time and (timezone.now() - last_comment_time).total_seconds() < 60:
            return True
        cache.set(cache_key, timezone.now(), 60)
        return False

    # --- Formulaire pour commentaire ---
    class CommentForm(forms.ModelForm):
        content = forms.CharField(
            widget=forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Votre commentaire...',
                'rows': 4
            }),
            required=True,  # Assurez-vous que ce champ est obligatoire
            label='Commentaire'
        )
        class Meta:
            model = Comment
            fields = ['name', 'email', 'content', 'image']
            widgets = {
                'image': forms.FileInput(attrs={
                    'accept': 'image/jpeg,image/png,image/gif,image/webp',
                    'class': 'form-control'
                })
            }

    form = CommentForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and request.user.is_authenticated:
        if is_flood_limited(request.user):
            messages.warning(request, "Patientez 1 minute entre chaque commentaire.")
            return redirect('detail_article', slug=slug)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article

            # Sécuriser le parent
            if comment.parent and comment.parent.article != article:
                comment.parent = None

            # Captcha vérif (si désactivée côté template pour les users loggés)
            if not request.user.is_authenticated and not form.cleaned_data.get('captcha'):
                form.add_error('captcha', "Veuillez cocher la case pour prouver que vous n'êtes pas un robot.")
            else:
                comment.is_spam = False
                comment.save()

                # Notif auteur article
                if comment.validated and hasattr(article, 'author') and getattr(article.author, 'email', None):
                    send_mail(
                        subject=f'Nouveau commentaire sur votre article : {article.title}',
                        message=f'{comment.name} a posté :\n\n{comment.content}\n\nVoir : {request.build_absolute_uri(article.get_absolute_url())}',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[article.author.email],
                        fail_silently=True,
                    )

                # Notif auteur du commentaire parent
                if comment.validated and comment.parent and comment.parent.email and comment.parent.email != comment.email:
                    send_mail(
                        subject=f'Nouvelle réponse à votre commentaire sur : {article.title}',
                        message=f'{comment.name} a répondu :\n\nVotre commentaire : {comment.parent.content}\n\nRéponse : {comment.content}\n\nVoir : {request.build_absolute_uri(article.get_absolute_url())}',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[comment.parent.email],
                        fail_silently=True,
                    )

                return redirect('detail_article', slug=slug)

    elif request.method == 'GET' and request.user.is_authenticated:
        form = CommentForm()
    else:
        form = None  # Utilisateur non connecté

    return render(request, 'detail_article.html', {
        'article': article,
        'categories_nav': categories_nav,
        'comments': comments,
        'form': form,
        'similaires': similaires
    })

def articles_par_categorie(request, slug):
    categorie = get_object_or_404(Category, slug=slug)
    articles_list = categorie.articles.order_by('-created_at')
    paginator = Paginator(articles_list, 6)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    categories_nav = Category.objects.order_by('name')
    return render(request, 'articles_categorie.html', {'categorie': categorie, 'articles': articles, 'categories_nav': categories_nav})

def recherche_articles(request):
    query = request.GET.get('q', '')
    articles = Article.objects.select_related('category').filter(
        models.Q(title__icontains=query) | models.Q(content__icontains=query)
    ).order_by('-created_at') if query else []
    categories_nav = Category.objects.order_by('name')
    return render(request, 'recherche.html', {'articles': articles, 'categories_nav': categories_nav, 'query': query})

@login_required
def profil(request):
    categories_nav = Category.objects.order_by('name')
    from .models import Profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'profil.html', {'categories_nav': categories_nav, 'profile': profile})

class EmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

@login_required
def edit_profil(request):
    categories_nav = Category.objects.order_by('name')
    from .models import Profile
    profile, _ = Profile.objects.get_or_create(user=request.user)

    class ProfileForm(forms.ModelForm):
        class Meta:
            model = Profile
            fields = ['bio', 'avatar', 'photo', 'twitter', 'linkedin', 'github', 'website', 'facebook', 'instagram', 'is_public', 'newsletter', 'notifications']

    ProfileFieldFormSet = forms.modelformset_factory(ProfileField, fields=("key", "value"), extra=0, can_delete=True)

    if request.method == 'POST':
        email_form = EmailForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        formset = ProfileFieldFormSet(request.POST, queryset=profile.custom_fields.all())
        if email_form.is_valid() and profile_form.is_valid() and formset.is_valid():
            email_form.save()
            profile_form.save()
            instances = formset.save(commit=False)
            for obj in formset.deleted_objects:
                obj.delete()
            for instance in instances:
                instance.profile = profile
                instance.save()
            return redirect('profil')
    else:
        email_form = EmailForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
        formset = ProfileFieldFormSet(queryset=profile.custom_fields.all())
    return render(request, 'edit_profil.html', {
        'form': email_form,
        'profile_form': profile_form,
        'formset': formset,
        'categories_nav': categories_nav
    })

@login_required
def edit_password(request):
    categories_nav = Category.objects.order_by('name')
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('profil')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'edit_password.html', {'form': form, 'categories_nav': categories_nav})

@staff_member_required
def moderation(request):
    # Filtres dynamiques de modération
    filter_type = request.GET.get('filter', 'all')
    
    # Requête de base pour les commentaires
    comments_query = Comment.objects.filter(is_approved=False)
    
    # Filtres conditionnels
    if filter_type == 'spam':
        comments_query = comments_query.filter(is_spam=True)
    elif filter_type == 'offensive':
        comments_query = comments_query.filter(is_offensive=True)
    elif filter_type == 'reported':
        comments_query = comments_query.filter(is_reported=True)
    
    # Ordonner par date de création
    comments = comments_query.order_by('-created_at')
    
    # Statistiques de modération
    all_comments_count = Comment.objects.filter(is_approved=False).count()
    reported_comments_count = Comment.objects.filter(is_reported=True).count()
    spam_comments_count = Comment.objects.filter(is_spam=True).count()
    offensive_comments_count = Comment.objects.filter(is_offensive=True).count()
    
    # Générer un rapport de statistiques
    moderation_report = None
    if MODERATION_STATS_AVAILABLE and ModerationStats:
        try:
            moderation_report = ModerationStats.generate_moderation_report()
        except Exception as e:
            print(f"Erreur lors de la génération du rapport : {e}")
    
    return render(request, 'moderation_dashboard.html', {
        'comments': comments,
        'filter_type': filter_type,
        'all_comments_count': all_comments_count,
        'reported_comments_count': reported_comments_count,
        'spam_comments_count': spam_comments_count,
        'offensive_comments_count': offensive_comments_count,
        'moderation_report': moderation_report
    })

@staff_member_required
@login_required
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        # Retirer un éventuel dislike
        comment.dislikes.remove(request.user)
        
        if request.user in comment.likes.all():
            # Si déjà liké, enlever le like
            comment.likes.remove(request.user)
        else:
            # Ajouter le like
            comment.likes.add(request.user)
        
        comment.save()
        return redirect(comment.article.get_absolute_url())

@login_required
def dislike_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        # Retirer un éventuel like
        comment.likes.remove(request.user)
        
        if request.user in comment.dislikes.all():
            # Si déjà disliké, enlever le dislike
            comment.dislikes.remove(request.user)
        else:
            # Ajouter le dislike
            comment.dislikes.add(request.user)
        
        comment.save()
        return redirect(comment.article.get_absolute_url())

@staff_member_required
def validate_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Vérification de la politique de modération
    policy = ModerationPolicy.get_policy()
    
    # Réinitialisation des flags de modération
    comment.is_reported = False
    comment.is_spam = False
    comment.is_offensive = False
    comment.is_approved = True
    comment.moderated_at = timezone.now()
    comment.moderated_by = request.user
    comment.save()
    
    # Journalisation de l'action
    log_moderation_action(request.user, comment, 'validate')
    
    # Notification de l'action de modération
    comment_moderation_action_notification(comment, 'validate')
    
    # Notification optionnelle à l'utilisateur
    if comment.email:
        send_mail(
            'Votre commentaire a été approuvé',
            f'Votre commentaire sur l\'article {comment.article.title} a été validé.',
            settings.DEFAULT_FROM_EMAIL,
            [comment.email],
            fail_silently=True
        )
    
    messages.success(request, "Le commentaire a été validé.")
    return redirect('moderation')

@staff_member_required
def reject_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Marquage et archivage du commentaire
    comment.is_reported = False
    comment.is_approved = False
    comment.is_spam = True  # Optionnel : peut être ajusté
    comment.moderated_at = timezone.now()
    comment.moderated_by = request.user
    comment.save()
    
    # Journalisation de l'action
    log_moderation_action(request.user, comment, 'reject')
    
    # Notification de l'action de modération
    comment_moderation_action_notification(comment, 'reject')
    
    # Notification optionnelle à l'utilisateur
    if comment.email:
        send_mail(
            'Votre commentaire a été rejeté',
            f'Votre commentaire sur l\'article {comment.article.title} ne respecte pas nos conditions.',
            settings.DEFAULT_FROM_EMAIL,
            [comment.email],
            fail_silently=True
        )
    
    messages.warning(request, "Le commentaire a été rejeté.")
    return redirect('moderation')

def profil_public(request, username):
    from django.shortcuts import get_object_or_404
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    from .models import Profile
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.is_public:
        from django.http import Http404
        raise Http404("Ce profil est privé.")
    categories_nav = Category.objects.order_by('name')
    return render(request, 'profil_public.html', {'profile': profile, 'categories_nav': categories_nav})

def report_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Vérification de la politique de modération
    policy_check = ModerationPolicy.check_comment(comment.content)
    
    comment.is_reported = True
    
    # Détection automatique
    moderation_result = detect_spam_or_offensive_content(comment.content)
    comment.is_spam = moderation_result['is_spam']
    comment.is_offensive = moderation_result['is_offensive']
    
    comment.save()
    
    # Journalisation de l'action
    log_moderation_action(request.user, comment, 'report')
    
    # Notification aux modérateurs
    comment_reported_notification(comment)
    
    if not policy_check['is_valid']:
        messages.warning(request, f"Commentaire signalé. Raisons : {', '.join(policy_check['reasons'])}")
    else:
        messages.success(request, "Le commentaire a été signalé à la modération.")
    
    return redirect('detail_article', slug=comment.article.slug)

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, 'Votre compte a été supprimé avec succès.')
        return redirect('home')
    return render(request, 'delete_account.html')

from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('home')


def register(request):
    categories_nav = Category.objects.order_by('name')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import login
            login(request, user)
            messages.success(request, 'Votre compte a été créé avec succès.')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form, 'categories_nav': categories_nav})

def articles_par_tag(request, slug):
    from django.shortcuts import get_object_or_404
    from .models import Tag
    tag = get_object_or_404(Tag, slug=slug)
    articles_list = tag.articles.order_by('-created_at')
    paginator = Paginator(articles_list, 6)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    categories_nav = Category.objects.order_by('name')
    return render(request, 'articles_tag.html', {'tag': tag, 'articles': articles, 'categories_nav': categories_nav})

@login_required
def user_profile(request):
    # Récupérer ou créer le profil de l'utilisateur connecté
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Récupérer les articles de l'utilisateur
    user_articles = Article.objects.filter(author=request.user).order_by('-created_at')
    
    context = {
        'profile': profile,
        'articles': user_articles,
        'total_articles': user_articles.count(),
    }
    
    return render(request, 'user_profile.html', context)
