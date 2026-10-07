"""
Подтверждение владения контактными данными (email / телефон).

Бот проверяет данные по базам утечек ТОЛЬКО после того, как пользователь
доказал, что контакт принадлежит ему:
  - email  — вводит код, который бот отправил на этот адрес;
  - телефон — отправляет его кнопкой Telegram «Поделиться контактом»
              (Telegram гарантирует, что номер принадлежит отправителю).

Коды хранятся в памяти процесса, имеют срок жизни и лимит попыток.
"""
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Константы политики проверки
CODE_TTL_SECONDS = 10 * 60      # код живёт 10 минут
MAX_ATTEMPTS = 5                # не больше 5 попыток ввода
CODE_LENGTH = 6                 # длина цифрового кода
RESEND_COOLDOWN_SECONDS = 60    # не чаще одного кода в минуту


@dataclass
class PendingCode:
    code: str
    expires_at: float
    attempts_left: int
    created_at: float


class VerificationError(Exception):
    """Базовая ошибка проверки."""


class CodeExpiredError(VerificationError):
    pass


class TooManyAttemptsError(VerificationError):
    pass


class ResendTooSoonError(VerificationError):
    pass


def generate_code(length: int = CODE_LENGTH) -> str:
    """Генерирует криптостойкий цифровой код фиксированной длины."""
    # secrets.randbelow даёт равномерное распределение без modulo-bias
    upper = 10 ** length
    return str(secrets.randbelow(upper)).zfill(length)


class VerificationManager:
    """
    Хранит коды подтверждения в формате {ключ: PendingCode}.

    Ключ строится из (тип, идентификатор), например ("email", "a@b.com"),
    чтобы один пользователь мог параллельно подтверждать разные контакты.
    """

    def __init__(self, ttl: int = CODE_TTL_SECONDS,
                 max_attempts: int = MAX_ATTEMPTS,
                 resend_cooldown: int = RESEND_COOLDOWN_SECONDS):
        self._store: Dict[Tuple[str, str], PendingCode] = {}
        self._ttl = ttl
        self._max_attempts = max_attempts
        self._resend_cooldown = resend_cooldown

    @staticmethod
    def _key(kind: str, identifier: str) -> Tuple[str, str]:
        return (kind, identifier.strip().lower())

    def _now(self) -> float:
        return time.monotonic()

    def create(self, kind: str, identifier: str) -> str:
        """
        Создаёт новый код для (kind, identifier) и возвращает его.
        Бросает ResendTooSoonError, если прошлый код выдан слишком недавно.
        """
        key = self._key(kind, identifier)
        now = self._now()

        existing = self._store.get(key)
        if existing and (now - existing.created_at) < self._resend_cooldown:
            wait = int(self._resend_cooldown - (now - existing.created_at))
            raise ResendTooSoonError(wait)

        code = generate_code()
        self._store[key] = PendingCode(
            code=code,
            expires_at=now + self._ttl,
            attempts_left=self._max_attempts,
            created_at=now,
        )
        return code

    def verify(self, kind: str, identifier: str, code: str) -> bool:
        """
        Проверяет код. Возвращает True при совпадении (и удаляет запись).
        Бросает:
          - CodeExpiredError    — кода нет или он истёк;
          - TooManyAttemptsError — исчерпан лимит попыток.
        При неверном коде (попытки ещё есть) возвращает False.
        """
        key = self._key(kind, identifier)
        now = self._now()
        pending = self._store.get(key)

        if pending is None or now > pending.expires_at:
            self._store.pop(key, None)
            raise CodeExpiredError()

        if pending.attempts_left <= 0:
            self._store.pop(key, None)
            raise TooManyAttemptsError()

        if secrets.compare_digest(pending.code, code.strip()):
            self._store.pop(key, None)
            return True

        pending.attempts_left -= 1
        if pending.attempts_left <= 0:
            self._store.pop(key, None)
            raise TooManyAttemptsError()
        return False

    def has_pending(self, kind: str, identifier: str) -> bool:
        key = self._key(kind, identifier)
        pending = self._store.get(key)
        if pending is None:
            return False
        if self._now() > pending.expires_at:
            self._store.pop(key, None)
            return False
        return True

    def discard(self, kind: str, identifier: str) -> None:
        self._store.pop(self._key(kind, identifier), None)

    def purge_expired(self) -> int:
        """Удаляет истёкшие коды. Возвращает число удалённых записей."""
        now = self._now()
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]
        return len(expired)


# Глобальный экземпляр для хендлеров
verification_manager = VerificationManager()
