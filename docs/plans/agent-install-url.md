# Agent-Fetchable Install URL for Packs and Setups

Status: **Researched, not started.** Design record only — no code exists for
this feature.
Scope: a URL a user can hand to *any* coding agent (whatever framework), which
the agent fetches and uses to install a pack, with no CLI and no account.

**Verdict:** it is ~80% possible today, and what is missing is one small
read-only endpoint plus a UI affordance. Nothing about the data model, the
compiler, or the adapters needs to change. The single genuinely new idea
needed is a *pack-scoped* compile (today everything compiles through a saved
setup), and even that is a ~40-line seam in `backend/app/services/compiler.py`.

---

## 1. What exists today

| Capability | Route / command | Auth | Scope |
|---|---|---|---|
| Compile to JSON | `POST /api/v1/profiles/compile` | session or Bearer | a **setup** (`Profile`) the caller can read |
| Compile to zip | `POST /api/v1/profiles/compile/zip` | session or Bearer | same |
| CLI install | `myace pull --profile <name\|id> --target <t>` | `myace login` token | same |
| Direct write (local companion) | `POST /apply/preview`, `POST /apply` on `127.0.0.1:8765` | loopback + `X-MyACE-Companion` | same, opt-in `--allow-apply` |
| Public pack metadata | `GET /api/v1/collections/community/{id}` | **none** | published + approved |
| Public pack contents | `GET /api/v1/collections/community/{id}/artifacts` | **none** | published + approved, enabled items only |
| Use counter | `POST /api/v1/collections/{id}/use` | required | — |

Key files:

- `backend/app/api/profiles.py` — compile, compile-status, zip, install claims.
- `backend/app/api/collections.py` — community/public reads (line ~266–418),
  `_visible_public_collection()` (line 237), `_get_public_collection_or_404()`
  (line 252), `/use` (line 1073).
- `backend/app/services/compiler.py` — `compile_profile()` (line 55) requires a
  `Profile` ORM row; `compute_compiled_hash()` (line 20).
- `frontend/src/components/InstallMethodPanel.tsx` — the existing
  Download / CLI / Direct three-way install UI.
- `frontend/src/pages/PackDetail.tsx` — the action aside, lines 592–683.
- `frontend/src/lib/packApi.ts` — the anonymous storefront client.

### The three gaps

1. **No pack-scoped compile.** Every compile path starts from a saved `Profile`
   row (`backend/app/api/profiles.py:276`, `:342`, and
   `cli/myace_cli/sync.py:306`). A pack alone cannot be compiled, so there is
   nothing to hand an agent for a pack.
2. **No anonymous compile.** `/compile`, `/compile/zip` and `myace pull` all
   require `Depends(get_current_user)`. An agent acting for a visitor has no
   cookie and no token.
