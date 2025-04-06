from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import uuid
from django.utils.crypto import get_random_string
from django.db.utils import IntegrityError 
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
import logging
import random
import string
from django.utils import timezone


# ---- ENUMERATIONS ----
class RoleType(models.TextChoices):
    ANNOUNCER = "ANNOUNCER", "Announcer"
    PANELIST = "PANELIST", "Panelist"
    ADMIN = "ADMIN", "Admin"  

class Gender(models.TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"

class QuestionType(models.TextChoices):
    TEXT = "text", "Text Field"
    RADIO = "radio", "Radio Button"
    CHECKLIST = "checklist", "Checklist"
    RATING = "rating", "Rating Scale"
    DROPDOWN = "dropdown", "Dropdown"
    FILE_UPLOAD = "file_upload", "File Upload"
    DATE_PICKER = "date_picker", "Date Picker"
class Status(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"

# ---- BASE MODEL (Ajout des timestamps) ----
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Ensures creation timestamp
    updated_at = models.DateTimeField(auto_now=True)  # ✅ Ensures update timestamp
    class Meta:
        abstract = True  # Modèle abstrait pour héritage


class InterestManager(models.Manager):
    def filter_by_prefix(self, prefix):
        return self.filter(name__istartswith=prefix)    
# ---- INTERESTS ----
class Interest(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    objects = InterestManager()

    def __str__(self):
        return self.name
# ---- USER MODEL ----
class User(AbstractUser, BaseModel):  
    role = models.CharField(max_length=20, choices=RoleType.choices)
    email = models.EmailField(unique=True)


    def set_user_password(self, raw_password):
        """Securely hash and set the password."""
        self.set_password(raw_password)
        self.save()

    def __str__(self):
        return self.username


class Badge(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    required_score = models.IntegerField()

    def __str__(self):
        return self.name
    




class Panelist(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="panelist_profile", editable=False)
    full_name = models.CharField(max_length=100, unique=True)
    email = models.EmailField()  # ✅ Ajout email
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="panelist_pictures/", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    birthday = models.DateField()
    location = models.CharField(max_length=255)
    interests = models.ManyToManyField(Interest, related_name="panelists", blank=True)
    preferred_contact_method = models.CharField(choices=[('EMAIL', 'Email'), ('SMS', 'SMS'), ('CALL', 'Call')], max_length=10)
    availability = models.CharField(choices=[('MORNING', 'Morning'), ('EVENING', 'Evening'), ('WEEKEND', 'Weekend')], max_length=20)
    social_media_profiles = models.JSONField(blank=True, null=True)
    experience_level = models.CharField(choices=[('BEGINNER', 'Beginner'), ('EXPERIENCED', 'Experienced')], max_length=20)
    password = models.CharField(max_length=128)  # Champ pour le mot de passe
    score = models.IntegerField(default=0) 
    rank = models.CharField(max_length=50, default="Beginner")  # Rank Field
    badges = models.ManyToManyField(Badge, through='PanelistBadge', related_name='panelists', blank=True)  # Référence à PanelistBadge

    def generate_unique_username(self):
        """Génère un username unique basé sur le full_name"""
        base_username = self.full_name.lower().replace(" ", "_")
        unique_username = base_username
        count = 1

        while User.objects.filter(username=unique_username).exists():
            unique_username = f"{base_username}_{count}"
            count += 1  # Incrémente jusqu'à ce que l'username soit unique

        return unique_username

    def save(self, *args, **kwargs):
        """Crée un utilisateur automatiquement avec un username unique, email et mot de passe."""
        if not self.user_id:
            username = self.generate_unique_username()  # ✅ Utiliser un username unique
            try:
                user = User.objects.create(username=username, role=RoleType.PANELIST, email=self.email)
                user.set_password(self.password)  # ✅ Utilisation du mot de passe défini
                user.save()
                self.user = user
            except IntegrityError:
                raise ValidationError("Un utilisateur avec cet email ou ce nom d'utilisateur existe déjà.")

        super().save(*args, **kwargs)

    def update_rank(self):
        """Updates the panelist's rank based on their score."""
        ranks = {
            "Beginner": 0,
            "Bronze": 50,
            "Silver": 100,
            "Gold": 200,
            "Platinum": 500,
            "Elite": 1000
        }
        for rank, min_score in reversed(ranks.items()):
            if self.score >= min_score:
                self.rank = rank
                break
        self.save()

    def __str__(self):
        return self.full_name

# ---- ANNOUNCER ----
class Announcer(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="announcer_profile", editable=False)
    company_name = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="announcer_pictures/", blank=True, null=True)
    location = models.CharField(max_length=255)
    industry = models.CharField(choices=[('TECH', 'Tech'), ('FASHION', 'Fashion'), ('BEAUTY', 'Beauty')], max_length=50)
    company_size = models.CharField(choices=[('SMALL', 'Startup'), ('MEDIUM', 'PME'), ('LARGE', 'Multinational')], max_length=20)
    company_description = models.TextField(blank=True, null=True)
    social_media_links = models.JSONField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    password = models.CharField(max_length=128)

    def generate_unique_username(self):
        """Génère un username unique basé sur company_name"""
        base_username = self.company_name.lower().replace(" ", "_")
        unique_username = base_username
        count = 1

        while User.objects.filter(username=unique_username).exists():
            unique_username = f"{base_username}_{count}"
            count += 1

        return unique_username

    def save(self, *args, **kwargs):
        """Crée un utilisateur automatiquement avec un username unique, email et mot de passe."""
        if not self.user_id:
            username = self.generate_unique_username()
            try:
                user = User.objects.create(username=username, role=RoleType.ANNOUNCER, email=self.email)
                user.set_password(self.password)  # ✅ Utilisation du mot de passe défini
                user.save()
                self.user = user
            except IntegrityError:
                raise ValidationError("Un utilisateur avec cet email ou ce nom d'utilisateur existe déjà.")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name


# ---- PRODUCT ----   
class Product(BaseModel):
    name = models.CharField(max_length=255, unique=True)  
    description = models.TextField(blank=True, null=True)  
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)  
    category = models.CharField(
        choices=[
            ('TECH', 'Tech'),
            ('FASHION', 'Fashion'),
            ('BEAUTY', 'Beauty'),
            ('FOOD', 'Food'),
            ('HEALTH', 'Health'),
            ('OTHER', 'Other'),
        ], max_length=50, default='OTHER')  
    announcer = models.ForeignKey(Announcer, on_delete=models.CASCADE, related_name="products")  
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  
    availability_status = models.CharField(
        choices=[('IN_STOCK', 'In Stock'), ('OUT_OF_STOCK', 'Out of Stock')], max_length=20, default='IN_STOCK'
    )  
    review_score = models.FloatField(blank=True, null=True)  
    tags = models.CharField(max_length=255, blank=True, null=True)  
    website_link = models.URLField(blank=True, null=True)  

    def __str__(self):
        return f"{self.name} - {self.announcer.company_name}"

 
#----Campaign----
class Campaign(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    announcer = models.ForeignKey(Announcer, on_delete=models.CASCADE, related_name="campaigns")
    panelists = models.ManyToManyField(Panelist, blank=True, related_name="campaigns")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    max_panelists = models.IntegerField()
    is_completed = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=True)
    reward_type = models.CharField(choices=[('DISCOUNT', 'Discount'), ('GIFT', 'Gift'), ('MONEY', 'Money Transfer')], max_length=20, blank=True, null=True)
    reward_value = models.CharField(max_length=100, blank=True, null=True)
    campaign_type = models.CharField(choices=[('PRODUCT_TEST', 'Product Testing'), ('SURVEY', 'Survey')], max_length=20)
    visibility = models.CharField(choices=[('PUBLIC', 'Public'), ('PRIVATE', 'Private')], max_length=20, default='PUBLIC')
    requirements = models.TextField(blank=True, null=True)
    target_age_group = models.CharField(choices=[('18-24', '18-24'), ('25-34', '25-34'), ('35-44', '35-44'), ('45+', '45+')], max_length=10, blank=True, null=True)
    target_gender = models.CharField(choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('ANY', 'Any')], max_length=10, default='ANY')
    target_location = models.CharField(max_length=255, blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    def clean(self):
        """ Vérifier que la date de fin est après la date de début """
        if self.end_date < self.start_date:
            raise ValidationError("La date de fin doit être après la date de début.")

    def is_active(self):
        """ Vérifie si la campagne est active en fonction des dates """
        return self.start_date <= date.today() <= self.end_date

    def can_add_panelist(self):
        """ Vérifie si la campagne peut encore accepter des panélistes """
        return self.panelists.count() < self.max_panelists

    def mark_as_completed(self):
        """ Marquer la campagne comme terminée """
        self.is_completed = True
        self.save()

    def publish(self):
        """ Publier la campagne en retirant le statut brouillon """
        if self.is_draft:
            self.is_draft = False
            self.save()

    def __str__(self):
        return self.name


# ---- FORMULAIRE ----
class Form(BaseModel):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="campaign_form")
    announcer = models.ForeignKey(Announcer, on_delete=models.CASCADE, related_name="forms")
    title = models.CharField(max_length=255, unique=True, null=True) 
    editable = models.BooleanField(default=True)
    expiration_date = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return self.expiration_date and self.expiration_date < now()
    def __str__(self):
        return f"Form - {self.campaign.name}"


# ---- section ----
class Section(BaseModel):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Section: {self.title} - {self.form.title}"
# ---- questions ----
class Question(BaseModel):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="questions")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)  # Permet de gérer la suppression logique des questions

    def __str__(self):
        return f"{self.text} ({self.get_question_type_display()})"
