from django.utils.deprecation import MiddlewareMixin
from .models import ArticleView, Article

class ArticleViewTrackingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Vérifier si la vue est celle de détail d'article
        if view_func.__name__ == 'detail_article':
            # Récupérer l'article
            article_slug = view_kwargs.get('slug')
            try:
                article = Article.objects.get(slug=article_slug)
                
                # Créer une vue d'article
                ArticleView.objects.create(
                    article=article,
                    viewer=request.user if request.user.is_authenticated else None,
                    ip_address=self.get_client_ip(request)
                )
            except Article.DoesNotExist:
                pass
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
