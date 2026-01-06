from utils.token.counter import TokenCounter


def test_token_counter_basic():
    counter = TokenCounter()
    text = "Hello world"
    # Basic sanity check (approximates)
    count = counter.count_tokens(text)
    assert count > 0


def test_token_counter_caching():
    counter = TokenCounter()
    text = "Repeat this text multiple times"

    # First call
    c1 = counter.count_tokens(text)

    # Second call (should hit cache - verify internally or just speed)
    c2 = counter.count_tokens(text)

    assert c1 == c2
