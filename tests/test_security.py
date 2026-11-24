"""Password hashing: bcrypt used directly, compatible with hashes made by passlib."""

from app.core.security import hash_password, verify_password

# Hashes produced by the previous stack (passlib 1.7.4 on bcrypt 4.0.1).
# Public test fixtures: hashes of throwaway passwords defined in this file, not credentials.
LEGACY = {
    # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash
    "correct horse battery": "$2b$12$RmqzE5D5KLD1.HIfCncKPO/ujfYcr7fdCGshJXHqGbduAtu75rjxy",
    # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash
    "pässwörd-日本語-9": "$2b$12$EM42EY5t6BOyuj6DLXdlou/Hz7MbVWY/Elz.w4XHFZ52R5VXowt6q",
    # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash
    "L" * 100: "$2b$12$GEcheFEkAAuL5v2o0PcizO0xsfwls96PNJQrmBtR7wb8eN6MCeaVO",
}


def test_legacy_hashes_still_verify():
    for plain, hashed in LEGACY.items():
        assert verify_password(plain, hashed)


def test_wrong_password_is_rejected():
    assert not verify_password("wrong password", LEGACY["correct horse battery"])


def test_long_passwords_match_the_72_byte_rule():
    hashed = LEGACY["L" * 100]
    assert verify_password("L" * 100 + "extra", hashed)
    assert not verify_password("M" * 100, hashed)


def test_round_trip_uses_the_same_format_and_cost():
    hashed = hash_password("round trip")
    assert hashed.startswith("$2b$12$")
    assert verify_password("round trip", hashed)
    assert not verify_password("round trip!", hashed)


def test_malformed_hash_is_a_failed_login_not_an_error():
    assert not verify_password("anything", "not-a-hash")
