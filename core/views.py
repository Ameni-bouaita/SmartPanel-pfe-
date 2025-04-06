from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login, User as AuthUser
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Q
from .models import User, Panelist, Announcer, Interest, Campaign, PanelistResponse, ScoreHistory, Question, Form, Section, PasswordResetToken, RoleType, PasswordResetToken
from .serializers import UserSerializer, PanelistSerializer, AnnouncerSerializer, InterestSerializer, QuestionSerializer
from .utils import update_panelist_score
import logging
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from .tasks import send_reminder_email
from .permissions import IsAdmin
from django.contrib.auth.decorators import login_required, permission_required
from django.forms import modelform_factory, inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
import random
import json
import string  
from django.utils import timezone
from django.contrib.auth.hashers import make_password



logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    """
    Vue pour gérer la connexion et la génération des tokens JWT.
    """
    pass

def get_tokens_for_user(user):
    """
    Génère un token JWT (refresh + access) pour un utilisateur authentifié.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserViewSet(viewsets.ModelViewSet):
    """
    API permettant de gérer les utilisateurs (CRUD)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

def send_verification_email(user, request):
    try:
        token = default_token_generator.make_token(user)
        uid = user.pk
        current_site = get_current_site(request)
        mail_subject = "Activate your account"
        message = f"Hi {user.username}, please click the link to activate your account: http://{current_site.domain}/activate/{uid}/{token}/"
        
        send_mail(mail_subject, message, settings.EMAIL_HOST_USER, [user.email])

        logger.info(f"Email de vérification envoyé à {user.email}")

    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de vérification : {e}")

# ---- SIGNUP (INSCRIPTION) ----

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    try:
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        if not username or not email or not password or not role:
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password, role=role)

        # Optionally send activation email
        # send_verification_email(user, request)

        return Response({
            "message": "User created successfully"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def signin(request):
    data = request.data
    identifier = data.get('username')  # Peut être email ou username
    password = data.get('password')

    if not identifier or not password:
        return Response({"error": "Nom d'utilisateur/email et mot de passe requis"}, status=400)

    User = get_user_model()

    # Essayer username puis email
    try:
        user_obj = User.objects.get(username=identifier)
    except User.DoesNotExist:
        try:
            user_obj = User.objects.get(email=identifier)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé"}, status=404)

    # Authentification via username interne
    user = authenticate(username=user_obj.username, password=password)

    if user is None:
        return Response({"error": "Mot de passe incorrect"}, status=401)

    if not user.is_active:
        return Response({"error": "Compte désactivé"}, status=403)
 
    # ✅ DEBUG temporaire
    print("UTILISATEUR CONNECTÉ :", user.username)
    print("RÔLE :", user.role)

    # Token JWT
    refresh = RefreshToken.for_user(user)
    return Response({
        "message": "Connexion réussie",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role  # ✅ AJOUTE BIEN CECI

        }
    })


# ---- OBTENIR UN NOUVEAU TOKEN D'ACCÈS ----
@api_view(['POST'])
def get_token(request):
    """
    Renouvelle le token d'accès avec un refresh token.
    """
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response({"error": "Refresh token requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            "access": str(refresh.access_token)
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "Token invalide ou expiré"}, status=status.HTTP_401_UNAUTHORIZED)


# ---- LISTE DES INTÉRÊTS ----
class InterestViewSet(viewsets.ModelViewSet):
    queryset = Interest.objects.all()
    serializer_class = InterestSerializer


# ---- LISTE DES PANELISTES ----
class PanelistViewSet(viewsets.ModelViewSet):
    queryset = Panelist.objects.all()
    serializer_class = PanelistSerializer


# ---- LISTE DES ANNONCEURS ----
class AnnouncerViewSet(viewsets.ModelViewSet):
    queryset = Announcer.objects.all()
    serializer_class = AnnouncerSerializer


# ---- ENDPOINT PROTÉGÉ POUR TESTER JWT ----
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def protected_view(request):
    """
    Test d'un endpoint sécurisé nécessitant un token JWT valide
    """
    return Response({"message": f"Bienvenue {request.user.username}, votre rôle est {request.user.role}"})



def activate_email(request, uid, token):
    try:
        user = get_user_model().objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return HttpResponse('Your email has been confirmed.')
        else:
            return HttpResponse('Invalid or expired token.')
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}')



