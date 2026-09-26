from app.news_intelligence.source_config import load_news_sources_config


def test_default_news_sources_yaml_is_safe_and_empty(tmp_path):
    path = tmp_path / "news_sources.yaml"
    path.write_text(
        "telegram:\n  enabled: false\n  channels: []\nrss:\n  enabled: true\n  sources: []\n",
        encoding="utf-8",
    )
    config = load_news_sources_config(path)
    assert config.telegram.enabled is False
    assert config.telegram.channels == []
    assert config.rss.enabled is True


def test_telegram_factory_respects_disabled_source_config(tmp_path):
    from app.news_intelligence.telegram import TelegramNewsSource

    path = tmp_path / "news_sources.yaml"
    path.write_text(
        "telegram:\n  enabled: false\n  channels: ['@example']\nrss:\n  enabled: true\n  sources: []\n",
        encoding="utf-8",
    )
    source = TelegramNewsSource.from_config(
        str(path),
        api_id=1,
        api_hash="hash",
        session_path="/tmp/test.session",
        client_factory=lambda *_args: (_ for _ in ()).throw(AssertionError("must not connect")),
    )
    assert source.available is False
    assert source.fetch() == []
