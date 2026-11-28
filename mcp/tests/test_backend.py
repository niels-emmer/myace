"""Backend client behaviour: query building, pagination, error mapping."""

import json

import httpx
import pytest

from backend import BackendClient, BackendError, NotFoundError

BASE = "http://backend:8000"
SITE = "https://myace.example"


def make_client(handler) -> BackendClient:
    return BackendClient(BASE, site_url=SITE, transport=httpx.MockTransport(handler))


def _pack(**overrides) -> dict[str, object]:
    pack = {
        "id": "11111111-1111-1111-1111-111111111111",
        "owner_id": "22222222-2222-2222-2222-222222222222",
        "name": "Software Engineer",
        "description": "A starting point",
        "collection_type": "base",
        "artifact_count": 3,
        "download_count": 7,
        "category": "Engineering",
        "license": "MIT",
        "avg_rating": 4.5,
        "rating_count": 2,
        "last_verified_at": None,
    }
    pack.update(overrides)
    return pack


def _item(name: str = "orchestrator", body: str = "Orchestrator body.") -> dict[str, object]:
    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "collection_id": "11111111-1111-1111-1111-111111111111",
        "name": name,
        "artifact_type": "agent",
        "priority": 90,
        "version": "1.0.0",
        "description": "Routes work",
        "tags": ["core"],
        "handoff_to": ["builder"],
        "body": body,
    }


async def test_search_forwards_filters_and_adds_site_url() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"items": [_pack()], "total": 1})

    result = await make_client(handler).search_packs(
        query="alpha", category="Engineering", pack_type="base", sort="rating", limit=5
    )

    assert seen["params"] == {
        "sort": "rating",
        "limit": "5",
        "offset": "0",
        "q": "alpha",
        "category": "Engineering",
        "type": "base",
    }
    assert result["total"] == 1
    pack = result["packs"][0]
    assert pack["name"] == "Software Engineer"
    assert pack["url"] == f"{SITE}/packs/{pack['id']}"
    # Owner ids and other internals stay out of the agent-facing payload.
    assert "owner_id" not in pack


async def test_404_becomes_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Collection not found"})

    with pytest.raises(NotFoundError):
        await make_client(handler).get_pack("11111111-1111-1111-1111-111111111111")


async def test_400_detail_is_surfaced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "Adapter 'cursor' is currently disabled"})

    with pytest.raises(BackendError, match="disabled"):
        await make_client(handler).install(
            "11111111-1111-1111-1111-111111111111", "cursor"
        )


async def test_get_item_is_case_insensitive() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_item("Orchestrator")])

    item = await make_client(handler).get_item(
        "11111111-1111-1111-1111-111111111111", "orchestrator"
    )

    assert item["name"] == "Orchestrator"


async def test_get_item_missing_lists_available_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_item("alpha"), _item("beta")])

    with pytest.raises(NotFoundError, match="alpha, beta"):
        await make_client(handler).get_item(
            "11111111-1111-1111-1111-111111111111", "gamma"
        )


async def test_install_json_repeats_with_params() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.extend(request.url.params.get_list("with"))
        return httpx.Response(
            200,
            json={
                "subject": "pack",
                "pack_id": "11111111-1111-1111-1111-111111111111",
                "files": {"CLAUDE.md": "x"},
            },
        )

    await make_client(handler).install(
        "11111111-1111-1111-1111-111111111111",
        "claude-code",
        with_packs=["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    )

    assert seen == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]


async def test_install_zip_returns_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "zip"
        return httpx.Response(200, content=b"PK\x03\x04", headers={"content-type": "application/zip"})

    archive = await make_client(handler).install(
        "11111111-1111-1111-1111-111111111111", "claude-code", fmt="zip"
    )

    assert archive == b"PK\x03\x04"


async def test_unknown_target_guidance_is_showable_not_a_decode_error() -> None:
    """The route answers 200 *markdown* for a target it does not know.

    Regression for a real failure: `install()` assumed JSON, so a typo or an
    alias like "claude" surfaced to the agent as `Expecting value: line 1
    column 1` instead of the backend's list of valid targets.
    """
    guidance = "# Choose a coding framework for X\n\n- `claude-code` — https://…"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=guidance, headers={"content-type": "text/markdown; charset=utf-8"}
        )

    with pytest.raises(BackendError, match="claude-code"):
        await make_client(handler).install(
            "11111111-1111-1111-1111-111111111111", "claude", fmt="json"
        )


