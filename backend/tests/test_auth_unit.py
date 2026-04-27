from app.core.auth.password import hash_password, verify_password


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("testpassword123")
    assert hashed != "testpassword123"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("testpassword123")
    assert verify_password("testpassword123", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("testpassword123")
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_unique_salts():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2
