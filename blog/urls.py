from django.urls import path
from . import views
from .views import logout_view

urlpatterns = [
    path('', views.home, name='home'),
    path('article/<slug:slug>/', views.detail_article, name='detail_article'),
    path('accounts/profile/', views.user_profile, name='user_profile'),
    path('accounts/logout/', logout_view, name='logout'),
    path('categorie/<slug:slug>/', views.articles_par_categorie, name='articles_par_categorie'),
    path('recherche/', views.recherche_articles, name='recherche_articles'),
    path('tag/<slug:slug>/', views.articles_par_tag, name='articles_par_tag'),
    path('register/', views.register, name='register'),
    path('profil/', views.profil, name='profil'),
    path('profil/modifier/', views.edit_profil, name='edit_profil'),
    path('profil/password/', views.edit_password, name='edit_password'),
    path('profil/<str:username>/', views.profil_public, name='profil_public'),
    path('delete_account/', views.delete_account, name='delete_account'),
    # Commentaires
    path('comment/report/<int:comment_id>/', views.report_comment, name='report_comment'),
    path('comment/like/<int:comment_id>/', views.like_comment, name='like_comment'),
    path('comment/dislike/<int:comment_id>/', views.dislike_comment, name='dislike_comment'),
    
    # Modération des commentaires
    path('comment/moderate/<int:comment_id>/', views.moderate_comment, name='moderate_comment'),
    path('moderation/', views.moderation, name='moderation'),
    path('moderation/validate/<int:comment_id>/', views.validate_comment, name='validate_comment'),
    path('moderation/reject/<int:comment_id>/', views.reject_comment, name='reject_comment'),
    
    # Newsletter
    path('newsletter/subscribe/', views.subscribe_newsletter, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/<str:email>/', views.unsubscribe_newsletter, name='newsletter_unsubscribe'),
    path('newsletter/success/', views.newsletter_success, name='newsletter_success'),
    
    # Tableau de bord auteur
    path('dashboard/', views.author_dashboard, name='author_dashboard'),
    path('dashboard/article/<int:article_id>/', views.article_performance_detail, name='article_performance'),
    
    # Gestion des brouillons
    path('drafts/', views.drafts_list, name='drafts_list'),
    path('drafts/create/', views.create_draft, name='create_draft'),
    path('drafts/edit/<int:article_id>/', views.edit_draft, name='edit_draft'),
    path('drafts/publish/<int:article_id>/', views.publish_draft, name='publish_draft'),
    path('drafts/delete/<int:article_id>/', views.delete_draft, name='delete_draft'),
    
    # Recherche avancée
    path('search/', views.search_articles, name='advanced_search'),
    
    # Mode lecture
    path('reading-preferences/', views.reading_preferences, name='reading_preferences'),
    path('reading-mode/<int:article_id>/', views.reading_mode, name='reading_mode'),
    
    # Badges et points
    path('badges/', views.user_badges, name='user_badges'),
    path('points-history/', views.points_history, name='points_history'),
    
    # Services IA
    path('ai-analysis/<int:article_id>/', views.ai_article_analysis, name='ai_article_analysis'),
    path('ai-apply-suggestions/<int:article_id>/', views.apply_ai_suggestions, name='apply_ai_suggestions'),
    
]
