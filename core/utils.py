from .models import Form, Section, Question
from .models import Panelist
from django.apps import apps
from django.utils.timezone import now, timedelta
from django.db import transaction
from django.db.models import Count, Q
from .models import Badge, PanelistBadge


def duplicate_form(form_id):
    """ Duplication d'un formulaire et de ses sections/questions """
    original_form = Form.objects.get(id=form_id)
    new_form = Form.objects.create(
        campaign=original_form.campaign,
        announcer=original_form.announcer,
        title=f"{original_form.title} (copie)",
        editable=True
    )

    for section in original_form.sections.all():
        new_section = Section.objects.create(
            form=new_form, title=section.title, description=section.description, order=section.order
        )
        for question in section.questions.all():
            Question.objects.create(
                form=new_form, section=new_section, text=question.text, 
                question_type=question.question_type, is_required=question.is_required, order=question.order
            )

    return new_form


def award_badge(panelist):
    """Attribue des badges au paneliste en fonction de son score."""
    # Récupérer tous les badges définis dans la base de données
    badges = Badge.objects.all()

    for badge in badges:
        # Vérifier si le paneliste a atteint le score requis pour ce badge
        if panelist.score >= badge.required_score:
            # Vérifier s'il n'a pas déjà ce badge
            if not PanelistBadge.objects.filter(panelist=panelist, badge=badge).exists():
                # Si le paneliste n'a pas encore ce badge, on l'attribue
                PanelistBadge.objects.create(panelist=panelist, badge=badge)
                print(f"Badge {badge.name} attribué à {panelist.full_name}")



def update_panelist_score(panelist, action):
    """Mise à jour du score du panéliste, gestion des limites et historique."""

    ScoreHistory = apps.get_model('core', 'ScoreHistory')  # Lazy import pour éviter les dépendances circulaires

    points = {
        "register": 10,
        "complete_profile": 5,
        "apply_campaign": 5,
        "selected_for_campaign": 10,
        "submit_response": 20,
        "high_quality_review": 30,
        "frequent_feedback": 10,
        "refer_friend": 50,
    }

    action_limits = {
        "submit_response": {"max_per_day": 5},  # ✅ Limite : max 5 réponses par jour
        "refer_friend": {"max_per_week": 3},   # ✅ Limite : max 3 amis référés par semaine
    }

    if action not in points:
        return None  # ✅ Protection contre les actions invalides

    # Vérification des limites d'action (évite les abus)
    time_filters = {}
    if action in action_limits:
        limit = action_limits[action]
        if "max_per_day" in limit:
            time_filters["timestamp__gte"] = now() - timedelta(days=1)
        elif "max_per_week" in limit:
            time_filters["timestamp__gte"] = now() - timedelta(weeks=1)

        action_count = ScoreHistory.objects.filter(panelist=panelist, action=action, **time_filters).count()
        if action_count >= limit.get("max_per_day", limit.get("max_per_week", float('inf'))):
            return panelist.score  # ✅ Si la limite est atteinte, ne pas ajouter de points

    with transaction.atomic():  # ✅ Sécurise les modifications en base
        panelist = Panelist.objects.select_for_update().get(pk=panelist.pk)  # 🔒 Empêche les conflits de transaction
        panelist.score += points[action]
        panelist.save()
        panelist.refresh_from_db()  # 🔥 Assure que le score est bien mis à jour en base

        # ✅ Mettre à jour le rang après un gain de points
        panelist.update_rank()

        # ✅ Historiser le changement de score
        ScoreHistory.objects.create(
            panelist=panelist,
            action=action,
            points=points[action]
        )
        
    award_badge(panelist)

    return panelist.score  # ✅ Retourne le score mis à jour



def get_weekly_leaderboard():
    """Returns the top 5 panelists based on scores for the current week."""
    start_of_week = now().date() - timedelta(days=now().weekday())  # Monday
    return Panelist.objects.filter(user__date_joined__gte=start_of_week).order_by('-score')[:5]