#--- Condition---
class ConditionalLogic(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="conditional_logic")
    trigger_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="triggers", null=True, blank=True)
    trigger_value = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"If {self.trigger_question.text} = {self.trigger_value}, Show {self.question.text}"

# ---- OPTIONS DE RÉPONSE ----
class QuestionOption(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.question.text} - {self.value}"

# ---- RÉPONSES DES PANELISTES ----
class PanelistResponse(BaseModel):
    panelist = models.ForeignKey('Panelist', on_delete=models.CASCADE, related_name="panelistResponses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="panelistResponses")
    content = models.TextField(blank=True, null=True)  # Pour les champs texte
    #selected_options = models.ManyToManyField(QuestionOption, blank=True, related_name="responses")  # Pour les checkboxes & radios
    is_draft = models.BooleanField(default=True)  # ✅ Permet de sauvegarder sans soumettre

    def clean(self):
        """ Vérifie que la réponse correspond bien au type de la question associée. """
        question_type = self.question.question_type

        if question_type == QuestionType.TEXT:
            if not self.content:
                raise ValidationError("Une réponse textuelle est requise pour cette question.")
            if self.selected_options.exists():
                raise ValidationError("Les options de réponse ne sont pas autorisées pour une question texte.")

        elif question_type == QuestionType.RADIO:
            if self.selected_options.count() != 1:
                raise ValidationError("Vous devez sélectionner une seule option pour une question de type Radio.")
            if self.content:
                raise ValidationError("Le champ 'content' doit être vide pour une question de type Radio.")

        elif question_type == QuestionType.CHECKLIST:
            if self.selected_options.count() < 1:
                raise ValidationError("Vous devez sélectionner au moins une option pour une question de type Checklist.")
            if self.content:
                raise ValidationError("Le champ 'content' doit être vide pour une question de type Checklist.")

        elif question_type == QuestionType.RATING:
            try:
                rating = int(self.content)
                if not (1 <= rating <= 5):
                    raise ValidationError("La note doit être comprise entre 1 et 5 pour une question de type Rating.")
            except ValueError:
                raise ValidationError("La réponse pour une question de type Rating doit être un nombre entre 1 et 5.")

    def save(self, *args, **kwargs):
        """ Vérifie la validité avant de sauvegarder. """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Response by {self.panelist.full_name} - {self.question.text}"


# ---- FEEDBACK & ANALYSE ----
class Feedback(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedbacks")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="feedbacks")
    text = models.TextField()
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.campaign.name}"

class AIAnalysis(BaseModel):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="ai_analysis")
    results = models.JSONField()

    def __str__(self):
        return f"AI Analysis - {self.feedback.user.username}"
