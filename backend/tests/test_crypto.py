from cryptography.fernet import Fernet, InvalidToken
import pytest

from app.crypto import imsi_decrypt, imsi_encrypt, imsi_hash

FAKE_IMSI = "123456789012345"
OTHER_IMSI = "999999999999999"


def test_encrypt_decrypt_round_trip():
    key = Fernet.generate_key().decode()
    token = imsi_encrypt(FAKE_IMSI, key=key)
    assert imsi_decrypt(token, key=key) == FAKE_IMSI


def test_hash_is_stable():
    pepper = "test-pepper"
    assert imsi_hash(FAKE_IMSI, pepper=pepper) == imsi_hash(FAKE_IMSI, pepper=pepper)


def test_hash_is_unique_per_imsi():
    pepper = "test-pepper"
    assert imsi_hash(FAKE_IMSI, pepper=pepper) != imsi_hash(OTHER_IMSI, pepper=pepper)


def test_decrypt_with_wrong_key_fails():
    key = Fernet.generate_key().decode()
    wrong_key = Fernet.generate_key().decode()
    token = imsi_encrypt(FAKE_IMSI, key=key)
    with pytest.raises(InvalidToken):
        imsi_decrypt(token, key=wrong_key)
