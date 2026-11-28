---
name: Personal Data Inventory
description: Procedure for building a record of personal data processing from code and infrastructure. Use when starting a privacy review or before adding a new data store or integration.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [privacy, data-mapping, gdpr]
---
## Purpose

Produce an accurate map of what personal data exists, where it flows and who can see it, which every other privacy task depends on.

## When to use it

When onboarding a system, preparing a DPIA or records of processing (GDPR Art. 30), or adding a store, event or vendor.

## Checklist

- **Find stores**: databases, object storage, caches, search indexes, queues, logs, analytics, backups and exports.
- **Find fields**: names, emails, phone numbers, addresses, IDs, IP addresses, device and cookie identifiers, location, free text and uploads; remember special categories (health, biometrics, beliefs) need extra care.
- **Per store record**: data categories, purpose, source, who can access, processors and recipients, region, retention and deletion mechanism.
- **Flows**: where data enters, is copied (replicas, ETL, exports) and leaves (vendors, support tools, AI services).
- **Gaps**: list unknowns as questions for the owner rather than guessing.
- **Keep it current**: the inventory is updated in the same change that alters the data.

## Expected output

A table of stores and flows with purpose, retention and recipients filled in, and a list of open questions for the privacy lead.
