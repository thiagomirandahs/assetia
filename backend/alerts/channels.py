"""Canais de notificacao para alertas: e-mail (SMTP) e Telegram.

Configuracao via .env. Se as variaveis nao estiverem definidas, o canal eh
silenciosamente ignorado — assim o sistema funciona sem dependencias externas
em modo dev.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from ..core.models import Alert

logger = logging.getLogger(__name__)

ICONES = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}


def _formato_assunto(alert: Alert) -> str:
    return f"[ReconIA] {ICONES.get(alert.severidade, '•')} {alert.titulo}"


def _formato_corpo(alert: Alert) -> str:
    return (
        f"{alert.titulo}\n"
        f"{'-' * 60}\n\n"
        f"{alert.mensagem}\n\n"
        f"{'-' * 60}\n"
        f"Severidade: {alert.severidade}\n"
        f"Gerado em: {alert.criado_em:%d/%m/%Y %H:%M}"
    )


def enviar_email(alert: Alert) -> bool:
    """Envia um alerta por SMTP. Retorna True se enviou, False se canal desabilitado/falhou."""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    senha = os.getenv("SMTP_PASS")
    destino = os.getenv("ALERT_EMAIL_TO")
    porta = int(os.getenv("SMTP_PORT", "587"))

    if not all([host, user, senha, destino]):
        logger.debug("canal email desabilitado (faltam variaveis SMTP_*)")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = destino
        msg["Subject"] = _formato_assunto(alert)
        msg.attach(MIMEText(_formato_corpo(alert), "plain", "utf-8"))

        with smtplib.SMTP(host, porta, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, senha)
            smtp.send_message(msg)
        logger.info("email enviado: alert_id=%s", alert.id)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("falha no envio de email: %s", e)
        return False


def enviar_telegram(alert: Alert) -> bool:
    """Envia alerta para um chat do Telegram via Bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not all([token, chat_id]):
        logger.debug("canal telegram desabilitado (faltam TELEGRAM_BOT_TOKEN / _CHAT_ID)")
        return False

    icone = ICONES.get(alert.severidade, "•")
    texto = f"*{icone} {alert.titulo}*\n\n{alert.mensagem}\n\n_Severidade: {alert.severidade}_"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = httpx.post(
            url,
            json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"},
            timeout=10,
        )
        r.raise_for_status()
        logger.info("telegram enviado: alert_id=%s", alert.id)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("falha no envio telegram: %s", e)
        return False


def notificar(alert: Alert, canais: list[str]) -> dict[str, bool]:
    """Despacha o alerta para os canais configurados. 'in_app' eh sempre OK."""
    resultado = {"in_app": True}  # in_app eh apenas o registro no banco
    if "email" in canais:
        resultado["email"] = enviar_email(alert)
    if "telegram" in canais:
        resultado["telegram"] = enviar_telegram(alert)
    return resultado
