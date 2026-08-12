---
name: Secrets Scan Checklist
description: Common credential shapes to recognize in a diff (API keys, tokens, connection strings, private key blocks) and the escalation rule to follow when one is found.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [security, secrets, review]
---
## Purpose

Give a reviewer a fast pattern-matching pass for credential-shaped strings, so secrets get caught by recognizable shape rather than relying on remembering to look for them. Pair this with the `Secrets Are Always A Hard Fail` rule — this skill is about *finding* the secret; that rule governs what happens next.

## When to use it

At the start of every review, before looking at anything else — a live credential outranks every other finding in urgency, so it's worth checking first rather than stumbling into it halfway through. Also run it against commit history when a repository's history hasn't been checked before, not just the current diff — a secret removed in a later commit is still exposed in history.

## Shapes to recognize

- **Cloud/provider API keys** — long fixed-prefix strings such as vendor keys that start with a recognizable literal prefix followed by 20+ alphanumeric characters. Don't rely on memorizing every vendor's exact prefix; the pattern (short literal prefix + long high-entropy suffix) is the signal.
- **Generic tokens/secrets** — high-entropy strings (mixed case, digits, length 32+) assigned to a variable or field named `token`, `secret`, `key`, `password`, `credential`, `auth`, or similar, especially in config, `.env`-style files, or hardcoded as a default value.
- **Connection strings** — URLs with a scheme like `postgres://`, `mysql://`, `mongodb://`, `redis://`, `amqp://` that embed a username and password in the authority component (`scheme://user:password@host/...`).
- **Private key blocks** — anything containing `-----BEGIN ... PRIVATE KEY-----` (RSA, EC, OpenSSH, PGP), or `.pem`/`.pfx`/`.p12` file content pasted inline.
- **JWTs and session tokens** — three base64url segments separated by dots (`eyJ...`.`...`.`...`), especially if hardcoded rather than generated at runtime.
- **Webhook/signing secrets** — values assigned to names like `webhook_secret`, `signing_key`, `hmac_key` sitting next to the verification code that's supposed to use them.

## What doesn't count

Not every long random-looking string is a secret — don't flag UUIDs used as non-sensitive IDs, hashes of already-public content, or clearly-labeled placeholder/example values (`sk-example-xxxxxxxxxxxx`, `YOUR_API_KEY_HERE`) as long as they're unambiguously non-functional. When genuinely unsure whether a string is live, treat it as a secret until proven otherwise rather than the reverse — the cost of a false positive (someone confirms it's a placeholder) is far lower than the cost of a false negative (a live key ships).

## Steps

1. Search the diff (and, on a first-time review, the full history) for the shapes above using both pattern search and a scan of variable/field names that suggest a credential.
2. For each hit, confirm whether it looks like a real, functioning value or an obvious placeholder.
3. Any real hit is an automatic FAIL — do not downgrade it, do not defer it, do not fold it into a lower-priority note.
4. Escalate immediately per the `Secrets Are Always A Hard Fail` rule: report it as its own top-line item, separate from the rest of the findings report, and note that the credential should be treated as compromised and rotated — not just removed from the diff.

## Expected output

```
SECRET FOUND — <file:line>
  Shape: <API key / connection string / private key / token / ...>
  Evidence: <redacted-but-identifiable snippet, e.g. "sk_live_****...last 4 chars only, never full value">
  Escalation: treat as compromised — rotate the credential; do not merely delete the line and consider it resolved.
```

Never paste the full secret value into the findings report itself — reference its location and a redacted form so the report doesn't become a second place the credential is exposed.
