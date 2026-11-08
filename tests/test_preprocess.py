from app.preprocess import find_cues, transform_text


def test_stems_and_drops_stopwords():
    cleaned = transform_text("I loved the lectures!!!")
    tokens = cleaned.split()
    assert "the" not in tokens
    assert "love" in tokens
    assert "lectur" in tokens
    assert "!" not in cleaned


def test_empty_symbols_leave_no_words():
    assert transform_text("???") == ""
    assert find_cues("???") == []


def test_cues_catch_link_phone_and_money():
    assert find_cues("Call 09061701461 about your prize") == ["Phone number"]
    assert find_cues("See http://bit.ly/prize now") == ["Link"]
    assert "Link" in find_cues("Claim at prize-now.com today")
    assert find_cues("You won a $1000 gift") == ["Money"]
    assert find_cues("Meet at 6, the date is 12/11/2026") == []
