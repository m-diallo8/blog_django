from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Article, Tag
from blog.ai_services import (
    generate_summary, 
    suggest_tags, 
    grammar_check, 
    detect_language_complexity
)

class Command(BaseCommand):
    help = 'Tester les services IA pour les articles'

    def handle(self, *args, **kwargs):
        # Récupérer un article de test
        try:
            article = Article.objects.first()
            if not article:
                self.stdout.write(self.style.ERROR('Aucun article trouvé. Créez un article avant de lancer ce test.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur lors de la récupération de l\'article : {e}'))
            return

        # Test de génération de résumé
        self.stdout.write(self.style.SUCCESS('\n--- Test de Génération de Résumé ---'))
        try:
            summary = generate_summary(article.content)
            self.stdout.write(f'Résumé généré : {summary}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur de génération de résumé : {e}'))

        # Test de suggestion de tags
        self.stdout.write(self.style.SUCCESS('\n--- Test de Suggestion de Tags ---'))
        try:
            suggested_tags = suggest_tags(article.content)
            self.stdout.write('Tags suggérés :')
            for tag in suggested_tags:
                self.stdout.write(f'- {tag}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur de suggestion de tags : {e}'))

        # Test de correction grammaticale
        self.stdout.write(self.style.SUCCESS('\n--- Test de Correction Grammaticale ---'))
        try:
            grammar_corrections = grammar_check(article.content)
            if grammar_corrections:
                self.stdout.write('Corrections grammaticales :')
                for correction in grammar_corrections:
                    self.stdout.write(f'- {correction["original"]} → {correction["correction"]}')
            else:
                self.stdout.write('Aucune correction grammaticale suggérée.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur de correction grammaticale : {e}'))

        # Test de détection de langue et complexité
        self.stdout.write(self.style.SUCCESS('\n--- Test de Détection de Langue et Complexité ---'))
        try:
            language_complexity = detect_language_complexity(article.content)
            self.stdout.write(f'Langue détectée : {language_complexity["language"]}')
            self.stdout.write(f'Score de complexité : {language_complexity["complexity_score"]}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur de détection de langue : {e}'))

        # Mise à jour automatique de l'article
        self.stdout.write(self.style.SUCCESS('\n--- Mise à Jour Automatique de l\'Article ---'))
        try:
            # Générer un résumé
            article.ai_summary = generate_summary(article.content)
            
            # Suggérer des tags
            suggested_tags = suggest_tags(article.content)
            article.ai_suggested_tags = ', '.join(suggested_tags)
            
            # Ajouter les tags suggérés
            for tag_name in suggested_tags:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                article.tags.add(tag)
            
            # Corrections grammaticales
            article.ai_grammar_corrections = grammar_check(article.content)
            
            # Détection de langue
            language_info = detect_language_complexity(article.content)
            article.language = language_info['language']
            article.complexity_score = language_info['complexity_score']
            
            article.save()
            self.stdout.write(self.style.SUCCESS('Article mis à jour avec succès !'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur de mise à jour de l\'article : {e}'))
