---
name: Threat Modeling Quickstart
description: A lightweight what-could-go-wrong / who-could-exploit-it / what's-the-blast-radius pass for any new network-facing interface, data store, or trust boundary.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [security, threat-model, review]
---
## Purpose

Give new attack surface a fast, structured look before it's considered reviewed, without requiring a full formal threat-modeling exercise (STRIDE workshop, data-flow diagrams, etc.) for every small change. This is the lightweight version that fits inside a normal code review.

## When to use it

Trigger this pass whenever a change introduces or materially alters:
- A new network-facing endpoint, listener, or public interface.
- A new data store (database, cache, queue, file store) or a new class of data flowing into an existing one.
- A new trust boundary — a new external integration, a new class of caller (e.g. previously internal-only, now reachable by end users), or a change to what an existing boundary trusts.

If none of these apply, skip it and note "N/A — no new attack surface" in the review.

## Steps

1. **Name the surface.** State in one sentence what's new: "a new `/api/v1/webhooks/incoming` endpoint that accepts POSTs from an external payment provider."

2. **What could go wrong?** List concrete failure modes, not abstract categories — spoofed requests (no signature verification), replay of a captured valid request, oversized payloads causing resource exhaustion, malformed payloads crashing the handler, the endpoint being used to enumerate internal state via timing or error differences.

3. **Who could exploit it?** Name the realistic actor for each failure mode: an anonymous internet user, an authenticated low-privilege user, someone who has compromised a downstream dependency, an insider with legitimate but narrower access. Don't default to "a sophisticated attacker" when the honest answer is "anyone who can send an HTTP request."

4. **What's the blast radius?** For each failure mode, state what's actually reachable if it's exploited — a single record, a single tenant's data, the whole data store, the ability to pivot to another system, or just noisy logs and no real impact. Be specific about scope; "could be bad" isn't a blast radius.

5. **Check the boundary controls.** For each identified risk, confirm there's a concrete mitigation in place — signature/HMAC verification, rate limiting, authentication, input size limits, allowlisted callers — and note which risks have no mitigation yet.

6. **Record the pass.** Write it up as a short block (see Expected output) attached to the review, not just a mental check — the point is that the next reviewer can see it happened rather than having to redo it or take it on faith.

## Expected output

```
Surface: <one-sentence description>

Risk: <what could go wrong>
  Actor: <who is positioned to do this>
  Blast radius: <what's actually reachable if they do>
  Mitigation: <what's in place today, or "none — flagged as a finding">

(repeat Risk block per failure mode identified)
```

Any risk with no mitigation and a non-trivial blast radius should also appear as a FAIL in the accompanying `security-checklist` report, not just noted here and forgotten.
