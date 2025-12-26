import pytest

from utils.context.scorer import RelevanceScorer


@pytest.fixture
def scorer():
    return RelevanceScorer()


def test_score_path_tier_1(scorer):
    # Tier 1 files should always return 1.0
    assert scorer.score_path("pyproject.toml", "any task") == 1.0
    assert scorer.score_path("README.md", "any task") == 1.0


def test_score_path_test_boost(scorer):
    # base 0.1
    # is_test_related=True -> +0.4 = 0.5
    # task keywords: 'failing' (7), 'tests' (5)
    # path keywords: 'tests' (5), 'test' (4), 'foo' (3)
    # overlap: {'tests', 'test'} -> length 2 -> +0.3 + 0.1*2 = 0.5
    # Total: 0.5 + 0.5 = 1.0 -> capped at 0.9
    score_normal = scorer.score_path("tests/test_foo.py", "implement feature")
    score_test = scorer.score_path("tests/test_foo.py", "fix failing tests", is_test_related=True)
    assert score_test > score_normal
    assert score_test == 0.9


def test_score_path_keyword_boost(scorer):
    # base 0.1
    # task: 'fix auth bug' -> 'auth', 'bug'
    # path: 'src/auth.py' -> 'src', 'auth', 'py'
    # overlap: {'auth'} -> len 1 -> +0.3 + 0.1 = 0.4
    # Total: 0.1 + 0.4 = 0.5
    base_score = scorer.score_path("src/auth.py", "implement logging")
    boosted_score = scorer.score_path("src/auth.py", "fix auth bug")
    assert boosted_score > base_score
    assert boosted_score == pytest.approx(0.5)


def test_score_content_boost(scorer):
    # Content keywords matching task keywords should boost score by 0.1
    task = "implement authentication"
    filepath = "src/other.py"
    content_no_match = "some random content"
    content_match = "this file handles authentication logic"

    score_no_match = scorer.score(filepath, content_no_match, task)
    score_match = scorer.score(filepath, content_match, task)

    assert score_match > score_no_match
    # base 0.1 + content boost 0.1 = 0.2
    assert score_match == pytest.approx(0.2)


def test_score_caps(scorer):
    # Scores should be capped
    # Path score caps at 0.9
    # overlap 3: 0.1 + 0.3 + 0.1*3 = 0.7
    task = "one two three four five"
    path = "one_two_three_four_five.py"
    assert scorer.score_path(path, task) == pytest.approx(0.7)

    # Full score caps at 0.95
    # 0.7 + 0.1 (content match) = 0.8
    assert scorer.score(path, "one two three four five", task) == pytest.approx(0.8)
