from django import forms
from .models import NewsletterSubscriber, Article, Category, Tag, ReadingPreference

class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email', 'name']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Votre adresse email',
                'required': 'required'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Votre nom (optionnel)'
            })
        }
        labels = {
            'email': 'Adresse email',
            'name': 'Nom (optionnel)'
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Vérifier si l'email existe déjà
        if NewsletterSubscriber.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("Cet email est déjà abonné à la newsletter.")
        return email

class ReadingPreferenceForm(forms.ModelForm):
    class Meta:
        model = ReadingPreference
        fields = ['font_size', 'contrast_mode', 'line_height', 'reading_width']
        widgets = {
            'font_size': forms.Select(attrs={'class': 'form-control'}),
            'contrast_mode': forms.Select(attrs={'class': 'form-control'}),
            'line_height': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1', 
                'min': '1', 
                'max': '2.5'
            }),
            'reading_width': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '5', 
                'min': '50', 
                'max': '100'
            })
        }
        labels = {
            'font_size': 'Taille de police',
            'contrast_mode': 'Mode de contraste',
            'line_height': 'Hauteur de ligne',
            'reading_width': 'Largeur de lecture (%)',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        # Créer ou mettre à jour les préférences
        instance, created = ReadingPreference.objects.get_or_create(
            user=self.user,
            defaults=self.cleaned_data
        )
        
        if not created:
            # Mettre à jour les préférences existantes
            for key, value in self.cleaned_data.items():
                setattr(instance, key, value)
            instance.save()
        
        return instance

class AdvancedSearchForm(forms.Form):
    query = forms.CharField(
        label='Recherche',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Mots-clés de recherche'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label='Catégorie',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        label='Tags',
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2', 
            'multiple': 'multiple'
        })
    )
    
    start_date = forms.DateField(
        label='Date de début',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker', 
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        label='Date de fin',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker', 
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Vérifier la cohérence des dates
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La date de début doit être antérieure à la date de fin.")
        
        return cleaned_data
    
    def get_corrected_query(self):
        # Correction orthographique
        spell = SpellChecker(language='fr')
        query = self.cleaned_data.get('query', '')
        
        # Correction des mots mal orthographiés
        corrected_words = [spell.correction(word) for word in query.split()]
        return ' '.join(corrected_words)

class DraftArticleForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=False
    )
    
    class Meta:
        model = Article
        fields = ['title', 'content', 'category', 'tags', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de l\'article'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Contenu de l\'article', 
                'rows': 10
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        # Forcer l'article à être un brouillon
        instance = super().save(commit=False)
        instance.is_published = False
        instance.author = self.user
        
        if commit:
            instance.save()
            # Sauvegarder les tags
            self.save_m2m()
        
        return instance
