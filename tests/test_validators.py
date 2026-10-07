from utils.validators import (
    validate_email,
    validate_phone,
    validate_username,
    detect_input_type,
    normalize_phone,
)


def test_validate_email():
    assert validate_email("user@example.com") is True
    assert validate_email("not-an-email") is False
    assert validate_email("") is False


def test_validate_phone():
    assert validate_phone("+14155552671") is True   # валидный US-номер
    assert validate_phone("12345") is False
    assert validate_phone("abc") is False


def test_validate_username():
    assert validate_username("durov") is True
    assert validate_username("ab") is False          # слишком короткий
    assert validate_username("1user") is False        # начинается с цифры
    assert validate_username("good_name_1") is True


def test_detect_input_type_email():
    assert detect_input_type("user@example.com") == "email"


def test_detect_input_type_phone():
    assert detect_input_type("+14155552671") == "phone"


def test_detect_input_type_username():
    assert detect_input_type("@durov") == "username"
    assert detect_input_type("durov") == "username"


def test_detect_input_type_user_id():
    assert detect_input_type("123456789") == "user_id"


def test_detect_input_type_unknown():
    assert detect_input_type("!!!") == "unknown"


def test_normalize_phone():
    assert normalize_phone("+1 (415) 555-2671") == "+14155552671"
    # при неразборчивом вводе возвращается исходная строка
    assert normalize_phone("garbage") == "garbage"
