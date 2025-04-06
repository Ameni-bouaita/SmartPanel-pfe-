from celery import shared_task
from django.utils.timezone import now
from .models import Campaign
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def check_and_send_reminders():
    today = now().date()
    upcoming_campaigns = Campaign.objects.filter(start_date=today + timedelta(days=1))
    ending_campaigns = Campaign.objects.filter(end_date=today + timedelta(days=1))

    for campaign in upcoming_campaigns:
        send_reminder_email(campaign.announcer.email, campaign.name, "Campaign Start", campaign.start_date)

    for campaign in ending_campaigns:
        send_reminder_email(campaign.announcer.email, campaign.name, "Campaign End", campaign.end_date)

@shared_task
def send_reminder_email(user_email, campaign_name, event_type, event_date):
    """
    Envoie un email de rappel pour un événement de campagne.
    """
    subject = f"Reminder: {event_type} for {campaign_name}"
    message = f"Hello, this is a reminder that the {event_type.lower()} for {campaign_name} is scheduled on {event_date}."
    
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [user_email])
        print(f"Reminder email sent to {user_email}")
    except Exception as e:
        print(f"Error sending reminder email: {e}")