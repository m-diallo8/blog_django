from django.core.cache import cache
from django.conf import settings
import json
import os

class ModerationPolicy:
    DEFAULT_POLICY = {
        'spam_threshold': 0.7,
        'auto_reject_links_count': 3,
        'offensive_words_list': [
            'spam', 'viagra', 'bitcoin', 'escroquerie', 
            'arnaque', 'vente', 'promotion', 'publicité'
        ],
        'enable_auto_moderation': True,
        'max_comment_length': 500,
        'min_words_count': 3,
        'block_new_users': False,
        'block_users_with_multiple_reports': True,
        'max_reports_before_block': 3
    }

    @classmethod
    def get_policy(cls):
        """
        Récupère la politique de modération, soit depuis le cache, 
        soit depuis un fichier de configuration, sinon utilise la politique par défaut
        """
        # Essayer de charger depuis un fichier de configuration
        config_path = os.path.join(settings.BASE_DIR, 'moderation_config.json')
        
        try:
            with open(config_path, 'r') as f:
                stored_policy = json.load(f)
                return {**cls.DEFAULT_POLICY, **stored_policy}
        except (FileNotFoundError, json.JSONDecodeError):
            # Utiliser la politique par défaut
            return cls.DEFAULT_POLICY

    @classmethod
    def update_policy(cls, new_policy):
        """
        Met à jour la politique de modération
        
        Args:
            new_policy (dict): Nouvelle configuration de politique
        """
        # Fusionner avec la politique par défaut
        updated_policy = {**cls.DEFAULT_POLICY, **new_policy}
        
        # Sauvegarder dans un fichier de configuration
        config_path = os.path.join(settings.BASE_DIR, 'moderation_config.json')
        
        try:
            with open(config_path, 'w') as f:
                json.dump(updated_policy, f, indent=4)
            
            return updated_policy
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la politique : {e}")
            return None

    @classmethod
    def check_comment(cls, comment_text, user=None):
        """
        Vérifie un commentaire selon la politique de modération
        
        Args:
            comment_text (str): Texte du commentaire
            user (User, optional): Utilisateur qui poste le commentaire
        
        Returns:
            dict: Résultat de la vérification
        """
        policy = cls.get_policy()
        result = {
            'is_valid': True,
            'reasons': []
        }

        # Vérification de la longueur
        if len(comment_text) > policy['max_comment_length']:
            result['is_valid'] = False
            result['reasons'].append('Commentaire trop long')

        # Vérification du nombre de mots
        words = comment_text.split()
        if len(words) < policy['min_words_count']:
            result['is_valid'] = False
            result['reasons'].append('Commentaire trop court')

        # Vérification des mots offensants
        offensive_words = [word for word in policy['offensive_words_list'] if word.lower() in comment_text.lower()]
        if offensive_words:
            result['is_valid'] = False
            result['reasons'].append(f'Mots offensants détectés : {", ".join(offensive_words)}')

        # Vérification des liens
        import re
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', comment_text)
        if len(links) > policy['auto_reject_links_count']:
            result['is_valid'] = False
            result['reasons'].append(f'Trop de liens détectés : {len(links)}')

        return result
