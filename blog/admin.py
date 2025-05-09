from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import Article, Category, Tag, Comment, Profile, ProfileField
from .moderation_policy import ModerationPolicy
from .moderation_logs import log_moderation_action
from django.urls import reverse
from django.contrib import messages

class ArticleInline(admin.TabularInline):
    model = Article
    extra = 0
    readonly_fields = ('title', 'created_at', 'status')
    can_delete = False

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('content', 'is_approved', 'is_spam')
    can_delete = True

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ArticleInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(articles_count=Count('articles'))

    def article_count(self, obj):
        return obj.articles_count
    article_count.short_description = 'Nombre d\'Articles'
    article_count.admin_order_field = 'articles_count'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ("title", "category", "created_at", "slug", "tag_list")
    list_filter = ("category", "created_at", "tags")
    search_fields = ("title", "content")
    filter_horizontal = ("tags",)
    def tag_list(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    tag_list.short_description = "Tags"

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)

class ProfileFieldInline(admin.TabularInline):
    model = ProfileField
    extra = 1

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bio")
    search_fields = ("user__username", "bio")
    inlines = [ProfileFieldInline]
    inlines = [ProfileFieldInline]

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "name", "email", "created_at", "short_content", "validated", "is_spam", "is_reported", "parent")
    list_filter = ("validated", "is_spam", "is_reported", "created_at", "parent")
    search_fields = ("name", "email", "content")
    list_editable = ("validated", "is_reported")
    actions = ["valider_commentaires"]

    def short_content(self, obj):
        return (obj.content[:40] + '...') if len(obj.content) > 40 else obj.content
    short_content.short_description = "Contenu"

    def valider_commentaires(self, request, queryset):
        updated = queryset.update(validated=True)
        self.message_user(request, f"{updated} commentaire(s) validé(s).")
    valider_commentaires.short_description = "Valider les commentaires sélectionnés"

# Register your models here.
