from types import SimpleNamespace

from plugins.web.exa import provider as exa_provider


def test_exa_search_preserves_published_date(monkeypatch):
    client = SimpleNamespace(
        search=lambda *_args, **_kwargs: SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://example.com/story",
                    title="Current story",
                    highlights=["Opened evidence"],
                    published_date="2026-07-28T12:30:00.000Z",
                )
            ]
        )
    )
    monkeypatch.setattr(exa_provider, "_get_exa_client", lambda: client)

    result = exa_provider.ExaWebSearchProvider().search("current story")

    assert result["success"] is True
    assert (
        result["data"]["web"][0]["published_at"]
        == "2026-07-28T12:30:00.000Z"
    )


def test_exa_extract_preserves_published_date_in_metadata(monkeypatch):
    client = SimpleNamespace(
        get_contents=lambda *_args, **_kwargs: SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://example.com/story",
                    title="Current story",
                    text="Opened article body.",
                    published_date="2026-07-28T12:30:00.000Z",
                )
            ]
        )
    )
    monkeypatch.setattr(exa_provider, "_get_exa_client", lambda: client)

    result = exa_provider.ExaWebSearchProvider().extract(
        ["https://example.com/story"]
    )

    assert (
        result[0]["metadata"]["published_at"]
        == "2026-07-28T12:30:00.000Z"
    )
