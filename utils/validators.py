import re
import phonenumbers
from email_validator import validate_email as validate_email_lib

def validate_phone(phone: str) -> bool:
    """Проверка корректности номера телефона в международном формате"""
    try:
        # Очищаем от лишних символов
        cleaned = re.sub(r'[^\d+]', '', phone)
        parsed = phonenumbers.parse(cleaned, None)
        return phonenumbers.is_valid_number(parsed)
    except:
        return False

def validate_email(email: str) -> bool:
    try:
        validate_email_lib(email)
        return True
    except:
        return False

def validate_username(username: str) -> bool:
    """Проверка корректности username Telegram"""
    # Telegram username: от 5 до 32 символов, латиница, цифры, подчеркивание
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return bool(re.match(pattern, username))

def detect_input_type(input_str: str) -> str:
    """
    Определяет тип ввода:
    - 'phone' — номер телефона
    - 'username' — юзернейм
    - 'user_id' — числовой ID
    - 'email' — email
    - 'unknown' — не удалось определить
    """
    input_str = input_str.strip()
    
    # Проверка на phone
    if validate_phone(input_str):
        return 'phone'
    
    # Проверка на email
    if validate_email(input_str):
        return 'email'
    
    # Проверка на username (начинается с @ или без)
    clean_username = input_str.lstrip('@')
    if validate_username(clean_username):
        return 'username'
    
    # Проверка на user_id (число)
    if input_str.isdigit():
        return 'user_id'
    
    return 'unknown'

def normalize_phone(phone: str) -> str:
    """Приводит номер к международному формату"""
    cleaned = re.sub(r'[^\d+]', '', phone)
    try:
        parsed = phonenumbers.parse(cleaned, None)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        return phone
