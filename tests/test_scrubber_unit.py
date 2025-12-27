import pytest

from utils.security.scrubber import SecretScrubber


@pytest.fixture
def scrubber():
    return SecretScrubber()


def test_scrub_openai_key(scrubber):
    text = "Here is my key: sk-5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t"
    assert "sk-" not in scrubber.scrub(text)
    assert "[REDACTED_OPENAI_API_KEY]" in scrubber.scrub(text)


def test_scrub_google_key(scrubber):
    text = "AIzaSyB-xY_XyZ1234567890123456789012345"
    assert "[REDACTED_GOOGLE_API_KEY]" in scrubber.scrub(text)


def test_scrub_email(scrubber):
    text = "Contact me at test.user@example.co.uk for details"
    assert "test.user@example.co.uk" not in scrubber.scrub(text)
    assert "[REDACTED_EMAIL]" in scrubber.scrub(text)


def test_scrub_ipv4(scrubber):
    text = "Server is at 192.168.1.100"
    assert "192.168.1.100" not in scrubber.scrub(text)
    assert "[REDACTED_IPV4]" in scrubber.scrub(text)


def test_scrub_db_connection(scrubber):
    text = "postgres://admin:password123@localhost:5432/mydb"
    assert "admin:password123" not in scrubber.scrub(text)
    assert "[REDACTED_DB_CONNECTION]" in scrubber.scrub(text)


def test_scrub_generic_api_key(scrubber):
    # Note: pattern requires 16 chars and specific prefix
    text2 = "api_key = 'some-very-secret-token-12345'"
    assert "some-very-secret-token-12345" not in scrubber.scrub(text2)
    assert "[REDACTED_GENERIC_API_KEY]" in scrubber.scrub(text2)
    assert "api_key = '" in scrubber.scrub(text2)


def test_scrub_ssh_private_key(scrubber):
    text = """
-----BEGIN RSA PRIVATE KEY BLOCK-----
MIIEpAIBAAKCAQEA75h...
...
-----END RSA PRIVATE KEY BLOCK-----
"""
    assert "[REDACTED_SSH_PRIVATE_KEY]" in scrubber.scrub(text)


def test_scrub_multiple(scrubber):
    text = "Key sk-5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t5t and email test@test.com"
    scrubbed = scrubber.scrub(text)
    assert "[REDACTED_OPENAI_API_KEY]" in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed


def test_scrub_no_match(scrubber):
    text = "This is just a normal sentence with no secrets."
    assert scrubber.scrub(text) == text


def test_scrub_empty(scrubber):
    assert scrubber.scrub("") == ""
    assert scrubber.scrub(None) == ""


def test_scrub_aws_access_key(scrubber):
    text = "AKIAIOSFODNN7EXAMPLE"
    assert "[REDACTED_AWS_ACCESS_KEY]" in scrubber.scrub(text)


def test_scrub_aws_secret_key(scrubber):
    # Pattern requires boundaries now
    text = "secret_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" 
    assert "[REDACTED_AWS_SECRET_KEY]" in scrubber.scrub(text)


def test_scrub_slack_token(scrubber):
    text = "xoxb-1234567890-1234567890-1234567890"
    assert "[REDACTED_SLACK_TOKEN]" in scrubber.scrub(text)


def test_scrub_complex_pem(scrubber):
    text = """
-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFDjBABgkqhkiG9w0BBQ0wMzAbBgkqhkiG9w0BBQwwDgQIzn
...
-----END ENCRYPTED PRIVATE KEY-----
"""
    assert "[REDACTED_SSH_PRIVATE_KEY]" in scrubber.scrub(text)