3. **No agent-shaped payload.** The two wire formats are a JSON
   `{filename: content}` map and a zip. An arbitrary agent can technically use
   either (shell + `unzip`/`jq`), but neither is a document it can *read*, and
   neither carries the behavioural instruction ("don't clobber the user's
   files") that makes an unattended write safe.

---

## 2. Design options

| Option | Agent UX | Effort | Verdict |
|---|---|---|---|
| **A. Markdown install doc over HTTP** | Agent does `WebFetch <url>`, reads a self-describing doc, writes the files | S | **Recommended v1** |
| B. JSON manifest + `jq`/script | Agent must shell out and parse | S | Ship alongside A as `?format=json` |
| C. Public zip URL | Agent must download + unzip | S | Add as `?format=zip`, not the headline |
| D. MCP server (`/mcp`, `get_pack` tool) | Best UX *where supported*, zero support elsewhere | L | Phase 3 |
| E. `curl … \| sh` installer script | Works everywhere; piping the internet into a shell is a bad default | M | Rejected |
| F. `myace install <url>` CLI subcommand | Clean, reuses `/apply` safety, but needs the CLI installed | M | Phase 2.5 |

A is the only option that satisfies "whatever platform" with zero client
install and zero parsing, and it degrades gracefully — a human can read the
same URL and follow it by hand.

---

## 3. Recommended v1

### 3.1 Endpoint

```
GET /api/v1/collections/community/{collection_id}/install.md?target=<adapter>
```

- Lives in the `/community/...` URL family, registered above
  `/{collection_id}` (AGENTS.md rule 16), decorated with
  `@storefront_limiter.limit(settings.storefront_rate_limit)` exactly like its
  neighbours (rule 42 / ADR-0014).
- Visibility predicate: reuse `_get_public_collection_or_404()` unchanged —
  `is_active AND published AND moderation_status == 'approved'`, 404 otherwise.
  **No new data exposure**: every byte this route emits is already available
  anonymously from `/community/{id}/artifacts`.
- **`target` contract — two HTTP outcomes, four cases.** The param is declared
  as plain `str | None = Query(None)`, deliberately **not** `CompileTarget`:
  that `Literal` (`backend/app/models/profile.py:101`) is a hand-maintained list
  that drifts from the adapter registry, and a Literal would make an unrecognised
  value a 422 that never reaches the handler. Since an unrecognised target's
  best answer is the guidance document, not a validation error, the handler owns
  the decision:
  1. **omitted** → `200 text/markdown`: a short "which framework?" document
     listing every **enabled** adapter with its full install URL, so the links
     it publishes are exactly the ones that will compile. Admin-disabled
     adapters are named in a separate "currently disabled by an administrator"
     line, with no URL — advertising a link that case 4 answers with a 400 would
     be the same contradiction in a different place. This is what makes a bare
     pasted link useful instead of a 422.
  2. **known** → the compiled install document.
  3. **unrecognised** → also `200 text/markdown`, the same guidance document,
     with one extra line naming the requested value as unknown. Returning 200
     here is deliberate: the caller is an agent holding a link it did not build,
     and a browsable list of valid targets is more useful than an error it can
     only retry blindly. It is also what makes a stale `PACK_TARGETS` entry in
     the UI self-heal (§5.1) rather than dead-end in a 400.
  4. **registered but admin-disabled** → `400` with `AdapterDisabledError`'s
     message. This one *is* an error: the adapter exists and an administrator
     turned it off, so the actionable answer is the message, not a list.

  **`format` is ignored for cases 1 and 3.** The guidance document is always
  `text/markdown`, even when the caller asked for `json` or `zip`: there are no
  files to package, and an agent that asked for `?target=typo&format=json`
  still needs something it can read and act on. Document that, and cover it in
  the test matrix — otherwise the behaviour is undefined for half the matrix.

  There is no default target and no `pack_install_default_target` setting:
  guessing a framework writes files into the wrong layout.
- Media type `text/markdown; charset=utf-8`, plus:
  - `ETag: W/"<compiled_hash>"` and `304` on `If-None-Match`
    (`compute_compiled_hash()` already exists).
  - `Cache-Control: public, max-age=300`.
  - `X-Robots-Tag: noindex`.
  - `Content-Disposition: inline; filename="<slug>.install.md"` via `slugify()`
    (rule 22 — never interpolate `pack.name` raw into a header).

**Do not** increment `download_count` on this GET. Counters that move on an
unauthenticated GET are trivially inflatable and turn a crawler into a "use".
Keep the counter on the explicit `POST /use`.

### 3.2 Getting a compiled file set from a pack

Preferred: extract a private helper from `compile_profile()`.

```python
async def _compile_collections(
    session, *,
    collection_ids: list[uuid.UUID],
    disabled_ids: set[uuid.UUID],
    snapshots: dict[str, dict[str, object]],
    can_use_frozen: bool,          # ADR-0015 gate, resolved by the caller
    profile_id: str,
    profile_name: str,
    target: str,
    include_disabled: bool,
    requesting_user: User | None,
) -> ProfileCompileResponse: ...
```

`compile_profile()` keeps its signature and becomes a thin wrapper: it parses
`profile.additional_collection_ids` / `disabled_artifact_ids` /
`pack_snapshots` and computes the frozen gate exactly as it does today —
`requesting_user is None or requesting_user.id == profile.owner_id or
requesting_user.is_admin` (`backend/app/services/compiler.py:113-117`) — then
passes it in. A new `compile_pack(session, collection_ids, target)` calls the
same helper with `disabled_ids=set()`, `snapshots={}`, `can_use_frozen=False`,
`include_disabled=False`, `requesting_user=None`.

The `can_use_frozen` parameter is not cosmetic. That branch is the ADR-0015
gate: it is what stops a third party compiling *someone else's public profile*
from being served a frozen snapshot of a pack that has since been unpublished.
The helper has no `Profile.owner_id` to compare against, so the rule must be
computed by whoever holds the profile — never re-derived inside the helper, and
never defaulted to `True`. `compile_pack()` passes `False` unconditionally: a
pack-scoped install has no snapshots to serve anyway, and the safe value costs
nothing.

Note that `collection_ids` is a **list**, not a single id, so the `?with=`
composable-pack case (Q2 below) costs no extra signature churn. `compile_pack()`
still takes the packs in caller order — base first — because name dedup is
order-sensitive (rule 29).

**Envelope values for a pack compile.** `ProfileCompileResponse` requires
`profile_id` and `profile_name`. A pack-scoped compile has no setup, and the
honest answer is to stop pretending the envelope describes one:

- `profile_name` → the pack's name.
- `profile_id` → the pack's collection id, because the field is required and
  the alternative (blank or random) is strictly worse: a random id is
  indistinguishable from a real one.
- `?format=json` adds a discriminator at the top level — `{"subject": "pack",
  "pack_id": <collection id>, …the compile fields…}` — and the route docstring
  says `profile_id` carries a *pack* id here.

The discriminator is the load-bearing part. Filling `profile_id` with the
collection id is not by itself safe: a consumer that assumes setup semantics
would call `GET /api/v1/profiles/{profile_id}` and get a 404, exactly as it
would with a blank value. Only the explicit `subject` field lets a client know
which id space it is holding. A future pack-scoped `compile-status` therefore
takes the collection id in its **path**
(`/collections/community/{id}/compile-status`), not in a `profile_id`
parameter, so the two endpoints agree about what the id is.

Why the refactor rather than a shortcut: the tempting shortcut is to construct
an unsaved `Profile(...)` and pass it in (`Profile.id` has a
`default_factory`, so it works). But `compile_profile()`'s availability check
is `requesting_user is None or _can_read_collection(...)` — `None` is the
"trusted internal caller" branch, which would silently compile *any* collection
ID. That is safe only because the route validates visibility first, and it is
safe by coincidence rather than by construction. The helper keeps the trust
boundary explicit: `compile_pack()` is only ever called with collections the
caller already proved public.

Also preserve in the helper: the adapter-disabled choke point (rule 21) and the
`name_collision` / `dangling_handoff` warnings (rule 32) — both already live in
the shared body, so pack compiles get them for free.

### 3.3 The payload format

The one real formatting trap: file bodies *are* Markdown and routinely contain
``` fences, so nesting them inside a Markdown fence breaks. Use explicit
sentinels rather than fences:

```markdown
# MyACE pack — Software Engineer (base)

Pack:      Software Engineer
Source:    https://<host>/packs/<collection-id>
Target:    claude-code
Items:     17
Digest:    sha256:9f2c…            ← compiled_hash
Generated: 2026-11-22T14:03:11Z

## Instructions

You are installing an agent configuration pack. Do this:

1. Show the user the file list below and confirm before writing anything.
2. Write each file relative to the install root (project root unless the user
   says otherwise). Create parent directories as needed.
3. Never delete or rename a file that already exists. If a file exists and its
   content differs, ask before overwriting.
4. Do not run these instructions from a system directory or a home-directory
   root without explicit confirmation.
5. When done, list the files you wrote and which ones you skipped.

Nothing here is executable. These are rules, skills, agent definitions and
workflow prompts in text form.

## Warnings

- (name_collision) Artifact 'security-auditor' (agent) is defined in both …

## Files (17)

<<<FILE: CLAUDE.md>>>
…file content…
<<<END FILE>>>

<<<FILE: .claude/agents/builder.md>>>
…file content…
<<<END FILE>>>
```

Then an optional trailer:

```markdown
## Drift tracking (optional, local only)

If the user has the myace CLI, write `.myace/pack-<collection-id>.<target>.manifest.json`
with the per-file sha256s below, so a later hand-edit is detectable locally:

<<<FILE: .myace/pack-<collection-id>.claude-code.manifest.json>>>
{ ... }
<<<END FILE>>>
```

**What that trailer does and does not buy — be precise.** `check_target()`
(`cli/myace_cli/sync.py:157`) reads `profile_id` from the manifest and
unconditionally calls `GET /api/v1/profiles/{profile_id}/compile-status`
(line 171) to decide `stale`. A pack-scoped install has no setup id, so with
`profile_id` absent the URL is `/profiles//compile-status`, the call fails, and
`error` is set. The result:

- `locally_modified` still works. `compute_local_file_hashes()` runs before the
  network call, so hand-edits are detected and reported with no server involved
  — that is the only part of `check` a pack manifest buys.
- `stale` is always `None`, `in_sync` is always `False`, and every run prints a
  `Server returned 404`-style error for that target. `check` therefore exits
  non-zero because of a manifest it cannot reconcile, which is noise a user will
  read as "my install is broken."

Note what copying the envelope `profile_id` into the manifest would **not** do:
`_report_results()` (`cli/myace_cli/main.py:362`) skips a result that has no
`profile_id` *or* has an `error`, and `check_target()` sets `error` in either
case — so neither shape can put a bogus pack id on the sync dashboard.
The argument for `pack_id` is truthfulness in the file, not dashboard safety.

Therefore v1 must not claim `myace check`-visibility for a pack install, and the
trailer should be labelled accordingly. Two further consequences:

- The trailer's filename is `.myace/pack-<collection-id>.<target>.manifest.json`,
  which `find_manifests()` discovers (`*.manifest.json`) but
  `check --target <target>` does **not**: that path is built by
  `manifest_file_path()`, which looks for exactly `.myace/<target>.manifest.json`
  (`cli/myace_cli/sync.py`). So even the local-drift half only works via
  `myace check --all`. Say that in the trailer, or name the file
  `.myace/<target>.manifest.json` and accept that it collides with a setup pull
  for the same target in the same directory.
- Because of the permanent `error`, the honest v1 default is to make the trailer
  **opt-in** (a sentence the agent may act on), not a normal part of the
  install — or to leave it out of v1 entirely and ship it in Phase 2 with the
  route and CLI change that make it truthful.

Either write the manifest with a `pack_id` field and let `check` treat a manifest
with no `profile_id` as local-only, or add a pack-scoped
`GET /api/v1/collections/community/{id}/compile-status?target=…` (collection id
in the path — §3.2) and extend `check_target()` to use it. That second option is
a Phase 2 item, since it needs a small CLI change (`cli/myace_cli/sync.py`) as
well as the route. Until then the plan's phasing treats the manifest as optional
and unverified.

`?format=json` returns the `ProfileCompileResponse` fields
(`{files, warnings, compiled_hash, artifact_count, profile_name, profile_id}`)
**plus the discriminator described in §3.2** —

```json
{
  "subject": "pack",
  "pack_id": "0b0f…",
  "profile_id": "0b0f…",
  "profile_name": "Software Engineer",
  "target": "claude-code",
  "artifact_count": 17,
  "compiled_hash": "9f2c…",
  "files": { "CLAUDE.md": "…" },
  "warnings": []
}
```

`profile_id` is present only because the response model requires it; `subject`
and `pack_id` are what a client should branch on, and the two id fields are
equal by construction. A consumer that ignores `subject` and treats
`profile_id` as a setup id will 404 on `/api/v1/profiles/{id}` — the docstring
must say so.

**How the discriminator survives serialization.** This is the one place the
implementation can silently lose the whole mechanism: the route returns three
media types, so it must **not** declare
`response_model=ProfileCompileResponse` — FastAPI would validate the handler's
return value against that model and drop `subject`/`pack_id` as unlisted fields,
with no error to notice. Two acceptable shapes, pick one and test it:

- declare `response_model=None` and build the JSON branch explicitly, e.g.
  `JSONResponse(PackCompileResponse(...).model_dump(mode="json"))`; or
- declare a small `PackCompileResponse(ProfileCompileResponse)` schema with
  `subject: Literal["pack"]` and `pack_id: uuid.UUID`, and return that from the
  JSON branch, accepting that a single route cannot carry a per-format
  `response_model` and so still needs `response_model=None` at the decorator.

`PackCompileResponse` is a response schema only — **no table, no migration**.
The test in §6 must assert `subject`/`pack_id` in the parsed body, because a
`response_model` regression that strips them still returns 200 with every other
field intact.

`?format=zip` returns the same archive `/compile/zip` builds. It carries no
discriminator file, and that is a judgement call rather than an invariable rule:
`/compile/zip` already adds `_myace_warnings.txt` when there are warnings, so a
bookkeeping file in the archive is an established precedent. The reasoning here
is that a warnings file is an exceptional, transient report while a
discriminator would ship on every install, and the URL is already pack-scoped so
nothing needs disambiguating. All three formats share one `compile_pack()` call.

### 3.4 Size and abuse

- Output size is bounded by the pack, not by the request: a request body is
  absent (GET), so `MaxBodySizeMiddleware` is irrelevant here. Add a
  `settings.pack_install_max_bytes` (say 2 MiB) and return 413 with a
  "download the zip instead" message if the rendered doc exceeds it, so one
  pathological pack cannot pin a worker per request.
- Enable gzip at the nginx `/api/` location (or `GZipMiddleware` scoped to
  this route). These documents are highly compressible Markdown; without it a
  17-item pack is several hundred KB per fetch, at 120 requests/minute/IP.
- Rate limiting is per-process in-memory (rule 36's documented caveat) — fine
  as an abuse deterrent, not as a hard quota.

### 3.5 Private and draft packs

An agent has no cookie, so `GET /community/...` is the only URL that works
unattended. That means:

- **v1 scope: published + approved packs only.** The UI must not offer the URL
  for a draft or private pack.
- **Phase 1.5 (optional, cheap):** an authenticated twin,
  `GET /api/v1/collections/{collection_id}/install.md?target=…`, behind
  `Depends(get_current_user)` with `authorize_access(is_public=…)`. Then
  `curl -H "Authorization: Bearer $MYACE_API_TOKEN" <url>` works for the
  user's own packs, from any agent that can run a shell with an env var.
  No signed-URL/token-in-query-string machinery, which would put credentials
  into access logs, proxy logs and browser history.
- **Do not** design a "public link for my private pack" minted-token URL yet.
  It is a new credential type with its own revocation, expiry, and logging
  story — a separate ADR, and not needed for the use case described.

---

## 4. Open design questions

**Q1. Which target does the URL use?**
It must be explicit or the file layout is unknowable (`.claude/…` vs
`.cursor/rules/…` vs `AGENTS.md`). Recommendation: `?target=` on the URL, with
a picker in the UI, and the generated doc always naming the target it was
built for. If `target` is omitted, do not guess silently — render a short
"which framework?" document that lists the available adapters and their URLs.
That keeps a stale link useful rather than wrong. The normative four-case
contract (omitted / known / unrecognised / registered-but-disabled, and why the
param is a plain `str` rather than `CompileTarget`) is §3.1; everything else
defers to it.

**Q2. What about add-on ("additional") packs that assume a base pack?**
A pack-scoped compile compiles that pack alone, which for an add-on may be an
incomplete story. Recommendation: (a) the doc states the pack kind
(`base` / `add-on`) and, for an add-on, names the packs it is usually paired
with; (b) accept a repeatable `?with=<collection-id>` that adds more packs to
the compile (all still validated as publicly visible), so
`?with=<base-id>` produces the real composed set. Cheap: the helper already
takes a list.

**Q3. Pack URL or setup URL?**
Both, and they are different products:

- **Pack URL** — public, shareable, zero-account. "Here is a pack, install it."
  This is what the user asked for and what works unauthenticated.
- **Setup URL** — exact. It carries the user's own choices (which packs, which
  items disabled) and matches what the web UI's install panel installs. Needs
  auth (Phase 1.5) or a Bearer token.

Recommendation: ship the pack URL first (it is the public, viral one), then add
the setup variant inside `InstallMethodPanel` as a fourth method tab.

**Q4. What should the user actually paste into their agent?**
Not a bare URL — a sentence. The copy action should put this on the clipboard:

> Fetch this and install the pack it describes, following its instructions.
> Ask me before overwriting any existing file: <url>

That single line is the whole feature from the user's point of view, and it is
why the payload must be self-describing rather than a tarball.

---

## 5. Where to surface it in the UI

### 5.1 Pack detail — yes, in the action aside

The user's instinct is right: `PackDetail.tsx`, in the right-hand aside
(lines 592–683), below `Use this pack` / `Add to a setup…` /
`Customize a copy`, as a **fourth, visually secondary** affordance. Reasons:

- It is the only page where a pack is the subject, it already renders for
  anonymous visitors, and it already has the copy-to-clipboard idiom in the
  codebase (`InstallMethodPanel.tsx:118`, `ProfileDetail.tsx:277`).
- It must be *below* the primary actions and styled like `Customize a copy`
  (borderless, muted), because it is a power path: most people will still use
  "Use this pack". Labelling it as a peer of the brand-coloured button would
  make a niche action look like the recommended one.
- The Secondary/tertiary placement also keeps the aside's visual rhythm —
  one brand button, then quieter rows — which rule 42's vocabulary work
  established.

Shape (two branches — the page serves owners and anonymous visitors, and the
stack differs):

```
signed-in, owner of a published pack        anonymous
─────────────────────────────────           ─────────────────────────────
[ Publish… / Manage items ]                 [ Use this pack ]        (signup)
[ … owner tools … ]                         [ Sign up to build a setup ]
[ Customize a copy ]  (n/a for owner)       [ Customize a copy ]
─────────────────────────────────           ─────────────────────────────
 Install with your agent  ▾                 Install with your agent  ▾
   Target: [ Claude Code ▾ ]                  Target: [ Claude Code ▾ ]
   [ Copy install prompt ]                    [ Copy install prompt ]
   https://<host>/api/v1/collections/…        https://<host>/api/v1/collections/…
```

Details:

- Gate on `published && moderation_status === 'approved' && pack.is_active !==
  false` — the same conditions as `_visible_public_collection()` (ADR-0014),
  written so it works on **both** payload shapes. This matters: the frontend's
  `Pack` interface (`frontend/src/types/packs.ts:21`) has no `is_active` field,
  and `PublicCollectionRead` omits it entirely, so a plain
  `pack.is_active && …` is `undefined && …` on the anonymous payload — which
  would hide the panel from exactly the audience it exists for, and is a type
  error besides. Add `is_active?: boolean` to `Pack` and use the `!== false`
  form: inactive packs are already excluded server-side on the public route, so
  `undefined` legitimately means "not reported, therefore fine."
  For an owner's draft, show the row disabled with "available once this pack is
  published" rather than hiding it — otherwise the owner never discovers it.
- **The target picker's data source must not be `GET /api/v1/adapters`.** That
  route is authenticated (`Depends(get_current_user)`,
  `backend/app/api/adapters.py:28`), and this panel renders on the anonymous
  `/packs/:id` route (`frontend/src/App.tsx:139-145`, outside `RequireAuth`) —
  so for the very audience this feature exists for, a live adapter fetch is
  empty. `FRAMEWORK_LABELS` (`frontend/src/lib/packs.ts:39`) is display labels
  only, with no exported label→target-id map. Pick one and name it:
  - **Recommended:** export a small `PACK_TARGETS: { id, label }[]` constant from
    `lib/packs.ts` next to `FRAMEWORK_LABELS`, and accept that it can drift.
    The drift is self-healing: an id the server no longer knows gets the
    "which framework?" document (§3.1 case 3), which lists the *live* adapter
    set. No new route, no new auth exception.
  - Alternative: add a public `GET /api/v1/adapters/public` that returns name +
    label only, and name it as a further ADR-0014 exception. Do this only if
    adapter-list drift becomes a real problem; it is a second public route for
    a UI convenience.
  Either way the rule-23 constraint holds: read `adapter.name` for the target
  id, never a `supported_targets()` alias.
- Put the raw URL in a `<code>` block with its own copy button, plus a second
  button that copies the full prompt sentence. Two buttons, not one, because
  the URL is also what people paste into issue trackers and chat.
- The whole block collapses by default. This is a disclosure, not a headline.

### 5.2 Setup detail — the authenticated twin

In `InstallMethodPanel.tsx`, add a fourth tab next to Download / CLI / Direct:
`Agent`. It shows the same two copy actions but with the setup's own target
and (Phase 1.5) a `curl -H "Authorization: Bearer $MYACE_API_TOKEN" …` line.
Follow the existing rule from that file's docstring — a method that cannot work
is *absent*, not a disabled tease (the `direct` tab already does this).

### 5.3 Not recommended

- Do not put the URL in the global ⌘K palette or the sidebar.
- Do not add a new page/route for it in v1. If a pretty shareable URL is
  wanted (`https://<host>/i/<id>.md`), do it later as a one-line nginx
  `location /i/` proxy — no React route, no SPA change, and the `.md`
  extension keeps "give this to an agent" self-evident.
- Do not surface it on the library cards — one action per card, and it is
  navigational.

---

## 6. Implementation checklist

### Backend

1. `backend/app/services/compiler.py`: extract `_compile_collections()`, keep
   `compile_profile()` as
   a wrapper, add `compile_pack()`. No behaviour change to existing callers —
   the existing compiler tests are the regression net.
2. `collections.py`: `GET /community/{collection_id}/install.md`
   - `target: str | None = Query(None)` — **not** `CompileTarget` (§3.1);
     omitted → guidance doc; unrecognised → guidance doc; registered-but-disabled
     → 400 with `AdapterDisabledError`'s message
   - `format: Literal["md","json","zip"] = "md"` — the `json` variant includes
     the `{"subject": "pack", "pack_id": …}` discriminator (§3.3)
   - `with_: list[uuid.UUID] = Query([], alias="with")`
   - `_get_public_collection_or_404()` for the pack and each `with=` pack
   - `@storefront_limiter.limit(settings.storefront_rate_limit)`
   - ETag from `compiled_hash`, `Cache-Control`, `X-Robots-Tag`,
     `Content-Disposition` via `slugify()`
   - size guard → 413 with a zip suggestion
3. `config.py`: `pack_install_max_bytes` (default 2 MiB). No default-target
   setting — an omitted `target` returns the guidance document, never a guess.
4. Docstring on the route stating the ADR-0014 auth exception it inherits, why
   no counter moves, and that `profile_id` in the envelope carries a **pack**
   id (branch on `subject`).
5. Add a `PackCompileResponse(ProfileCompileResponse)` **response schema**
   (`subject: Literal["pack"]`, `pack_id: uuid.UUID`) and return the JSON branch
   through it with `response_model=None` on the decorator (§3.3 — a
   `response_model` here would silently strip the discriminator). No table
   model, no migration, no adapter change.

### Frontend

1. `lib/packApi.ts`: `installUrl(collectionId, target)` helper — single place
   that builds the URL from `window.location.origin`, so tests and the
   component agree.
2. New `components/AgentInstallPanel.tsx` (collapsible; target picker; URL
   `<code>`; two copy buttons). Used by `PackDetail.tsx`; later reused with an
   `authenticated` prop in `InstallMethodPanel.tsx`.
3. `PackDetail.tsx`: mount it below `Customize a copy` in the aside, gated on
   published + approved; disabled-with-reason for the owner's draft.
4. Tests: renders only for approved packs; target picker builds the right URL;
   copy writes the expected string (the codebase already asserts
   `navigator.clipboard.writeText` — `TargetExporter.test.tsx:162`).

### Docs

- `README.md` route table: the new public route.
- `AGENTS.md` rule 42 (canonical routes/vocabulary) and rule 13's auth-exception
  list: add the route, name it "agent install URL".
- New ADR `docs/adr/0017-agent-fetchable-install-documents.md`: why a document
  instead of a tarball or an installer script, why public read only, why no
  counting, and why the payload is sentinel-delimited.
- `docs/debugging.md`: the nested-code-fence trap and the "URL 404s because the
  pack is not approved" case (the most likely support question).

### Tests (backend)

- Anonymous 200 for an approved public pack; 404 for draft, private, inactive,
  unpublished — including `with=` ids that are not publicly visible.
- Omitted `target` → 200 guidance document listing live adapter names and
  URLs (not a 422); an unrecognised `target` → the same guidance document with
  an "unknown target" line, **not** a 400; a registered-but-admin-disabled
  adapter → 400 with `AdapterDisabledError`'s message.
- Guidance cases ignore `format`: `?target=typo&format=json` and
  `&format=zip` still return `text/markdown` guidance, not a JSON/zip error.
- `target` is a plain `str` param: a `CompileTarget` Literal would make the
  unrecognised case an unreachable 422, so assert the 200-guidance behaviour
  explicitly.
- Payload contains every enabled item's target file and **no** disabled ones.
- `format=json` returns the `ProfileCompileResponse` fields **plus**
  `subject: "pack"` and `pack_id`, with `profile_id == pack_id`; assert the
  discriminator, not just the field names. `format=zip` opens and contains the
  same filenames with no added bookkeeping file.
- `with=<base>` composes two packs and emits `name_collision` warnings when
  they collide.
- ETag/304 round trip.
- Size guard 413.
- `download_count` unchanged after N calls.
- Compiler parity: `compile_pack()` on a collection == `compile_profile()` on a
  setup whose only pack is that collection (same files, same hash).
- **ADR-0015 gate:** `_compile_collections()` with `can_use_frozen=False` never
  serves a snapshot even when `snapshots` is populated, and `compile_profile()`
  still denies a third party's frozen snapshot for a public profile — the
  existing `test_compile_authz.py` cases must pass unchanged.

---

## 7. Phasing and rough effort

| Phase | Scope | Effort |
|---|---|---|
| 0 | Decide Q1/Q2 and the payload format (this doc) | — |
| 1 | `compile_pack()` + `install.md` (the omitted / unrecognised / disabled `target` cases) + JSON/zip formats + tests | ~1 day |
| 1.5 | `AgentInstallPanel` in `PackDetail` + `PACK_TARGETS` + `packApi` helper + tests + docs/ADR | ~0.5 day |
| 2 | Authenticated `/{collection_id}/install.md`; `Agent` tab in `InstallMethodPanel`; pack-scoped `.../compile-status` + `check_target()` change so an agent-written manifest can report `stale` | ~1 day |
| 2.5 | `myace install <url>` — fetch the JSON form, reuse `/apply`'s diff+backup+409-on-change machinery so the CLI path and the agent path share one safety story | ~1–2 days |
| 3 | MCP server exposing `list_packs` / `get_pack` / `install_pack` tools | ~1 week |

Total for a shippable v1 (phase 1 + 1.5): about a day and a half of careful
work, most of it tests and docs.

---

## 8. Risks and honest caveats

1. **Write safety is advisory, not enforced.** The endpoint hands an agent
   files and asks it to confirm before overwriting. Nothing can enforce that —
   the same is already true of every "install this config" document on the
   internet. Mitigations: the instructions lead with the confirm step, the doc
   lists files before content, and the payload never contains a shell command.
   This is a real, permanent limitation, not something a later phase fixes.
2. **Prompt-injection surface in the *other* direction.** Pack bodies are
   user-authored text that an agent will read as instructions. That is exactly
   what a rules/skills pack *is*, and it is already true of `myace pull` writing
   `AGENTS.md`. Worth one sentence in the install doc ("these files become
   instructions your agent will follow") so the human is not surprised.
3. **Target ≠ the agent's platform.** A user may paste a `claude-code` URL into
   a Cursor agent. The doc names its target explicitly so a mismatch is at
   least visible; whether to add a "wrong target?" hint is a UI decision, not a
   correctness one.
4. **Public-only means drafts have no URL.** Correct and intentional, but it
   will be the first piece of feedback ("why can't I share my draft"). Answer:
   publish it, or use the CLI/Bearer path.
5. **Cache invalidation.** `max-age=300` plus a `compiled_hash` ETag means a
   pack edit can lag up to five minutes for an agent that respects caching. Use
   a shorter `max-age` (60s) if that is too blunt; the ETag makes revalidation
   cheap either way.
6. **No server-side drift tracking for a pack install.** `myace check` keys
   off `profile_id` from the manifest, and a pack-scoped install has none — so
   even with the optional trailer, only `locally_modified` works and every run
   reports an `error` and exits non-zero until a pack-scoped compile-status
   route exists (§3.3, Phase 2). That is why the trailer is opt-in rather than
   part of a normal install. Do not claim "verified" anywhere — the existing
   install-claim vs `SyncStatus` distinction (ADR-0015) still holds.
7. **The roadmap now advertises an unbuilt feature.** Publishing the plan also
   publishes the gap on the project's front page. That is deliberate (it is
   what "on the roadmap" means) but it is a commitment to a shape that may
   change; if the design shifts materially, the README bullet moves with it.

---

## 9. Direct answers to the three questions

**Is it possible with the current backend?** Not as a URL. Every compile path
is setup-scoped and authenticated, and the only unauthenticated pack reads
return metadata plus raw items, not a compiled file set. The pieces are all
present — `compile_profile()`, the adapters, `compute_compiled_hash()`, the
public-visibility predicate, and the storefront rate limiter — so this is
assembly, not invention.

**What needs building?** One service seam (`compile_pack()` over a shared
`_compile_collections()`), one public GET route in the `/community/...` family
returning a sentinel-delimited Markdown document (plus `json`/`zip` variants),
a small frontend panel with a target picker and two copy buttons, and the
matching tests/ADR. No migration, no **table** model change, no adapter change —
the only added schema is the `PackCompileResponse` response model.

**Where in the UI?** Confirmed: the pack detail aside, below `Use this pack` /
`Add to a setup…` / `Customize a copy`, styled as a muted secondary disclosure
with the URL collapsed by default — visible only when the pack is published and
approved. The same component then reappears on the setup install panel as an
`Agent` tab for the authenticated, exact-setup variant.
