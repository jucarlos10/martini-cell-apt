import os

import resend
from django.core.exceptions import ImproperlyConfigured


def send_email(to, subject, html):
    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        raise ImproperlyConfigured(
            "La variable de entorno RESEND_API_KEY no está configurada."
        )

    resend.api_key = api_key

    params: resend.Emails.SendParams = {
        "from": os.getenv(
            "RESEND_FROM_EMAIL",
            "Martini Cell <onboarding@resend.dev>",
        ),
        "to": [to],
        "subject": subject,
        "html": html,
    }

    return resend.Emails.send(params)