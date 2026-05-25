import pytest

pytest.importorskip("discord")

import discord

from config import Config
from messages.discord_embeds import DiscordEmbeds


class _DummyWebhook:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)


def _build_embeds(monkeypatch):
    # Prevent tests from constructing a real webhook from local config.
    monkeypatch.setattr(DiscordEmbeds, "_get_webhook", lambda self, hook_url: None)
    return DiscordEmbeds()


def test_send_embed_ignores_none_embed(monkeypatch):
    embeds = _build_embeds(monkeypatch)
    webhook = _DummyWebhook()

    embeds._send_embed(None, webhook)

    assert len(webhook.calls) == 0


def test_send_embed_sends_valid_embed(monkeypatch):
    embeds = _build_embeds(monkeypatch)
    webhook = _DummyWebhook()
    embed = discord.Embed(title="Update", description="Test", color=discord.Color.blue())

    embeds._send_embed(embed, webhook)

    assert len(webhook.calls) == 1
    call = webhook.calls[0]
    assert call["embed"] is embed
    assert call["username"] == Config().general["name"]
    assert embed.footer.text.startswith("Botty v.")
    assert embed.timestamp is not None
