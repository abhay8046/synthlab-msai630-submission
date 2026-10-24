"""OpenRouter routing tests; no account secrets, credits, or external requests."""
import pandas as pd
import pytest
from synthlab.generator import get_client, resolve_model, generate_batch, OPENROUTER_URL

def test_model_resolution_prioritizes_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-test-key-not-a-secret")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL", "some-other-model")
    assert resolve_model() == "openai/gpt-4o-mini"

def test_router_client_uses_openrouter_endpoint_without_network(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-test-key-not-a-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "other-fake-test-key")
    client = get_client()
    assert str(client.base_url).rstrip("/") == OPENROUTER_URL
    assert client.api_key == "fake-test-key-not-a-secret"

def test_router_model_cannot_be_swapped_from_web_ui(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-test-key-not-a-secret")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    seeds = pd.DataFrame([
        {"category":"card_not_working","text":"My card is declined."},
        {"category":"card_not_working","text":"Why can't I use my card?"},
    ])
    with pytest.raises(ValueError, match="model is locked"):
        generate_batch(seeds,intent="card_not_working",tone="neutral",
            length_band="short",count=1,model="some-expensive-model")

def test_without_router_legacy_openai_model_is_available(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL","gpt-4o-mini")
    assert resolve_model()=="gpt-4o-mini"
