import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_password_reset_email(email: str, token: str) -> bool:
    if not settings.smtp_host:
        return False
    message = EmailMessage()
    message["Subject"] = "Reset your Brightloop password"
    message["From"] = settings.smtp_from
    message["To"] = email
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    message.set_content(f"Use this link to reset your Brightloop password. It expires in {settings.reset_token_expire_minutes} minutes:\n\n{reset_url}")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return True
