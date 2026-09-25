from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.news_intelligence.service import NewsIntelligenceService
from app.news_intelligence.storage import NewsRepository
from app.news_intelligence.telegram import TelegramNewsSource


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class FakeMessage:
    def __init__(self, message_id=10, text="Bitcoin ETF approved", *, edit_date=None):
        self.id = message_id
        self.message = text
        self.date = NOW
        self.edit_date = edit_date
        self.chat = SimpleNamespace(title="Crypto Channel", username="crypto_channel")


class FakeClient:
    def __init__(self, messages=(), *, connect_error=None, connected=True, iter_error=None):
        self.messages = list(messages)
        self.connect_error = connect_error
        self.connected = connected
        self.iter_error = iter_error
        self.disconnected = False

    async def connect(self):
        if self.connect_error:
            raise self.connect_error

    def is_connected(self):
        return self.connected

    async def is_user_authorized(self):
        return True

    def iter_messages(self, _channel, *, limit):
        async def generator():
            if self.iter_error:
                raise self.iter_error
            for message in self.messages[:limit]:
                yield message
        return generator()

    async def disconnect(self):
        self.disconnected = True


def adapter_for(factory, **kwargs):
    return TelegramNewsSource(
        ["@crypto_channel"],
        api_id=123,
        api_hash="hash",
        session_path="/tmp/test.session",
        client_factory=factory,
        clock=lambda: NOW,
        **kwargs,
    )


def test_telegram_parsing_keeps_required_fields():
    item = TelegramNewsSource.parse_message(
        FakeMessage(message_id=77, text="Bitcoin ETF approved\nMore details"),
        "@crypto_channel",
        received_at=NOW,
    )
    assert item is not None
    assert item.channel == "Crypto Channel"
    assert item.message_id == 77
    assert item.published_at == NOW
    assert item.received_at == NOW
    assert item.text.startswith("Bitcoin ETF approved")
    assert item.url == "https://t.me/crypto_channel/77"
    assert item.external_id == "telegram:crypto_channel:77"


def test_duplicate_telegram_message_is_not_saved_twice(tmp_path):
    repository = NewsRepository(tmp_path / "news.db")
    service = NewsIntelligenceService(repository)
    item = TelegramNewsSource.parse_message(FakeMessage(), "@crypto_channel", received_at=NOW)
    first = service.process(item)
    second = service.process(item.model_copy())
    assert first.id == second.id
    assert len(repository.list_news()) == 1


def test_edited_telegram_message_updates_existing_row(tmp_path):
    repository = NewsRepository(tmp_path / "news.db")
    service = NewsIntelligenceService(repository)
    first = TelegramNewsSource.parse_message(
        FakeMessage(message_id=15, text="Bitcoin update"),
        "@crypto_channel",
        received_at=NOW,
    )
    edited_at = datetime(2026, 9, 25, 12, 10, tzinfo=timezone.utc)
    edited = TelegramNewsSource.parse_message(
        FakeMessage(message_id=15, text="Bitcoin update edited", edit_date=edited_at),
        "@crypto_channel",
        received_at=NOW,
    )
    saved_first = service.process(first)
    saved_edited = service.process(edited)
    assert saved_first.id == saved_edited.id
    assert saved_edited.text == "Bitcoin update edited"
    assert saved_edited.edited_at == edited_at
    assert len(repository.list_news()) == 1


def test_empty_telegram_message_is_skipped():
    assert TelegramNewsSource.parse_message(
        FakeMessage(text="   "), "@crypto_channel", received_at=NOW
    ) is None


def test_telegram_retries_after_failure():
    clients = [
        FakeClient(connect_error=ConnectionError("temporary")),
        FakeClient([FakeMessage(message_id=20)]),
    ]
    source = adapter_for(lambda *_args: clients.pop(0), max_retries=1)
    items = source.fetch()
    assert [item.message_id for item in items] == [20]


def test_disconnected_telegram_client_returns_empty_without_crash():
    source = adapter_for(lambda *_args: FakeClient(connected=False), max_retries=1)
    assert source.fetch() == []


def test_missing_credentials_disables_telegram(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION_PATH", raising=False)
    called = False

    def factory(*_args):
        nonlocal called
        called = True
        raise AssertionError("client must not be created")

    source = TelegramNewsSource(["@crypto_channel"], client_factory=factory)
    assert source.fetch() == []
    assert called is False
