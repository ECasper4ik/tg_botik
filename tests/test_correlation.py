from modules.correlation import (
    CorrelationEngine,
    classify_data_class,
    string_similarity,
    find_similar_handles,
    match_full_name,
    match_birth_year,
    match_interests,
    normalize_handle,
)

engine = CorrelationEngine()


# ---------------------------- строки / ники ----------------------------

def test_normalize_handle():
    assert normalize_handle("John.Doe_123") == "johndoe123"
    assert normalize_handle("@Alice!") == "alice"


def test_string_similarity_identical():
    assert string_similarity("john_doe", "JohnDoe") == 1.0


def test_string_similarity_partial():
    score = string_similarity("john_doe", "john_doe99")
    assert 0.7 < score < 1.0


def test_string_similarity_empty():
    assert string_similarity("", "abc") == 0.0


def test_find_similar_handles():
    res = find_similar_handles(
        "john_doe",
        ["johndoe", "john.doe.1", "totally_different", "jane_smith"],
        threshold=0.7,
    )
    handles = [r["handle"] for r in res]
    assert "johndoe" in handles
    assert "totally_different" not in handles
    # отсортировано по убыванию похожести
    scores = [r["score"] for r in res]
    assert scores == sorted(scores, reverse=True)


# ---------------------------- поля профиля ----------------------------

def test_match_full_name_order_independent():
    assert match_full_name("Иван Петров", "Петров Иван") == 1.0


def test_match_full_name_partial():
    assert match_full_name("Иван Петров Сергеевич", "Иван Петров") == pytest_approx(2 / 3)


def test_match_birth_year():
    assert match_birth_year(1990, 1990) == 1.0
    assert match_birth_year(1990, 1991) == 0.6
    assert match_birth_year(1990, 1995) == 0.0
    assert match_birth_year(None, 1990) == 0.0


def test_match_interests_jaccard():
    a = {"music", "football", "coding"}
    b = {"music", "coding", "travel"}
    # пересечение 2, объединение 4
    assert match_interests(a, b) == 0.5


# ---------------------------- match_profile ----------------------------

def test_match_profile_strong():
    subject = {
        "full_name": "Иван Петров",
        "username": "ivan_petrov",
        "city": "Москва",
        "birth_year": 1990,
        "interests": {"music", "coding"},
    }
    candidate = {
        "full_name": "Петров Иван",
        "username": "ivanpetrov",
        "city": "Москва",
        "birth_year": 1990,
        "interests": {"music", "coding", "art"},
    }
    res = engine.match_profile(subject, candidate)
    assert res["confidence"] > 0.8
    assert "full_name" in res["matched_fields"]


def test_match_profile_only_common_fields():
    subject = {"full_name": "Иван Петров"}
    candidate = {"full_name": "Иван Петров", "city": "Казань"}
    res = engine.match_profile(subject, candidate)
    # учитывается только общее поле full_name
    assert res["fields"] == {"full_name": 1.0}
    assert res["confidence"] == 1.0


def test_match_profile_no_common_fields():
    res = engine.match_profile({"city": "Москва"}, {"full_name": "Иван"})
    assert res["confidence"] == 0.0
    assert res["matched_fields"] == []


# ---------------------------- критичность ----------------------------

def test_classify_data_class():
    assert classify_data_class("Passwords") == "critical"
    assert classify_data_class("Phone numbers") == "high"
    assert classify_data_class("Email addresses") == "medium"
    assert classify_data_class("Time zones") == "low"


def test_assess_criticality_empty():
    res = engine.assess_breach_criticality([])
    assert res["level"] == "none"
    assert res["breach_count"] == 0


def test_assess_criticality_picks_highest():
    breaches = [
        {"Name": "A", "DataClasses": ["Email addresses", "Usernames"]},
        {"Name": "B", "DataClasses": ["Passwords", "Phone numbers"]},
    ]
    res = engine.assess_breach_criticality(breaches)
    assert res["level"] == "critical"
    assert res["breach_count"] == 2
    assert "Passwords" in res["leaked_data_classes"]
    assert res["recommendations"]


def test_assess_criticality_medium_only():
    breaches = [{"Name": "A", "DataClasses": ["Email addresses"]}]
    res = engine.assess_breach_criticality(breaches)
    assert res["level"] == "medium"


# небольшой помощник сравнения дробей без зависимости от pytest.approx импорта
def pytest_approx(value, tol=1e-6):
    class _Approx(float):
        def __eq__(self, other):
            return abs(float(self) - other) < tol
    return _Approx(value)
