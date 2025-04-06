from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_survey_completed_email(user, survey):
    """
    Sends a thank-you email to the user after completing a survey.
    """
    subject = "Thank you for completing the survey!"
    html_message = render_to_string('emails/survey_completed.html', {'user': user, 'survey': survey})
    plain_message = strip_tags(html_message)  # Strips the HTML tags from the email body.
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,  # Sender email
        [user.email],  # Recipient email
        html_message=html_message,  # Send the HTML version
    )

def send_answer_submitted_email(user, campaign, answer):
    """
    Sends an email after a panelist submits an answer to a question in a campaign.
    """
    subject = "Thank you for your response!"
    html_message = render_to_string('emails/answer_submitted.html', {'user': user, 'campaign': campaign, 'answer': answer})
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_message,
    )
