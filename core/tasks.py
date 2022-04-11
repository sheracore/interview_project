from celery import shared_task


@shared_task(bind=True, name='core.tasks.set_splash')
def set_splash(self):
    from core.models.system import System

    System.set_splash()


@shared_task(name='core.tasks.send_email')
def send_email(subject, body, recipient_list):
    from django.core.mail.backends.smtp import EmailBackend
    from django.core.mail import send_mail
    from core.models.system import System

    settings_ = System.get_settings()
    email_host = settings_['email_host']
    email_user = settings_['email_user']
    email_password = System.decrypt_password(settings_['email_password'])
    email_port = settings_['email_port']

    conn = EmailBackend(host=email_host, port=email_port,
                        username=email_user, password=email_password)
    send_mail(subject, '', email_user, recipient_list, connection=conn, html_message=body)
