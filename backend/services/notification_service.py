"""
notification_service.py — Envía notificaciones por email o webhook.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def send(rule: dict, event: dict) -> bool:
    """Envía notificación según el canal de la regla."""
    channel = rule.get("channel", "")
    if channel == "email":
        return _send_email(rule["destination"], event)
    elif channel == "webhook":
        return _send_webhook(rule["destination"], event)
    logger.warning("Canal de notificación desconocido", extra={"channel": channel})
    return False


def _send_email(to: str, event: dict) -> bool:
    """Envía email con STARTTLS. Retorna True si OK."""
    if not settings.smtp_host:
        logger.warning("SMTP no configurado — notificación email omitida")
        return False

    try:
        subject = f"[Hira SCADA] {event['event_type'].upper()} — {event['severity']}"
        body = (
            f"Evento: {event['event_type']}\n"
            f"Severidad: {event['severity']}\n"
            f"Mensaje: {event['message']}\n"
            f"Timestamp: {event.get('created_at', 'N/A')}\n"
        )
        if event.get("metadata"):
            body += f"Detalles: {event['metadata']}\n"

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(msg["From"], to, msg.as_string())

        logger.info("Email de notificación enviado", extra={"to": to, "event_type": event["event_type"]})
        return True
    except Exception as exc:
        logger.error("Error enviando email", extra={"to": to, "error": str(exc)})
        return False


def _send_webhook(url: str, event: dict) -> bool:
    """HTTP POST con httpx síncrono, timeout=10s."""
    try:
        import httpx

        payload = {
            "event_type": event.get("event_type"),
            "severity": event.get("severity"),
            "message": event.get("message"),
            "metadata": event.get("metadata"),
            "timestamp": str(event.get("created_at", "")),
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()

        logger.info("Webhook de notificación enviado", extra={"url": url, "event_type": event["event_type"]})
        return True
    except Exception as exc:
        logger.error("Error enviando webhook", extra={"url": url, "error": str(exc)})
        return False
