from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send(subject, body, recipient_list, from_email=settings.EMAIL_HOST_USER):
    msg = EmailMultiAlternatives(subject, body, from_email=from_email, to=recipient_list)
    msg.attach_alternative(body, "text/html")
    msg.send()
