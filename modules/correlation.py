from typing import List, Dict, Set, Any, Optional
from datetime import datetime
import re
import difflib


# --- Оценка критичности утёкших данных (по категориям HIBP DataClasses) ---

# Чем выше уровень, тем опаснее утечка такого типа данных.
SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]

# Ключевые слова категорий -> уровень критичности.
_DATA_CLASS_SEVERITY = {
    "critical": [
        "password", "security question", "bank account", "credit card",
        "credit status", "payment", "cvv", "pin", "crypto", "social security",
    ],
    "high": [
        "phone", "physical address", "date of birth", "government issued id",
        "passport", "driver", "geographic location", "private message",
        "sexual", "health", "biometric", "tax", "mother's maiden",
    ],
    "medium": [
        "email address", "username", "name", "gender", "ip address",
        "employer", "job title", "education", "nationalit",
    ],
    "low": [
        "website activity", "device", "spoken language", "time zone",
        "avatar", "social media", "profile photo", "bio", "age group",
    ],
}


def classify_data_class(name: str) -> str:
    """Возвращает уровень критичности для одной категории данных HIBP."""
    low = (name or "").lower()
    for severity in ("critical", "high", "medium", "low"):
        if any(kw in low for kw in _DATA_CLASS_SEVERITY[severity]):
            return severity
    return "low"  # неизвестную категорию считаем низкой, но учитываем


def _max_severity(levels: List[str]) -> str:
    best = "none"
    for lvl in levels:
        if SEVERITY_ORDER.index(lvl) > SEVERITY_ORDER.index(best):
            best = lvl
    return best


# --- Нечёткое сопоставление строк/профилей (всё офлайн) ---

def normalize_handle(value: str) -> str:
    """Приводит ник к канону: нижний регистр, только буквы/цифры."""
    return re.sub(r"[^a-z0-9а-яё]", "", (value or "").lower())


