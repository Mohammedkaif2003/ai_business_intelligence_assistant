import base64
import json

import modules.supabase_service as supabase_service


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict[str, object]):
        self.status_code = status_code
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload


def _make_jwt(payload: dict[str, object]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    def encode(part: dict[str, object]) -> str:
        raw = json.dumps(part, separators=(",", ":")).encode("utf-8")
        encoded = base64.urlsafe_b64encode(raw).decode("utf-8")
        return encoded.rstrip("=")

    return ".".join([encode(header), encode(payload), "signature"])


def test_validate_access_token_rejects_expired_token_without_network(monkeypatch):
    monkeypatch.setattr(
        supabase_service,
        "get_secret",
        lambda key, default="": {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "anon-key",
        }.get(key, default),
    )

    called = {"value": False}

    def fail_if_called(*args, **kwargs):
        called["value"] = True
        raise AssertionError("requests.get should not be called for expired tokens")

    monkeypatch.setattr(supabase_service.requests, "get", fail_if_called)

    token = _make_jwt({"exp": 1, "sub": "user-1"})
    ok, user_data = supabase_service.validate_access_token(token)

    assert ok is False
    assert user_data is None
    assert called["value"] is False


def test_validate_access_token_returns_user_data_for_valid_token(monkeypatch):
    monkeypatch.setattr(
        supabase_service,
        "get_secret",
        lambda key, default="": {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "anon-key",
        }.get(key, default),
    )

    def fake_get(*args, **kwargs):
        return _DummyResponse(200, {"id": "user-1", "email": "user@example.com"})

    monkeypatch.setattr(supabase_service.requests, "get", fake_get)

    token = _make_jwt({"exp": 4_000_000_000, "sub": "user-1"})
    ok, user_data = supabase_service.validate_access_token(token)

    assert ok is True
    assert user_data == {
        "id": "user-1",
        "email": "user@example.com",
        "access_token": token,
    }
