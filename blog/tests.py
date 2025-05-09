from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Comment, Article, Category
from .utils import detect_spam_or_offensive_content

User = get_user_model()

class CommentModerationTestCase(TestCase):
    def setUp(self):
        # Créer un utilisateur admin
        self.admin_user = User.objects.create_superuser(
            username='admin', 
            email='admin@example.com', 
            password='adminpassword'
        )
        
        # Créer une catégorie de test
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Créer un article de test
        self.article = Article.objects.create(
            title='Test Article',
            content='Test Content',
            slug='test-article',
            category=self.category
        )
    
    def test_spam_detection(self):
        spam_comments = [
            "Acheter viagra pas cher en ligne !",
            "Gagnez de l'argent rapidement avec Bitcoin",
            "http://site-suspect.com/article http://autre-site.com"
        ]
        
        for comment_text in spam_comments:
            result = detect_spam_or_offensive_content(comment_text)
            self.assertTrue(result['is_spam'], f"N'a pas détecté le spam: {comment_text}")
    
    def test_moderation_workflow(self):
        comment = Comment.objects.create(
            article=self.article,
            name='Test User',
            email='test@example.com',
            content='Commentaire de test pour modération'
        )
        
        # Vérifier l'état initial
        self.assertFalse(comment.is_approved)
        
        # Simuler un signalement
        comment.is_reported = True
        comment.save()
        
        # Vérifier le signalement
        self.assertTrue(comment.is_reported)
    
    def test_moderation_views(self):
        # Créer un commentaire à modérer
        Comment.objects.create(
            article=self.article,
            name='Spam User',
            email='spam@example.com',
            content='Acheter viagra pas cher en ligne !',
            is_reported=True
        )
        
        # Connexion en tant qu'admin
        self.client.login(username='admin', password='adminpassword')
        
        # Tester la vue de modération
        response = self.client.get(reverse('moderation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modération des commentaires')