def string_similarity(a: str, b: str) -> float:
    """Похожесть двух строк в диапазоне 0..1 (по нормализованным ником)."""
    na, nb = normalize_handle(a), normalize_handle(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def find_similar_handles(target: str, candidates: List[str],
                         threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Находит в списке ники, похожие на target.
    Возвращает список {handle, score}, отсортированный по убыванию похожести.
    """
    out = []
    for cand in candidates:
        score = string_similarity(target, cand)
        if score >= threshold:
            out.append({"handle": cand, "score": round(score, 3)})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def _tokens(value: str) -> Set[str]:
    return {t for t in re.split(r"[\s,]+", (value or "").lower().strip()) if t}


def match_full_name(a: str, b: str) -> float:
    """Совпадение ФИО по множеству токенов (порядок слов не важен)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    return len(inter) / max(len(ta), len(tb))


def match_city(a: str, b: str) -> float:
    return string_similarity(a, b)


def match_birth_year(a: Optional[int], b: Optional[int]) -> float:
    """1.0 при точном совпадении года, 0.6 при расхождении в 1 год, иначе 0."""
    if not a or not b:
        return 0.0
    diff = abs(int(a) - int(b))
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.6
    return 0.0


def match_interests(a: Set[str], b: Set[str]) -> float:
    """Коэффициент Жаккара по множествам интересов."""
    sa = {str(x).lower().strip() for x in (a or set()) if str(x).strip()}
    sb = {str(x).lower().strip() for x in (b or set()) if str(x).strip()}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

class CorrelationEngine:
    """
    Анализирует связи между пользователями и находит корреляции
    """
    
    def __init__(self):
        self.common_chats_cache = {}
    
    def extract_usernames_from_text(self, text: str) -> List[str]:
        """Извлекает возможные usernames из текста"""
        pattern = r'@([a-zA-Z0-9_]{4,32})'
        return re.findall(pattern, text)
    
    def extract_phones_from_text(self, text: str) -> List[str]:
        """Извлекает номера телефонов из текста"""
        pattern = r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        return re.findall(pattern, text)
    
    def extract_emails_from_text(self, text: str) -> List[str]:
        """Извлекает email из текста"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)
    
    def find_connections(self, chat_members: List[int], target_id: int) -> List[int]:
        """
        Находит пользователей, которые состоят в нескольких общих чатах с целью
        """
        # Это упрощённая версия — в реальности требует анализа графов
        return []
    
    def calculate_trust_score(self, entity_data: Dict) -> float:
        """
        Вычисляет "степень доверия" к найденной информации
        """
        score = 0.0
        factors = {
            'has_verified_phone': 0.2,
            'has_verified_email': 0.15,
            'has_common_chats': 0.25,
            'has_bio': 0.1,
            'has_profile_photo': 0.1,
            'premium_account': 0.1,
            'account_age_days': 0.1
        }
        
        # Проверка каждого фактора
        if entity_data.get('phone_confirmed'):
            score += factors['has_verified_phone']
        if entity_data.get('email_confirmed'):
            score += factors['has_verified_email']
        if entity_data.get('common_chats_count', 0) > 0:
            score += factors['has_common_chats']
        if entity_data.get('bio'):
            score += factors['has_bio']
        if entity_data.get('photo'):
            score += factors['has_profile_photo']
        if entity_data.get('premium'):
            score += factors['premium_account']
        
        # Возраст аккаунта (если есть дата регистрации)
        if entity_data.get('registration_date'):
            days = (datetime.now() - entity_data['registration_date']).days
            if days > 365:
                score += factors['account_age_days']
        
        return min(score, 1.0)
    
    # Веса полей при расчёте уверенности, что запись принадлежит субъекту
    _MATCH_WEIGHTS = {
        "full_name": 0.35,
        "username": 0.25,
        "city": 0.15,
        "birth_year": 0.15,
        "interests": 0.10,
    }

    def match_profile(self, subject: Dict[str, Any],
                      candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сопоставляет утёкшую/найденную запись (candidate) с данными самого
        субъекта (subject). Считается только по полям, присутствующим у обоих.

        Возвращает {fields: {поле: score}, confidence: 0..1, matched_fields}.
        Предназначено для самопроверки: «эта утёкшая запись похожа на меня».
        """
        field_scores: Dict[str, float] = {}

        if subject.get("full_name") and candidate.get("full_name"):
            field_scores["full_name"] = match_full_name(
                subject["full_name"], candidate["full_name"])

        if subject.get("username") and candidate.get("username"):
            field_scores["username"] = string_similarity(
                subject["username"], candidate["username"])

        if subject.get("city") and candidate.get("city"):
            field_scores["city"] = match_city(subject["city"], candidate["city"])

        if subject.get("birth_year") and candidate.get("birth_year"):
            field_scores["birth_year"] = match_birth_year(
                subject["birth_year"], candidate["birth_year"])

        if subject.get("interests") and candidate.get("interests"):
            field_scores["interests"] = match_interests(
                set(subject["interests"]), set(candidate["interests"]))

        # Взвешенная уверенность по доступным полям
        total_weight = sum(self._MATCH_WEIGHTS[f] for f in field_scores)
        if total_weight > 0:
            confidence = sum(
                score * self._MATCH_WEIGHTS[f]
                for f, score in field_scores.items()
            ) / total_weight
        else:
            confidence = 0.0

        matched = [f for f, s in field_scores.items() if s >= 0.6]
        return {
            "fields": {f: round(s, 3) for f, s in field_scores.items()},
            "confidence": round(confidence, 3),
            "matched_fields": matched,
        }

    def assess_breach_criticality(self, breaches: List[Dict]) -> Dict[str, Any]:
        """
        Оценивает, насколько критична утечка данных субъекта, на основе
        категорий данных (DataClasses) из ответа Have I Been Pwned.

        Возвращает {level, breach_count, by_severity, leaked_data_classes,
        recommendations}.
        """
        if not breaches:
            return {
                "level": "none",
                "breach_count": 0,
                "by_severity": {},
                "leaked_data_classes": [],
                "recommendations": [],
            }

        by_severity: Dict[str, Set[str]] = {}
        all_classes: Set[str] = set()
        for breach in breaches:
            for dc in breach.get("DataClasses", []) or []:
                all_classes.add(dc)
                sev = classify_data_class(dc)
                by_severity.setdefault(sev, set()).add(dc)

        level = _max_severity(list(by_severity.keys())) if by_severity else "medium"

        recommendations = []
        if "critical" in by_severity:
            recommendations.append(
                "Срочно смените пароли и проверьте финансовые/платёжные данные.")
        if "high" in by_severity:
            recommendations.append(
                "Утекли чувствительные данные (телефон/адрес/дата рождения) — "
                "будьте внимательны к фишингу и попыткам восстановления доступа.")
        recommendations.append("Включите двухфакторную аутентификацию везде, где можно.")
        recommendations.append("Не используйте один и тот же пароль на разных сервисах.")

        return {
            "level": level,
            "breach_count": len(breaches),
            "by_severity": {k: sorted(v) for k, v in by_severity.items()},
            "leaked_data_classes": sorted(all_classes),
            "recommendations": recommendations,
        }

    def merge_entities(self, entities: list):
        merged = {
            'user_ids': set(),
            'usernames': set(),
            'phones': set(),
            'emails': set(),
            'names': set(),
            'platforms': {},
            'common_chats': set(),
            'confidence_score': 0.0
        }

        for entity in entities:
            # Объединение данных
            if entity.get('user_id'):
                merged['user_ids'].add(entity['user_id'])
            if entity.get('username'):
                merged['usernames'].add(entity['username'])
            if entity.get('phone'):
                merged['phones'].add(entity['phone'])
            if entity.get('email'):
                merged['emails'].add(entity['email'])
            if entity.get('name'):
                merged['names'].add(entity['name'])
            
            # Платформы
            if entity.get('platforms'):
                merged['platforms'].update(entity['platforms'])
            
            # Общие чаты
            if entity.get('common_chats'):
                merged['common_chats'].update(entity['common_chats'])
        
        # Конвертация множеств в списки для сериализации
        merged['user_ids'] = list(merged['user_ids'])
        merged['usernames'] = list(merged['usernames'])
        merged['phones'] = list(merged['phones'])
        merged['emails'] = list(merged['emails'])
        merged['names'] = list(merged['names'])
        merged['common_chats'] = list(merged['common_chats'])
        
        return merged

correlation_engine = CorrelationEngine()
