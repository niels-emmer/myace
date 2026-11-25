"""HTTP client for MyACE's anonymous read routes.

Deliberately dumb: no database, no credentials, no compiler, no writes. Every
byte this container serves is already anonymously readable from the backend,
so this module only turns HTTP into dicts/bytes and maps failures onto
messages an agent can act on.

Keeping the visibility rules in the backend (one predicate:
`_get_public_collection_or_404`) is the point — this container has no query of
its own to get wrong.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

# Presentation fields only. `PublicCollectionRead` already withholds owner
# internals, and there is nothing here worth widening that.
_PACK_FIELDS = (
    "id",
    "name",
    "description",
    "collection_type",
    "artifact_count",
    "download_count",
    "category",
    "license",
    "avg_rating",
    "rating_count",
    "last_verified_at",
)

# Item bodies are fetched one at a time on purpose: a pack is often 17+ items
# and dumping every body into one tool result would flood the agent's context.
_ITEM_FIELDS = (
    "name",
    "artifact_type",
    "priority",
    "version",
    "description",
    "tags",
    "handoff_to",
)


class NotFoundError(Exception):
    """The pack does not exist, or is not published/approved."""


# What httpx accepts for `params=`. Named so `_get` does not take a bare
# `object` (which would silently accept anything and fail at request time).
QueryParams = dict[str, object] | list[tuple[str, object]] | None


class BackendError(Exception):
    """The backend rejected the request; the message is showable to an agent."""


def _detail(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return fallback


class BackendClient:
    """Thin async wrapper over `/api/v1/collections/community*` and friends."""

    def __init__(
        self,
        base_url: str,
        site_url: str = "",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )
        # Public site origin, used only to build links a human can open. The
        # backend URL is an internal Docker address, never a usable link.
        self.site_url = site_url.rstrip("/")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(
        self, path: str, params: QueryParams = None
    ) -> httpx.Response:
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            raise BackendError(
                f"Could not reach the MyACE backend ({type(exc).__name__})."
            ) from exc

        if response.status_code == 404:
            raise NotFoundError(
                "No such pack: it is not published, not approved, or does not exist."
            )
        if response.status_code == 413:
            raise BackendError(
                "This pack is too large for a document response; fetch the zip resource instead."
            )
        if response.status_code == 422:
            raise BackendError("That is not a valid pack id.")
        if response.status_code == 429:
            raise BackendError("Rate limited by MyACE; retry in a minute.")
        if response.status_code >= 400:
            raise BackendError(
                _detail(response, f"MyACE backend returned HTTP {response.status_code}.")
            )
        return response

    # ── reads ────────────────────────────────────────────────────────────

    async def search_packs(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        pack_type: str | None = None,
        sort: str = "downloads",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, object]:
        params: dict[str, object] = {"sort": sort, "limit": limit, "offset": offset}
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if pack_type:
            params["type"] = pack_type

        body = (await self._get("/api/v1/collections/community", params)).json()
        return {
            "total": body.get("total", 0),
            "offset": offset,
            "limit": limit,
            "packs": [self._pack_summary(raw) for raw in body.get("items", [])],
        }

    async def get_pack(self, pack_id: str) -> dict[str, object]:
        raw = (await self._get(f"/api/v1/collections/community/{pack_id}")).json()
        return self._pack_summary(raw)

    async def list_items(
        self, pack_id: str, artifact_type: str | None = None
    ) -> list[dict[str, object]]:
        raw = await self._raw_items(pack_id, artifact_type)
        return [{key: item.get(key) for key in _ITEM_FIELDS} for item in raw]

    async def get_item(self, pack_id: str, item_name: str) -> dict[str, object]:
        raw = await self._raw_items(pack_id, None)
        for item in raw:
            if item.get("name") == item_name:
                return item
        # Fall back to a case-insensitive match so an agent that lower-cased a
        # name still gets the item instead of a dead end.
        lowered = item_name.lower()
        for item in raw:
            if str(item.get("name", "")).lower() == lowered:
                return item
        available = sorted(str(item.get("name")) for item in raw)
        raise NotFoundError(
            f"No item named {item_name!r} in this pack. Available items: {', '.join(available)}"
        )

    async def list_frameworks(self) -> list[str]:
        return (await self._get("/api/v1/frameworks")).json()

    async def install(
        self,
        pack_id: str,
        target: str,
        with_packs: list[str] | None = None,
        fmt: str = "json",
    ) -> dict[str, object] | bytes:
        params: list[tuple[str, object]] = [("target", target), ("format", fmt)]
        params += [("with", other) for other in (with_packs or [])]
        response = await self._get(
            f"/api/v1/collections/community/{pack_id}/install.md", params
        )

        # `install.md` deliberately answers **200 text/markdown** for a target it
        # does not recognise — that body *is* the useful answer (the valid target
        # list), per its four-case contract. Parsing it as JSON raises
        # JSONDecodeError and handing it back as a zip mislabels prose as an
        # archive, so surface it as a showable failure instead. Reachable from
        # any stale link, typo, or `supported_targets()` alias such as "claude".
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/markdown"):
            raise BackendError(
                "No compiled output for that target. " + response.text.strip()
            )

        if fmt == "zip":
            return response.content
        return response.json()

    # ── helpers ──────────────────────────────────────────────────────────

    async def _raw_items(
        self, pack_id: str, artifact_type: str | None
    ) -> list[dict[str, object]]:
        params = {"type": artifact_type} if artifact_type else None
        response = await self._get(
            f"/api/v1/collections/community/{pack_id}/artifacts", params
        )
        return response.json()

    def _pack_summary(self, raw: dict[str, object]) -> dict[str, object]:
        summary = {key: raw.get(key) for key in _PACK_FIELDS}
        if self.site_url:
            summary["url"] = f"{self.site_url}/packs/{raw.get('id')}"
        return summary

    def install_url(
        self,
        pack_id: str,
        target: str,
        with_packs: list[str] | None = None,
        fmt: str = "md",
    ) -> str | None:
        """The plain HTTP link to the same compiled output, for non-MCP callers."""
        if not self.site_url:
            return None
        params: list[tuple[str, str]] = [("target", target), ("format", fmt)]
        params += [("with", other) for other in (with_packs or [])]
        return (
            f"{self.site_url}/api/v1/collections/community/{pack_id}/install.md?"
            f"{urlencode(params)}"
        )