@api_view(['POST'])
def get_new_access_token(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            "access": str(refresh.access_token)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request):
    logger.info(f"Request data: {request.data}")
    logger.info(f"User: {request.user}")
    """
    Soumettre une réponse à une question dans une campagne
    """
    # Récupérer les données de la requête
    data = request.data
    campaign_id = data.get('campaign_id')
    question_id = data.get('question_id')
    answer = data.get('answer')

    # Vérification des champs nécessaires
    if not campaign_id or not question_id or not answer:
        return Response({"error": "Les champs campagne, question et réponse sont obligatoires."}, status=400)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
        question = Question.objects.get(id=question_id)
    except (Campaign.DoesNotExist, Question.DoesNotExist):
        return Response({"error": "Campagne ou question non trouvée."}, status=404)

    response = PanelistResponse.objects.create(
    panelist=request.user.panelist_profile,
    question=question,
    content=answer
    )

    return DRFResponse({"message": "Réponse soumise avec succès."}, status=200)

def send_answer_submitted_email(user, campaign, answer):
    """ Envoi de l'email après soumission d'une réponse """
    subject = f"Merci pour votre réponse à la campagne {campaign.name}"
    message = f"Bonjour {user.username},\n\nMerci d'avoir répondu à la question dans la campagne {campaign.name}.\n\nVotre réponse : {answer}\n\nCordialement,\nL'équipe SmartPanel."
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)


def send_reminder_email(user_email, campaign_name, event_type, event_date):
    """
    Send a reminder email for an upcoming campaign event (start/end).
    """
    subject = f"Reminder: {event_type} for {campaign_name}"
    message = f"Hello,\n\nThis is a reminder that the {event_type.lower()} for '{campaign_name}' is scheduled on {event_date}.\n\nThank you!"
    
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [user_email])
        logger.info(f"✅ Reminder email sent to {user_email} for {campaign_name} ({event_type})")
    except Exception as e:
        logger.error(f"❌ Error sending reminder email: {e}")

"""

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_response(request):
    user = request.user

    if user.role != "PANELIST":
        return Response({"error": "Only panelists can submit responses."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    question_id = data.get("question_id")
    answer_content = data.get("answer")

    try:
        question = Question.objects.get(id=question_id)
        response = Response.objects.create(
            panelist=user.panelist_profile,
            question=question,
            content=answer_content,
            is_draft=False
        )
        response.save()

        # ✅ Award points for submitting a response
        update_panelist_score(user.panelist_profile, "submit_response")

        return Response({
            "message": "Response submitted successfully",
            "new_score": user.panelist_profile.score
        }, status=status.HTTP_201_CREATED)
    
    except Question.DoesNotExist:
        return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
"""

def get_weekly_leaderboard():
    """ Returns the top 5 panelists for the current week """
    start_of_week = now() - timedelta(days=now().weekday())

    return Panelist.objects.annotate(
        weekly_score=Sum(
            'scorehistory__points',  # Vérifie si "scorehistory" est bien la related_name de ScoreHistory
            filter=Q(scorehistory__timestamp__gte=start_of_week)
        )
    ).order_by('-weekly_score')[:5]

@api_view(['GET'])
def leaderboard(request):
    """ Get the overall leaderboard """
    top_panelists = Panelist.objects.order_by('-score')[:10]
    data = [{"id": p.id, "full_name": p.full_name, "score": p.score} for p in top_panelists]
    return Response({"leaderboard": data})

@api_view(['GET'])
def weekly_leaderboard(request):
    """ Get the weekly leaderboard """
    top_panelists = get_weekly_leaderboard()
    data = [{"id": p.id, "full_name": p.full_name, "weekly_score": p.weekly_score or 0} for p in top_panelists]
    return Response({"weekly_leaderboard": data})


