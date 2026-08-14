---
name: Container Build
description: Multi-stage builds, distroless base images, layer caching, and vulnerability scanning for production containers.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [devops, docker, containers]
---
## Purpose

Build containers that are small, secure, and reproducible.

## Checklist

- **Multi-stage builds**: build stage with full SDK, production stage with only runtime deps.
- **Base image**: prefer distroless or scratch for production; use Alpine as a pragmatic minimum.
- **Layer caching**: order Dockerfile instructions from least to most frequently changing (deps first, code last).
- **Non-root user**: production containers run as a non-root user, not root.
- **Vulnerability scanning**: scan images for CVEs before pushing to registry (trivy, grype, or equivalent).
- **Image tagging**: tag with commit SHA + semantic version; `latest` is never used in production.
- **Reproducible builds**: pin base image digests, not tags.

## Expected output

A Dockerfile producing minimal, scanned, non-root containers with pinned base images and multi-stage separation.