# ---- PERMISSIONS ----
class Permission(BaseModel):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class UserPermission(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.permission.name}"

    
# ---- PANELIST CAMPAIGN ----
class PanelistCampaign(BaseModel):
    panelist = models.ForeignKey(Panelist, on_delete=models.CASCADE, related_name="campaign_history")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="panelist_campaigns")
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected')
    ], default='PENDING')

    def __str__(self):
        return f"{self.panelist.full_name} - {self.campaign.name} ({self.status})"


logger = logging.getLogger(__name__)

def save(self, *args, **kwargs):
    """ Crée un utilisateur automatiquement et ajoute un log """
    if not self.user_id:
        try:
            user = User.objects.create(username=self.full_name.lower().replace(" ", "_"), role=RoleType.PANELIST, email=self.email)
            user.set_password(get_random_string(length=12))  # Mot de passe aléatoire sécurisé
            user.save()
            self.user = user
            logger.info(f"✅ Panelist créé : {user.username} (ID: {user.id})")
        except IntegrityError:
            logger.error(f"❌ Erreur de création : {self.email} existe déjà")
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
    super().save(*args, **kwargs)



class ScoreHistory(BaseModel):
    panelist = models.ForeignKey(Panelist, on_delete=models.CASCADE, related_name="score_history")
    action = models.CharField(max_length=100)
    points = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.panelist.full_name} - {self.action} (+{self.points})"


class PanelistBadge(BaseModel):
    panelist = models.ForeignKey(Panelist, on_delete=models.CASCADE, related_name='panelist_badges')  # Changer 'badges' par 'panelist_badges'
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.panelist.full_name} - {self.badge.name}"

# Modèle pour stocker le token de réinitialisation
class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=10)
    expired_at = models.DateTimeField(default=timezone.now)  # Make sure this field exists

    def is_expired(self):
        return timezone.now() > self.expired_at