---
name: RAG Design
description: Design and review checklist for retrieval-augmented generation covering ingestion, chunking, retrieval, grounding and failure handling. Use when building or debugging a RAG system.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ai, rag, retrieval]
---
## Purpose

Make retrieval measurable and the generated answer traceable to sources, since most RAG failures are retrieval failures.

## When to use it

When designing a RAG pipeline, debugging wrong or ungrounded answers, or changing the embedding model, chunking or index.

## Checklist

- **Evaluate retrieval separately**: measure whether the right passage is retrieved (recall at k, hit rate) before judging the generated answer; fix retrieval first.
- **Ingestion**: parse documents faithfully, keep structure (headings, tables), record source, version and access rights as metadata, and re-ingest on change.
- **Chunking**: split on meaning (sections, paragraphs) with modest overlap; tune size on your eval set rather than copying a default; keep the parent context reachable.
- **Retrieval**: combine lexical and vector search where exact terms matter, add a reranker if precision is low, and filter by metadata (tenant, date, permissions) before ranking.
- **Access control**: enforce the user's permissions at retrieval time; never retrieve and then rely on the model to withhold.
- **Prompting**: pass sources with identifiers, instruct the model to answer only from them and to say when they are insufficient, and require citations.
- **Treat retrieved text as untrusted**: it can contain instructions; apply the pack's rule that model-bound content is data, not commands.
- **Failure handling**: empty or low-score retrieval returns an honest 'not found', not a guess; log queries and retrieved ids (without personal data) for debugging.
- **Freshness and drift**: schedule re-embedding when the model changes, and monitor retrieval quality on a fixed query set.

## Expected output

A pipeline description with measured retrieval quality, enforced access control, cited answers and defined behaviour when nothing relevant is found.