class PanelistDetailView(APIView):
    permission_classes = [IsAuthenticated]  # Assurez-vous que seul un utilisateur authentifié peut accéder

    def get(self, request, pk):
        # Récupérer le paneliste par son ID
        try:
            panelist = Panelist.objects.get(id=pk)
        except Panelist.DoesNotExist:
            return Response({"error": "Panelist not found"}, status=404)

        # Récupérer les badges associés au paneliste
        badges = panelist.badges.all()

        # Sérialiser les données du paneliste et des badges
        return Response({
            'panelist': PanelistSerializer(panelist).data,
            'badges': [badge.name for badge in badges]  # Liste des badges
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_question(request, form_id):
    """Permet aux annonceurs d'ajouter des questions à un formulaire existant"""
    form = Form.objects.get(id=form_id)
    if request.user != form.announcer.user:
        return Response({"error": "Vous n'êtes pas autorisé à modifier ce formulaire."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    question = Question.objects.create(
        form=form,
        text=data.get('text'),
        question_type=data.get('question_type'),
        is_required=data.get('is_required', True),
        order=data.get('order', 0),
        is_active=True
    )
    return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_question(request, question_id):
    """Permet de mettre à jour une question"""
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return Response({"error": "Question non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    if request.user != question.form.announcer.user:
        return Response({"error": "Vous n'êtes pas autorisé à modifier cette question."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    question.text = data.get('text', question.text)
    question.question_type = data.get('question_type', question.question_type)
    question.is_required = data.get('is_required', question.is_required)
    question.save()
    return Response(QuestionSerializer(question).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Assure-toi que seul un utilisateur authentifié peut appeler cette vue
def test_send_reminder_email(request):
    """
    Test de l'envoi d'un email de rappel via Celery.
    """
    # Données de test (peut être paramétré via request.data dans une vraie utilisation)
    user_email = "panelist@example.com"  # Email du destinataire
    campaign_name = "Test Campaign"
    event_type = "Start"
    event_date = "2025-06-01"

    # Appel de la tâche Celery
    send_reminder_email(user_email, campaign_name, event_type, event_date)

    return Response({"message": "Reminder email task enqueued"})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])  # ✅ Seuls les Admins peuvent voir les utilisateurs
def list_users(request):
    """
    Liste tous les utilisateurs de la plateforme.
    """
    users = User.objects.all()
    return Response({"users": UserSerializer(users, many=True).data})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmin])
def delete_user(request, user_id):
    """
    Supprime un utilisateur (Uniquement pour les admins).
    """
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return Response({"message": "Utilisateur supprimé avec succès"}, status=200)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)
    


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def create_admin(request):
    """
    ✅ Crée un nouvel administrateur.
    """
    data = request.data
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return Response({"error": "Tous les champs sont obligatoires"}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Cet email est déjà utilisé"}, status=400)

    admin_user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        role="ADMIN"
    )
    return Response({"message": f"Admin {admin_user.username} créé avec succès !"}, status=201)

# Étape 1 - Créer un formulaire
@permission_required('core.add_form')
def create_form_view(request):
    try:
        announcer = request.user.announcer_profile
    except ObjectDoesNotExist:
        messages.error(request, "Vous devez avoir un profil annonceur pour créer un formulaire.")
        return redirect('admin:index')  # Ou une autre page plus appropriée

    if request.method == 'POST':
        form = Form.objects.create(
            campaign_id=request.POST.get('campaign'),
            announcer=announcer,
            title=request.POST.get('title'),
            expiration_date=request.POST.get('expiration_date')
        )
        return redirect('add_sections', form_id=form.id)

    campaigns = Campaign.objects.filter(announcer=announcer)
    return render(request, 'core/create_form.html', {'campaigns': campaigns})

# Étape 2 - Ajouter des sections au formulaire
@permission_required('core.add_section')
def add_sections_view(request, form_id):
    form = get_object_or_404(Form, id=form_id)

    if request.method == 'POST':
        Section.objects.create(
            form=form,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            order=request.POST.get('order', 0)
        )
        return redirect('add_sections', form_id=form.id)

    sections = Section.objects.filter(form=form).order_by('order')
    return render(request, 'core/add_sections.html', {
        'form': form,
        'sections': sections
    })

# Étape 3 - Ajouter des questions dans une section
@permission_required('core.add_question')
def add_questions_view(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        Question.objects.create(
            form=section.form,
            section=section,
            text=request.POST.get('text'),
            question_type=request.POST.get('question_type'),
            is_required=request.POST.get('is_required') == 'on',
            order=request.POST.get('order', 0)
        )
        return redirect('add_questions', section_id=section.id)

    questions = Question.objects.filter(section=section).order_by('order')
    return render(request, 'core/add_questions.html', {
        'section': section,
        'questions': questions
    })



def create_form(request):
    return render(request, 'core/create_form.html')

def add_sections(request, form_id):
    return render(request, 'core/add_sections.html', {'form_id': form_id})

def add_questions(request, section_id):
    return render(request, 'core/add_questions.html', {'section_id': section_id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_campaign(request):
    """
    Crée une nouvelle campagne
    """
    try:
        # Vérifier si l'utilisateur a un profil d'annonceur
        if not hasattr(request.user, 'announcer_profile'):
            return Response({"error": "L'utilisateur n'a pas de profil d'annonceur."}, status=status.HTTP_400_BAD_REQUEST)

        announcer = request.user.announcer_profile  # Profil d'annonceur de l'utilisateur connecté

        data = request.data
        name = data.get('name')
        description = data.get('description')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        max_panelists = data.get('max_panelists')

        if not name or not description or not start_date or not end_date or not max_panelists:
            return Response({"error": "Tous les champs sont requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Créer la campagne
        campaign = Campaign.objects.create(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            max_panelists=max_panelists,
            announcer=announcer  # Associer l'annonceur à la campagne
        )

        return Response({
            "message": "Campagne créée avec succès",
            "campaign": {"id": campaign.id, "name": campaign.name}
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error during campaign creation: {str(e)}")
        return Response({"error": f"Une erreur est survenue : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Retourne les informations du profil de l'utilisateur en fonction de son rôle.
    """
    if request.user.role == 'ANNOUNCER':
        announcer = request.user.announcer_profile
        return Response({
            'company_name': announcer.company_name,
            'industry': announcer.industry,
            'email': request.user.email,
        })
    elif request.user.role == 'PANELIST':
        panelist = request.user.panelist_profile
        return Response({
            'full_name': panelist.full_name,
            'location': panelist.location,
            'email': request.user.email,
        })
    else:
        return Response({'error': 'Role non défini'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def panelist_signup(request):
    try:
        print("Requête reçue :", request.data)

        data = request.data
        email = data.get('email')
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        profile_picture = request.FILES.get('profile_picture')
        gender = data.get('gender')
        birthday = data.get('birthday')
        location = data.get('location')
        preferred_contact_method = data.get('preferred_contact_method')
        availability = data.get('availability')
        experience_level = data.get('experience_level')
        interests = data.get('interests')

        # Validation des champs requis
        if not email or not full_name or not gender or not birthday or not location:
            return Response({"error": "Champs requis manquants"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé avec cet email."}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(user, 'panelist_profile'):
            return Response({"error": "Ce compte a déjà un profil panelist."}, status=status.HTTP_400_BAD_REQUEST)

        # Création du panelist
        panelist = Panelist.objects.create(
            user=user,
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            profile_picture=profile_picture,
            gender=gender,
            birthday=birthday,
            location=location,
            preferred_contact_method=preferred_contact_method,
            availability=availability,
            experience_level=experience_level,
        )

        # 🔎 Traitement des intérêts (liés à des objets existants)
        if interests:
            if isinstance(interests, str):
                interest_list = [i.strip() for i in interests.split(",")]
            else:
                interest_list = interests

            for int_name in interest_list:
                try:
                    interest_obj = Interest.objects.get(name=int_name)
                    panelist.interests.add(interest_obj)
                except Interest.DoesNotExist:
                    return Response({"error": f"L'intérêt '{int_name}' n'existe pas."}, status=400)

        return Response({"message": "Profil Panelist créé avec succès"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Erreur :", str(e))
        return Response({"error": f"Erreur serveur : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def announcer_signup(request):
    try:
        print("Requête reçue :", request.data)

        data = request.data
        email = data.get('email')
        password = data.get('password')  # optionnel, pour hash et vérif si besoin
        company_name = data.get('company_name')
        phone_number = data.get('phone_number')
        profile_picture = request.FILES.get('profile_picture')
        location = data.get('location')
        industry = data.get('industry')
        company_size = data.get('company_size')
        company_description = data.get('company_description')
        website = data.get('website')
        social_media_links = data.get('social_media_links')

        # Validation basique
        if not email or not company_name or not location or not industry or not company_size:
            return Response({"error": "Champs requis manquants"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé avec cet email."}, status=404)

        if hasattr(user, 'announcer_profile'):
            return Response({"error": "Ce compte a déjà un profil annonceur."}, status=400)

        # Création de l’annonceur
        announcer = Announcer.objects.create(
            user=user,
            email=email,
            password=password,  # ne sera pas utilisé pour authentification, juste stockage si besoin
            company_name=company_name,
            phone_number=phone_number,
            profile_picture=profile_picture,
            location=location,
            industry=industry,
            company_size=company_size,
            company_description=company_description,
            website=website,
            social_media_links=social_media_links  # doit être un JSON ou None
        )

        return Response({"message": "Profil Annonceur créé avec succès"}, status=201)

    except Exception as e:
        print("Erreur :", str(e))
        return Response({"error": f"Erreur serveur : {str(e)}"}, status=500)




@api_view(['GET'])
@permission_classes([AllowAny])
def list_interests(request):
    interests = Interest.objects.all().values('id', 'name')
    return Response(interests)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def panelist_me(request):
    try:
        panelist = request.user.panelist_profile
    except:
        return Response({"error": "Aucun profil panelist trouvé"}, status=404)

    if request.method == 'GET':
        data = {
            "full_name": panelist.full_name,
            "email": panelist.email,
            "phone_number": panelist.phone_number,
            "location": panelist.location,
            "gender": panelist.gender,
            "birthday": panelist.birthday,
            "preferred_contact_method": panelist.preferred_contact_method,
            "availability": panelist.availability,
            "experience_level": panelist.experience_level,
            "social_media_profiles": panelist.social_media_profiles,
            "interests": [i.name for i in panelist.interests.all()],
            "profile_picture": panelist.profile_picture.url if panelist.profile_picture else None,
        }
        return Response(data)

    if request.method == 'PATCH':
        for attr in [
            'full_name', 'email', 'phone_number', 'location', 'gender',
            'preferred_contact_method', 'availability', 'experience_level', 'social_media_profiles'
        ]:
            if attr in request.data:
                setattr(panelist, attr, request.data[attr])

        if 'interests' in request.data:
            panelist.interests.clear()
            for name in request.data['interests']:
                try:
                    interest = Interest.objects.get(name=name)
                    panelist.interests.add(interest)
                except Interest.DoesNotExist:
                    continue

        if 'profile_picture' in request.FILES:
            panelist.profile_picture = request.FILES['profile_picture']

        panelist.save()
        return Response({"message": "Profil mis à jour avec succès"})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def announcer_me(request):
    try:
        announcer = request.user.announcer_profile
    except:
        return Response({"error": "Aucun profil annonceur trouvé"}, status=404)

    if request.method == 'GET':
        data = {
            "company_name": announcer.company_name,
            "email": announcer.email,
            "phone_number": announcer.phone_number,
            "location": announcer.location,
            "industry": announcer.industry,
            "company_size": announcer.company_size,
            "company_description": announcer.company_description,
            "social_media_links": announcer.social_media_links,
            "website": announcer.website,
            "profile_picture": announcer.profile_picture.url if announcer.profile_picture else None,
        }
        return Response(data)

    if request.method == 'PATCH':
        for attr in [
            'company_name', 'email', 'phone_number', 'location',
            'industry', 'company_size', 'company_description',
            'social_media_links', 'website'
        ]:
            if attr in request.data:
                setattr(announcer, attr, request.data[attr])

        if 'profile_picture' in request.FILES:
            announcer.profile_picture = request.FILES['profile_picture']

        announcer.save()
        return Response({"message": "Profil mis à jour avec succès"})

# Fonction pour générer un token de réinitialisation
def generate_reset_token():
    return random.randint(1000, 9999)  # Génère un token aléatoire à 4 chiffres
# Fonction pour générer un token de réinitialisation
def generate_reset_token():
    try:
        token = random.randint(1000, 9999)  # Génère un token aléatoire à 4 chiffres
        logger.debug(f"Generated reset token: {token}")
        return token
    except Exception as e:
        logger.error(f"Error generating reset token: {e}")
        raise e

# Fonction pour envoyer un email de réinitialisation
def send_reset_email(user_email, token):
    try:
        subject = "Réinitialisation de votre mot de passe"
        message = f"Voici votre token de réinitialisation : {token}. Utilisez-le pour réinitialiser votre mot de passe."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])
        logger.debug(f"Sent reset email to {user_email} with token {token}")
    except Exception as e:
        logger.error(f"Error sending reset email to {user_email}: {e}")
        raise e

# Vue pour demander la réinitialisation du mot de passe
@api_view(['POST'])
@permission_classes([AllowAny])
def request_reset_password(request):
    try:
        data = json.loads(request.body)  # Assurez-vous que le corps est bien parsé en JSON
        email = data.get('email')

        if not email:
            logger.error("No email provided in the request")
            return JsonResponse({'message': 'Email est requis'}, status=400)

        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found with email {email}")
        except User.DoesNotExist:
            logger.error(f"User with email {email} not found")
            return JsonResponse({'message': 'Utilisateur non trouvé'}, status=400)

        # Générer le token de réinitialisation et sa date d'expiration
        token = generate_reset_token()
        expiration_time = timezone.now() + timedelta(hours=1)  # Le token expire dans 1 heure

        # Sauvegarder le token dans la base de données
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expired_at=expiration_time
        )
        logger.debug(f"Password reset token created for user {email}: {token}")

        # Envoyer le token par email
        send_reset_email(email, token)

        return JsonResponse({'message': 'Token de réinitialisation envoyé'}, status=200)
    
    except Exception as e:
        logger.error(f"Error in request_reset_password view: {e}")
        return JsonResponse({'message': 'Une erreur est survenue'}, status=500)

# Vue pour vérifier le code de réinitialisation
@api_view(['POST'])
@permission_classes([AllowAny]) 
def verify_reset_code(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        entered_token = data.get('reset_token')

        if not email or not entered_token:
            logger.error("Missing email or reset_token in the request")
            return JsonResponse({'message': 'Email et code sont requis'}, status=400)

        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.get(user=user, token=entered_token)

            # Vérifier si le token a expiré
            if reset_token.is_expired():
                logger.warning(f"Reset token expired for user {email}")
                return JsonResponse({'message': 'Le token a expiré'}, status=400)
            
            logger.debug(f"Reset token validated for user {email}")
            return JsonResponse({'message': 'Token valide. Entrez votre nouveau mot de passe.'}, status=200)

        except (User.DoesNotExist, PasswordResetToken.DoesNotExist) as e:
            logger.error(f"Error verifying reset code for email {email}: {e}")
            return JsonResponse({'message': 'Token ou utilisateur invalide'}, status=400)
    
    except Exception as e:
        logger.error(f"Error in verify_reset_code view: {e}")
        return JsonResponse({'message': 'Une erreur est survenue'}, status=500)

# Vue pour réinitialiser le mot de passe
@api_view(['POST'])
@permission_classes([AllowAny]) 
def reset_password(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not email or not new_password or not confirm_password:
            logger.error("Missing email, new password or confirm password in the request")
            return JsonResponse({'message': 'Tous les champs sont requis'}, status=400)

        if new_password != confirm_password:
            logger.error("Passwords do not match")
            return JsonResponse({'message': 'Les mots de passe ne correspondent pas'}, status=400)

        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found with email {email}")
            user.password = make_password(new_password)  # Hachage du nouveau mot de passe
            user.save()

            # Supprimer le token après réinitialisation réussie
            PasswordResetToken.objects.filter(user=user).delete()
            logger.debug(f"Password reset successfully for user {email}")

            return JsonResponse({'message': 'Mot de passe réinitialisé avec succès'}, status=200)

        except User.DoesNotExist:
            logger.error(f"User with email {email} not found during password reset")
            return JsonResponse({'message': 'Utilisateur non trouvé'}, status=400)

    except Exception as e:
        logger.error(f"Error in reset_password view: {e}")
        return JsonResponse({'message': 'Une erreur est survenue'}, status=500)