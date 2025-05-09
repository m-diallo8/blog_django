import os
import openai
import spacy
import nltk
from textblob import TextBlob
from langdetect import detect

# Configuration OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY', '')

# Charger les modèles NLP
nlp = spacy.load('fr_core_news_sm')
nltk.download('punkt')

def generate_summary(text, max_length=300):
    """
    Générer un résumé d'article avec OpenAI
    """
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Résume ce texte de manière concise en moins de {max_length} caractères :\n\n{text}",
            max_tokens=max_length,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        # Fallback : résumé extractif avec spaCy
        doc = nlp(text)
        sentences = [sent.text for sent in doc.sents]
        return ' '.join(sentences[:3])

def suggest_tags(text, max_tags=5):
    """
    Suggérer des tags automatiquement
    """
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Extrais les {max_tags} mots-clés principaux de ce texte :\n\n{text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        tags = [tag.strip() for tag in response.choices[0].text.split(',')]
        return tags[:max_tags]
    except Exception as e:
        # Fallback : extraction de noms avec spaCy
        doc = nlp(text)
        tags = [ent.text for ent in doc.ents if ent.label_ in ['ORG', 'PERSON', 'PRODUCT']]
        return list(set(tags))[:max_tags]

def grammar_check(text):
    """
    Vérification grammaticale assistée par IA
    """
    try:
        response = openai.Edit.create(
            engine="text-davinci-edit-001",
            input=text,
            instruction="Corrige les erreurs grammaticales et orthographiques en français",
            temperature=0.1,
            top_p=1.0
        )
        corrections = response.choices[0].text

        # Comparaison des différences
        original_tokens = nltk.word_tokenize(text)
        corrected_tokens = nltk.word_tokenize(corrections)
        
        diff_corrections = []
        for orig, corr in zip(original_tokens, corrected_tokens):
            if orig != corr:
                diff_corrections.append({
                    'original': orig,
                    'correction': corr
                })
        
        return diff_corrections
    except Exception as e:
        # Fallback : correction basique avec TextBlob
        blob = TextBlob(text)
        corrections = blob.correct()
        return [{
            'original': word,
            'correction': corrected
        } for word, corrected in zip(text.split(), str(corrections).split()) if word != corrected]

def detect_language_complexity(text):
    """
    Détecter la langue et calculer la complexité
    """
    try:
        # Détection de langue
        lang = detect(text)
        
        # Calcul de complexité
        blob = TextBlob(text)
        complexity = (
            len(blob.words) / 100 +  # Longueur
            len(set(blob.words)) / len(blob.words) +  # Diversité
            abs(blob.sentiment.polarity)  # Complexité émotionnelle
        ) / 3
        
        return {
            'language': lang,
            'complexity_score': min(max(complexity, 0), 1)
        }
    except Exception as e:
        return {
            'language': 'fr',
            'complexity_score': 0.5
        }
