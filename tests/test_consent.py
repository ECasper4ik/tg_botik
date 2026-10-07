import pytest

from utils.consent import (
    ConsentManager,
    UserRegistry,
    ConsentStatus,
    RequestNotFoundError,
    RequestExpiredError,
    NotTargetError,
    AlreadyAnsweredError,
    RequestTooSoonError,
)


# ---------------------------- UserRegistry ----------------------------

def test_registry_resolve_by_username():
    reg = UserRegistry()
    reg.register(111, "Alice")
    assert reg.resolve("@alice") == 111
    assert reg.resolve("alice") == 111
    assert reg.resolve("ALICE") == 111


def test_registry_resolve_by_id_only_if_known():
    reg = UserRegistry()
    reg.register(111, "alice")
    assert reg.resolve("111") == 111
    assert reg.resolve("999") is None


def test_registry_unknown_returns_none():
    reg = UserRegistry()
    assert reg.resolve("@nobody") is None


def test_registry_username_change_cleans_old():
    reg = UserRegistry()
    reg.register(111, "old")
    reg.register(111, "new")
    assert reg.resolve("@new") == 111
    assert reg.resolve("@old") is None


def test_registry_username_of():
    reg = UserRegistry()
    reg.register(111, "alice")
    assert reg.username_of(111) == "alice"
    assert reg.username_of(222) is None


# ---------------------------- ConsentManager ----------------------------

def test_create_and_grant_by_target():
    cm = ConsentManager()
    req = cm.create_request(operator_id=1, target_id=2, target_username="bob")
    assert req.status is ConsentStatus.PENDING
    granted = cm.grant(req.token, by_user_id=2)
    assert granted.status is ConsentStatus.GRANTED


def test_only_target_can_grant():
    cm = ConsentManager()
    req = cm.create_request(1, 2, "bob")
    # оператор (или кто-либо кроме субъекта) не может подтвердить за него
    with pytest.raises(NotTargetError):
        cm.grant(req.token, by_user_id=1)


def test_deny_by_target():
    cm = ConsentManager()
    req = cm.create_request(1, 2, "bob")
    denied = cm.deny(req.token, by_user_id=2)
    assert denied.status is ConsentStatus.DENIED


def test_cannot_answer_twice():
    cm = ConsentManager()
    req = cm.create_request(1, 2, "bob")
    cm.grant(req.token, 2)
    with pytest.raises(AlreadyAnsweredError):
        cm.deny(req.token, 2)


def test_unknown_token():
    cm = ConsentManager()
    with pytest.raises(RequestNotFoundError):
        cm.grant("nope", 2)


def test_expired_request():
    cm = ConsentManager(ttl=0)
    req = cm.create_request(1, 2, "bob")
    import time
    time.sleep(0.01)
    with pytest.raises(RequestExpiredError):
        cm.grant(req.token, 2)


def test_request_cooldown():
    cm = ConsentManager(cooldown=1000)
    cm.create_request(1, 2, "bob")
    with pytest.raises(RequestTooSoonError):
        cm.create_request(1, 2, "bob")


def test_cooldown_is_per_operator_target_pair():
    cm = ConsentManager(cooldown=1000)
    cm.create_request(1, 2, "bob")
    # другой субъект — отдельный лимит
    other = cm.create_request(1, 3, "carol")
    assert other.status is ConsentStatus.PENDING


def test_consume_removes_request():
    cm = ConsentManager()
    req = cm.create_request(1, 2, "bob")
    cm.consume(req.token)
    with pytest.raises(RequestNotFoundError):
        cm.grant(req.token, 2)


def test_purge_expired():
    cm = ConsentManager(ttl=0)
    cm.create_request(1, 2, "bob")
    cm.create_request(1, 3, "carol")
    import time
    time.sleep(0.01)
    assert cm.purge_expired() == 2