async def test_guidance_is_never_returned_as_an_archive() -> None:
    """The same 200-markdown body must not be handed back as `application/zip`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text="# Choose a coding framework", headers={"content-type": "text/markdown"}
        )

    with pytest.raises(BackendError, match="Choose a coding framework"):
        await make_client(handler).install(
            "11111111-1111-1111-1111-111111111111", "claude", fmt="zip"
        )


async def test_install_url_omits_nothing_and_encodes() -> None:
    client = make_client(lambda request: httpx.Response(200, json={}))

    url = client.install_url(
        "11111111-1111-1111-1111-111111111111",
        "claude-code",
        ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
        "zip",
    )

    assert url is not None
    assert url.startswith(f"{SITE}/api/v1/collections/community/")
    assert "target=claude-code" in url
    assert "format=zip" in url
    assert "with=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" in url


async def test_no_site_url_means_no_link() -> None:
    client = BackendClient(BASE, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))

    assert client.install_url("11111111-1111-1111-1111-111111111111", "cursor") is None
    summary = client._pack_summary(_pack())
    assert "url" not in summary


async def test_valid_json_roundtrip_of_pack_summary() -> None:
    """Guard against a non-serialisable field sneaking into the summary."""
    client = make_client(lambda request: httpx.Response(200, json={}))

    assert json.loads(json.dumps(client._pack_summary(_pack())))["name"] == "Software Engineer"


async def test_client_ip_is_forwarded_to_the_backend() -> None:
    """Backend limits are per client IP; every call leaves one container IP."""
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["xff"] = request.headers.get("x-forwarded-for")
        return httpx.Response(200, json={"items": [], "total": 0})

    client = BackendClient(
        BASE,
        site_url=SITE,
        transport=httpx.MockTransport(handler),
        client_ip=lambda: "203.0.113.9",
    )
    await client.search_packs()

    assert seen["xff"] == "203.0.113.9"


async def test_no_forwarded_header_when_caller_ip_is_unknown() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["xff"] = request.headers.get("x-forwarded-for")
        return httpx.Response(200, json={"items": [], "total": 0})

    client = BackendClient(
        BASE, transport=httpx.MockTransport(handler), client_ip=lambda: None
    )
    await client.search_packs()

    assert seen["xff"] is None


async def test_public_host_is_presented_to_the_backend() -> None:
    """A production backend's TrustedHostMiddleware rejects `backend:8000`."""
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.headers.get("host")
        return httpx.Response(200, json={"items": [], "total": 0})

    client = BackendClient(BASE, site_url=SITE, transport=httpx.MockTransport(handler))
    await client.search_packs()

    assert seen["host"] == "myace.example"


async def test_no_host_header_without_a_site_url() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.headers.get("host")
        return httpx.Response(200, json={"items": [], "total": 0})

    client = BackendClient(BASE, transport=httpx.MockTransport(handler))
    await client.search_packs()

    # Whatever httpx sends by default, it must not be a fabricated public host.
    assert seen["host"] != "myace.example"


async def test_plain_text_rejection_is_surfaced() -> None:
    """Starlette's TrustedHostMiddleware answers plain text, not JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Invalid host header")

    with pytest.raises(BackendError, match="Invalid host header"):
        await make_client(handler).search_packs()


async def test_get_pack_passes_relations_and_updated_stamp_through() -> None:
    relations = {
        "layers_on": [{"id": "44444444-4444-4444-4444-444444444444", "name": "IaC", "slug": "iac-expert"}],
        "pairs_with": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_pack(relations=relations, content_updated_at="2026-11-28T10:00:00Z"),
        )

    result = await make_client(handler).get_pack("11111111-1111-1111-1111-111111111111")

    assert result["relations"] == relations
    assert result["content_updated_at"] == "2026-11-28T10:00:00Z"


async def test_get_pack_tolerates_a_backend_without_relations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_pack())

    result = await make_client(handler).get_pack("11111111-1111-1111-1111-111111111111")

    assert result["relations"] is None
    assert result["content_updated_at"] is None
