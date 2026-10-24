"""Low-cost novelty checks; no live calls or actual account keys."""
from synthlab.novelty import normalized,most_similar

def test_case_punctuation_whitespace_ignored():
    assert normalized("  WHY, is MY card!! ")=="why is my card"
    duplicate,score=most_similar(
        "My card was declined!",
        ["my  CARD was declined?"],
    )
    assert duplicate and score==1.0

def test_fresh_message_is_accepted():
    duplicate,score=most_similar(
        "Could you check why an outgoing transfer hasn't completed?",
        ["My contactless card is repeatedly declined in shops."]
    )
    assert not duplicate
    assert score<0.87

def test_close_paraphrase_is_flagged():
    a="I tried paying at the shop but my bank card was repeatedly declined."
    b="I tried paying at a shop but my bank card was repeatedly declined!"
    duplicate,score=most_similar(a,[b],threshold=.87)
    assert duplicate and score>=.87

def test_invalid_threshold_rejected():
    import pytest
    with pytest.raises(ValueError):
        most_similar("hi",[],threshold=1.3)
