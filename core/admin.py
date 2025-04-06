from django.contrib import admin
from .models import (
    User, Permission, UserPermission, Panelist, Interest, Campaign, Form, Section,
    Question, QuestionOption, PanelistResponse, Feedback, AIAnalysis, Announcer, 
    PanelistCampaign, Product, ScoreHistory, ConditionalLogic,Badge
)


# ✅ Enregistrer les modèles basiques sans duplication
admin.site.register(User)
admin.site.register(Permission)
admin.site.register(UserPermission)
admin.site.register(Interest)
admin.site.register(Feedback)
admin.site.register(AIAnalysis)
admin.site.register(PanelistCampaign)
admin.site.register(Product)
admin.site.register(ScoreHistory)
admin.site.register(Badge)


# ✅ Ajout d'une meilleure gestion pour les panélistes
@admin.register(Panelist)
class PanelistAdmin(admin.ModelAdmin):
    list_display = ("full_name", "gender", "birthday", "location")
    search_fields = ("full_name", "location")
    list_filter = ("gender", "location")

# ✅ Ajout d'une meilleure gestion pour les annonceurs
@admin.register(Announcer)
class AnnouncerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "location", "phone_number")
    search_fields = ("company_name", "location")

# ✅ Gestion améliorée des campagnes
@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "announcer", "start_date", "end_date", "status", "max_panelists")
    list_filter = ("status", "start_date")
    search_fields = ("name", "announcer__company_name")

# ✅ Gestion des formulaires avec sections et questions
@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("title", "campaign", "announcer", "editable")
    search_fields = ("title", "campaign__name", "announcer__company_name")

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "form", "order")
    search_fields = ("title", "form__title")
    ordering = ("order",)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "form", "question_type", "is_required", "order")
    list_filter = ("question_type", "is_required")
    search_fields = ("text", "form__title")

@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ("value", "question")
    search_fields = ("value", "question__text")

@admin.register(PanelistResponse)
class PanelistResponseAdmin(admin.ModelAdmin):
    list_display = ("panelist", "question", "content")
    search_fields = ("panelist__full_name", "question__text")


# ✅ Ajout de la gestion des conditions logiques pour les questions
@admin.register(ConditionalLogic)
class ConditionalLogicAdmin(admin.ModelAdmin):
    list_display = ("question", "trigger_question", "trigger_value")
    search_fields = ("question__text", "trigger_question__text")