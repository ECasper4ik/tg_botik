"""
Отправка писем с кодом подтверждения по SMTP.

Настройки берутся из config (см. .env.example):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS

Если SMTP не настроен, send_code бросает MailerNotConfiguredError —
хендлер покажет пользователю понятное сообщение вместо падения.
"""
import asyncio
import smtplib
import ssl
from email.message import EmailMessage

try:
    from config import config
except Exception:  # pragma: no cover - config создаётся пользователем
    config = None


class MailerError(Exception):
    pass


class MailerNotConfiguredError(MailerError):
    pass


def _cfg(name: str, default=None):
    return getattr(config, name, default) if config is not None else default


def is_configured() -> bool:
    return bool(_cfg("SMTP_HOST") and _cfg("SMTP_FROM"))


def _send_sync(to_email: str, code: str) -> None:
    host = _cfg("SMTP_HOST")
    port = int(_cfg("SMTP_PORT", 587))
    user = _cfg("SMTP_USER")
    password = _cfg("SMTP_PASSWORD")
    sender = _cfg("SMTP_FROM")
    use_tls = bool(_cfg("SMTP_USE_TLS", True))

    msg = EmailMessage()
    msg["Subject"] = "Код подтверждения для проверки данных"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        f"Ваш код подтверждения: {code}\n\n"
        "Введите его в боте, чтобы подтвердить, что этот адрес принадлежит вам.\n"
        "Код действует 10 минут.\n\n"
        "Если вы не запрашивали проверку — просто проигнорируйте это письмо."
    )

    context = ssl.create_default_context()
    if use_tls:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls(context=context)
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)


async def send_code(to_email: str, code: str) -> None:
    """Асинхронно отправляет код на email. Бросает MailerError при сбое."""
    if not is_configured():
        raise MailerNotConfiguredError(
            "SMTP не настроен: заполните SMTP_HOST и SMTP_FROM в config/.env"
        )
    try:
        await asyncio.to_thread(_send_sync, to_email, code)
    except MailerError:
        raise
    except Exception as e:
        raise MailerError(f"Не удалось отправить письмо: {e}") from e
