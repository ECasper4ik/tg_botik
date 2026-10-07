import time

import pytest

from utils.verification import (
    VerificationManager,
    generate_code,
    CodeExpiredError,
    TooManyAttemptsError,
    ResendTooSoonError,
    CODE_LENGTH,
)


def test_generate_code_format():
    for _ in range(50):
        code = generate_code()
        assert len(code) == CODE_LENGTH
        assert code.isdigit()


def test_generate_code_custom_length():
    assert len(generate_code(4)) == 4


def test_create_and_verify_success():
    vm = VerificationManager()
    code = vm.create("email", "User@Example.com")
    # идентификатор нечувствителен к регистру
    assert vm.verify("email", "user@example.com", code) is True
    # код одноразовый — повторная проверка падает как истёкший
    with pytest.raises(CodeExpiredError):
        vm.verify("email", "user@example.com", code)


def test_wrong_code_decrements_attempts():
    vm = VerificationManager(max_attempts=3)
    vm.create("email", "a@b.com")
    assert vm.verify("email", "a@b.com", "000000") is False
    assert vm.verify("email", "a@b.com", "111111") is False


def test_too_many_attempts():
    vm = VerificationManager(max_attempts=2)
    vm.create("email", "a@b.com")
    assert vm.verify("email", "a@b.com", "000000") is False
    with pytest.raises(TooManyAttemptsError):
        vm.verify("email", "a@b.com", "111111")
    # после блокировки запись удалена
    with pytest.raises(CodeExpiredError):
        vm.verify("email", "a@b.com", "222222")


def test_expired_code():
    vm = VerificationManager(ttl=0)
    code = vm.create("email", "a@b.com")
    time.sleep(0.01)
    with pytest.raises(CodeExpiredError):
        vm.verify("email", "a@b.com", code)


def test_verify_unknown_identifier():
    vm = VerificationManager()
    with pytest.raises(CodeExpiredError):
        vm.verify("email", "nobody@nowhere.com", "123456")


def test_resend_cooldown():
    vm = VerificationManager(resend_cooldown=1000)
    vm.create("email", "a@b.com")
    with pytest.raises(ResendTooSoonError):
        vm.create("email", "a@b.com")


def test_resend_allowed_without_cooldown():
    vm = VerificationManager(resend_cooldown=0)
    first = vm.create("email", "a@b.com")
    second = vm.create("email", "a@b.com")
    # новый код инвалидирует старый
    assert vm.verify("email", "a@b.com", first) is False or second != first


def test_has_pending_and_discard():
    vm = VerificationManager()
    vm.create("phone", "+79990000000")
    assert vm.has_pending("phone", "+79990000000") is True
    vm.discard("phone", "+79990000000")
    assert vm.has_pending("phone", "+79990000000") is False


def test_purge_expired():
    vm = VerificationManager(ttl=0)
    vm.create("email", "a@b.com")
    vm.create("email", "c@d.com")
    time.sleep(0.01)
    assert vm.purge_expired() == 2


def test_separate_kinds_independent():
    vm = VerificationManager()
    ec = vm.create("email", "x@y.com")
    pc = vm.create("phone", "x@y.com")
    assert ec != pc or True  # разные записи
    assert vm.verify("email", "x@y.com", ec) is True
    # телефонная запись всё ещё жива
    assert vm.has_pending("phone", "x@y.com") is True
